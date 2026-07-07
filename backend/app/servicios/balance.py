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
    Movimiento, Produccion_Intermedio,
    Registro_Trabajador, Trabajador,
)


def calcular_estado_actual(sesion):
    """
    Calcula el estado actual de la fabrica con desglose completo,
    SIN guardar nada (vista previa). Devuelve un dict listo para la API.

    NOTA: aqui escenario_a == escenario_b porque esta vista previa aun no
    suma activos fijos; la foto guardada (tomar_balance) si los incluye.
    """
    # Efectivo: suma de saldos de cuentas
    efectivo = sesion.query(func.coalesce(func.sum(Cuenta.Saldo_Actual_Cuenta), 0)).scalar()

    # Stock materia prima valorizado (restante x precio unitario del lote)
    compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > 0).all()
    stock_mp = sum(float(c.Cantidad_Restante_Compra) * (float(c.Precio_Compra) / float(c.Cantidad_Compra)) for c in compras)

    # Stock de producto INTERMEDIO valorizado (a su costo unitario)
    prods_int = sesion.query(Produccion_Intermedio).filter(Produccion_Intermedio.Cantidad_Restante_Producida > 0).all()
    stock_int = sum(float(p.Cantidad_Restante_Producida) * float(p.Costo_Unitario_Produccion_Intermedio or 0) for p in prods_int)

    # Horas de trabajo en stand-by (pagadas/registradas pero no consumidas)
    jornadas = sesion.query(Registro_Trabajador).filter(Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0).all()
    valor_horas = 0
    for j in jornadas:
        trab = sesion.get(Trabajador, j.Id_Trabajador)
        valor_horas += float(j.Horas_Restante_Registro_Trabajador) * float(trab.Pago_Trabajador or 0) if trab else 0

    # Stock producto terminado valorizado (a precio recomendado)
    producciones = sesion.query(Produccion).filter(Produccion.Cantidad_Restante_Produccion > 0).all()
    stock_pt = 0
    for p in producciones:
        prod = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        precio = float(prod.Precio_Venta_Recomendado_Producto_Terminado or 0) if prod else 0
        stock_pt += float(p.Cantidad_Restante_Produccion) * precio

    # Deudas
    deudas = sesion.query(func.coalesce(func.sum(Deuda.Saldo_Actual_Deuda), 0)).scalar()

    efectivo = float(efectivo)
    deudas = float(deudas)
    escenario_c = efectivo - deudas
    escenario_b = efectivo + stock_mp + stock_int + stock_pt + valor_horas - deudas
    escenario_a = escenario_b  # sin activos fijos por ahora (se suman si los hay)

    return {
        "efectivo": round(efectivo, 2),
        "stock_materia_prima": round(stock_mp, 2),
        "stock_producto_terminado": round(stock_pt, 2),
        "deudas": round(deudas, 2),
        "escenario_c": round(escenario_c, 2),
        "escenario_b": round(escenario_b, 2),
        "escenario_a": round(escenario_a, 2),
        "patrimonio": round(escenario_a, 2),
        "stock_producto_intermedio": round(stock_int, 2),
        "valor_horas_standby": round(valor_horas, 2),
    }


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

        # Stock de producto intermedio valorizado (a su costo unitario)
        prods_int = sesion.query(Produccion_Intermedio).filter(
            Produccion_Intermedio.Cantidad_Restante_Producida > 0
        ).all()
        valor_stock_intermedio = sum(
            p.Cantidad_Restante_Producida * (p.Costo_Unitario_Produccion_Intermedio or 0)
            for p in prods_int
        )

        # Horas de trabajo en stand-by (registradas pero no consumidas)
        jornadas_pend = sesion.query(Registro_Trabajador).filter(
            Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0
        ).all()
        valor_horas_standby = 0
        for j in jornadas_pend:
            trab = sesion.get(Trabajador, j.Id_Trabajador)
            if trab:
                valor_horas_standby += j.Horas_Restante_Registro_Trabajador * (trab.Pago_Trabajador or 0)

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
        escenario_b = total_efectivo + valor_stock_mp + valor_stock_intermedio + valor_stock_pt + valor_horas_standby - total_deudas
        escenario_a = total_efectivo + valor_stock_mp + valor_stock_intermedio + valor_stock_pt + valor_horas_standby + total_activos_fijos - total_deudas
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
            Valor_Stock_Intermedio=valor_stock_intermedio,
            Valor_Horas_Standby=valor_horas_standby,
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