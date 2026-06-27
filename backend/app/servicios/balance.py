"""
balance.py
Logica para tomar una "foto" del balance de la fabrica en un instante.
Recorre el estado actual: suma saldos de cuentas, valoriza inventarios,
suma deudas y activos fijos, calcula escenarios y patrimonio. Congela todo
en una fila de Balance (mas el detalle por producto). La foto es inmutable.

NOTA: varios calculos (ventas/compras/gastos de la semana, escenarios)
dependen de definiciones de negocio que pueden ajustarse. Se marcan con TODO.
"""

from datetime import date, timedelta
from sqlalchemy import func
from app.models import (
    Balance, Balance_Detalle_Producto,
    Cuenta, Deuda, Activo, Tipo_Bien,
    Compra, Produccion, Producto_Terminado,
    Movimiento,
)


def tomar_balance(sesion, fecha_balance=None, dias_semana=7):
    """
    Toma una foto del balance actual de la fabrica.
    fecha_balance: fecha de la foto (referencia para "la semana").
    dias_semana: cuantos dias hacia atras cuentan como "esta semana".
    Devuelve el objeto Balance creado.
    """

    try:
        # ===== ACTIVOS LIQUIDOS: suma de saldos de todas las cuentas =====
        total_efectivo = sesion.query(
            func.coalesce(func.sum(Cuenta.Saldo_Actual_Cuenta), 0)
        ).scalar()

        # ===== ACTIVOS FIJOS por tipo de bien =====
        # Suma de valores de activos, agrupados segun el nombre del tipo de bien
        def suma_activos_por_tipo(palabra):
            return sesion.query(
                func.coalesce(func.sum(Activo.Valor_Activo), 0)
            ).join(Tipo_Bien, Activo.Id_Tipo_Bien == Tipo_Bien.Id_Tipo_Bien).filter(
                Tipo_Bien.Nombre_Tipo_Bien.ilike(f"%{palabra}%")
            ).scalar()

        total_inmuebles = suma_activos_por_tipo("INMUEBLE")
        total_equipos = suma_activos_por_tipo("EQUIPO")
        # Otros activos: todo lo que no es inmueble ni equipo
        total_otros = sesion.query(
            func.coalesce(func.sum(Activo.Valor_Activo), 0)
        ).scalar() - total_inmuebles - total_equipos

        # ===== INVENTARIOS VALORIZADOS =====
        # Stock de materia prima: restante x precio unitario del lote
        compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > 0).all()
        valor_stock_mp = 0
        for c in compras:
            precio_unit = c.Precio_Compra / c.Cantidad_Compra
            valor_stock_mp += c.Cantidad_Restante_Compra * precio_unit

        # Stock de producto terminado: restante x precio recomendado de venta
        producciones = sesion.query(Produccion).filter(
            Produccion.Cantidad_Restante_Produccion > 0
        ).all()
        valor_stock_pt = 0
        detalle_por_producto = {}  # id_producto -> (cantidad, valor)
        for p in producciones:
            producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
            precio_venta = producto.Precio_Venta_Recomendado_Producto_Terminado or 0
            valor = p.Cantidad_Restante_Produccion * precio_venta
            valor_stock_pt += valor
            # acumular para el detalle por producto
            if p.Id_Producto_Terminado not in detalle_por_producto:
                detalle_por_producto[p.Id_Producto_Terminado] = [0, 0]
            detalle_por_producto[p.Id_Producto_Terminado][0] += p.Cantidad_Restante_Produccion
            detalle_por_producto[p.Id_Producto_Terminado][1] += valor

        # ===== PASIVOS: suma de saldos de deudas =====
        total_deudas = sesion.query(
            func.coalesce(func.sum(Deuda.Saldo_Actual_Deuda), 0)
        ).scalar()

        # ===== RESULTADO DE LA SEMANA (movimientos de los ultimos N dias) =====
        # TODO: ajustar la definicion de "semana" segun necesidad
        if fecha_balance is None:
            fecha_corte = None
        else:
            fecha_corte = fecha_balance - timedelta(days=dias_semana)

        def suma_movimientos(tipo, desde, hasta):
            q = sesion.query(func.coalesce(func.sum(Movimiento.Monto_Movimiento), 0)).filter(
                Movimiento.Tipo_Movimiento == tipo
            )
            if desde is not None:
                q = q.filter(Movimiento.Fecha_Movimiento >= desde)
            if hasta is not None:
                q = q.filter(Movimiento.Fecha_Movimiento <= hasta)
            return q.scalar()

        ventas_semana = suma_movimientos("ENTRADA", fecha_corte, fecha_balance)
        # Compras + gastos son ambos SALIDA; aqui los juntamos como salidas de la semana
        # TODO: si quieres separar compras de gastos, usar el grupo o el vinculo a Compra
        salidas_semana = suma_movimientos("SALIDA", fecha_corte, fecha_balance)
        compras_semana = salidas_semana   # aproximacion; refinar con grupos
        gastos_semana = 0                  # placeholder hasta separar por grupo

        # ===== ESCENARIOS y PATRIMONIO =====
        total_activos_fijos = total_inmuebles + total_equipos + total_otros
        escenario_c = total_efectivo - total_deudas
        escenario_b = total_efectivo + valor_stock_mp + valor_stock_pt - total_deudas
        escenario_a = total_efectivo + valor_stock_mp + valor_stock_pt + total_activos_fijos - total_deudas
        patrimonio = escenario_a   # patrimonio = mejor escenario (todo el activo - pasivo)

        # ===== CREAR LA FOTO =====
        balance = Balance(
            Fecha_Balance=fecha_balance,
            Total_Efectivo=total_efectivo,
            Total_Inmuebles=total_inmuebles,
            Total_Equipos=total_equipos,
            Total_Otros_Activos=total_otros,
            Valor_Stock_Materia_Prima=valor_stock_mp,
            Valor_Stock_Producto_Terminado=valor_stock_pt,
            Total_Deudas=total_deudas,
            Ventas_Semana=ventas_semana,
            Compras_Semana=compras_semana,
            Gastos_Semana=gastos_semana,
            Escenario_A=escenario_a,
            Escenario_B=escenario_b,
            Escenario_C=escenario_c,
            Patrimonio=patrimonio,
        )
        sesion.add(balance)
        sesion.flush()  # para obtener el Id_Balance

        # Detalle por producto
        for id_prod, (cantidad, valor) in detalle_por_producto.items():
            sesion.add(Balance_Detalle_Producto(
                Id_Balance=balance.Id_Balance,
                Id_Producto_Terminado=id_prod,
                Cantidad_En_Stock=cantidad,
                Valor_En_Stock=valor,
            ))

        sesion.commit()
        return balance

    except Exception as e:
        sesion.rollback()
        raise e