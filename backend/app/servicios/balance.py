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
from app.config import UMBRAL_STOCK_MINIMO
from app.models import (
    Balance, Balance_Detalle_Producto,
    Cliente, Cuenta, Deuda, Activo, Tipo_Bien,
    Compra, Detalle_Venta, Materia_Prima, Pago_Trabajador, Produccion,
    Producto_Intermedio, Producto_Terminado, Venta,
    Movimiento, Produccion_Intermedio,
    Registro_Trabajador, Trabajador,
)


def serializar_balance(balance):
    """
    Convierte una foto de Balance guardada en el dict que consume la API
    (mismos campos y nombres que usa el frontend). Se usa para la ultima
    foto y para el listado del historico (comparativa 4.4), asi ambos
    endpoints devuelven siempre la misma forma sin duplicar la logica.
    """
    total_inmuebles = float(balance.Total_Inmuebles or 0)
    total_equipos = float(balance.Total_Equipos or 0)
    total_otros = float(balance.Total_Otros_Activos or 0)
    activos_fijos = total_inmuebles + total_equipos + total_otros
    return {
        "id_balance": balance.Id_Balance,
        "fecha": str(balance.Fecha_Balance),
        "efectivo": float(balance.Total_Efectivo or 0),
        "stock_materia_prima": float(balance.Valor_Stock_Materia_Prima or 0),
        "stock_producto_intermedio": float(balance.Valor_Stock_Intermedio or 0),
        "valor_horas_standby": float(balance.Valor_Horas_Standby or 0),
        "stock_producto_terminado": float(balance.Valor_Stock_Producto_Terminado or 0),
        "stock_producto_terminado_conservador": float(balance.Valor_Stock_Producto_Terminado_Conservador or 0),
        "deudas": float(balance.Total_Deudas or 0),
        "activos_fijos": round(activos_fijos, 2),
        "total_inmuebles": round(total_inmuebles, 2),
        "total_equipos": round(total_equipos, 2),
        "total_otros": round(total_otros, 2),
        "escenario_c": float(balance.Escenario_C or 0),
        "escenario_b": float(balance.Escenario_B or 0),
        "escenario_a": float(balance.Escenario_A or 0),
        "patrimonio": float(balance.Patrimonio or 0),
        "ventas": float(balance.Ventas_Semana or 0),
        "compras": float(balance.Compras_Semana or 0),
        "gastos": float(balance.Gastos_Semana or 0),
        # None (no 0): las fotos tomadas antes de esta columna no tienen este dato
        "pagos": float(balance.Pagos_Semana) if balance.Pagos_Semana is not None else None,
    }


def calcular_estado_actual(sesion):
    """
    Calcula el estado actual de la fabrica con desglose completo,
    SIN guardar nada (vista previa). Devuelve un dict listo para la API.

    Los escenarios se distinguen por lo que suman al efectivo (menos deudas):
      C = solo efectivo
      B = C + inventarios valorizados + horas en stand-by
      A = B + activos fijos  (el "todo")
    """
    # Efectivo: suma de saldos de cuentas
    efectivo = sesion.query(func.coalesce(func.sum(Cuenta.Saldo_Actual_Cuenta), 0)).scalar()

    # Stock materia prima valorizado (restante x precio unitario del lote)
    compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()
    stock_mp = sum(float(c.Cantidad_Restante_Compra) * (float(c.Precio_Compra) / float(c.Cantidad_Compra)) for c in compras)

    # Stock de producto INTERMEDIO valorizado (a su costo unitario)
    prods_int = sesion.query(Produccion_Intermedio).filter(Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO).all()
    stock_int = sum(float(p.Cantidad_Restante_Producida) * float(p.Costo_Unitario_Produccion_Intermedio or 0) for p in prods_int)

    # Horas de trabajo en stand-by (pagadas/registradas pero no consumidas)
    jornadas = sesion.query(Registro_Trabajador).filter(Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0).all()
    valor_horas = 0
    for j in jornadas:
        trab = sesion.get(Trabajador, j.Id_Trabajador)
        valor_horas += float(j.Horas_Restante_Registro_Trabajador) * float(trab.Pago_Trabajador or 0) if trab else 0

    # Stock producto terminado valorizado a precio recomendado (para los
    # escenarios de liquidez) y, aparte, a "costo o mercado, el menor"
    # (para el patrimonio contable, ver 4.3 en MEJORAS_FUTURAS.md): no
    # reconoce la ganancia de lo que todavia no se vendio.
    producciones = sesion.query(Produccion).filter(Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO).all()
    stock_pt = 0
    stock_pt_conservador = 0
    for p in producciones:
        prod = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        precio_venta = float(prod.Precio_Venta_Recomendado_Producto_Terminado or 0) if prod else 0
        costo = float(p.Precio_Unitario_Producto_Terminado or 0)
        cantidad = float(p.Cantidad_Restante_Produccion)
        stock_pt += cantidad * precio_venta
        stock_pt_conservador += cantidad * min(costo, precio_venta)

    # Deudas
    deudas = sesion.query(func.coalesce(func.sum(Deuda.Saldo_Actual_Deuda), 0)).scalar()

    # Activos fijos, desglosados por categoria explicita del tipo de bien
    # (ver 4.2 en MEJORAS_FUTURAS.md). La suma de las tres es "activos_fijos",
    # lo unico que diferencia el Escenario A del B.
    def suma_activos_por_categoria(categoria):
        return sesion.query(
            func.coalesce(func.sum(Activo.Valor_Activo), 0)
        ).join(Tipo_Bien, Activo.Id_Tipo_Bien == Tipo_Bien.Id_Tipo_Bien).filter(
            Tipo_Bien.Categoria_Tipo_Bien == categoria
        ).scalar()

    total_inmuebles = float(suma_activos_por_categoria("INMUEBLE"))
    total_equipos = float(suma_activos_por_categoria("EQUIPO"))
    total_otros = float(suma_activos_por_categoria("OTRO"))
    activos_fijos = total_inmuebles + total_equipos + total_otros

    efectivo = float(efectivo)
    deudas = float(deudas)
    escenario_c = efectivo - deudas
    escenario_b = efectivo + stock_mp + stock_int + stock_pt + valor_horas - deudas
    escenario_a = escenario_b + activos_fijos
    # Patrimonio contable puro (4.3): igual que Escenario A pero con el stock
    # de producto terminado a costo o mercado (el menor), no a precio de venta.
    patrimonio = efectivo + stock_mp + stock_int + stock_pt_conservador + valor_horas + activos_fijos - deudas

    return {
        "efectivo": round(efectivo, 2),
        "stock_materia_prima": round(stock_mp, 2),
        "stock_producto_terminado": round(stock_pt, 2),
        "stock_producto_terminado_conservador": round(stock_pt_conservador, 2),
        "deudas": round(deudas, 2),
        "activos_fijos": round(activos_fijos, 2),
        "total_inmuebles": round(total_inmuebles, 2),
        "total_equipos": round(total_equipos, 2),
        "total_otros": round(total_otros, 2),
        "escenario_c": round(escenario_c, 2),
        "escenario_b": round(escenario_b, 2),
        "escenario_a": round(escenario_a, 2),
        "patrimonio": round(patrimonio, 2),
        "stock_producto_intermedio": round(stock_int, 2),
        "valor_horas_standby": round(valor_horas, 2),
    }


def resumen_desde_ultima_foto(sesion):
    """
    Resumen dia a dia de lo que paso en la fabrica desde la ultima foto de
    balance guardada hasta hoy, SIN necesidad de tomar una foto nueva. Sirve
    para revisar el avance dia a dia (o notar si algo no se registro) sin
    esperar al cierre semanal. Si no hay ninguna foto guardada, resume desde
    el principio.

    Separa compras / pagos a trabajadores / gastos usando el vinculo real
    (Compra.Id_Movimiento, Pago_Trabajador.Id_Movimiento) en vez de asumir
    que toda SALIDA es una compra (ese era el bug de 4.1: antes se sumaba
    todo como "compras_semana" y "gastos_semana" quedaba en cero fijo).
    """
    ultimo = sesion.query(Balance).order_by(Balance.Id_Balance.desc()).first()
    desde = ultimo.Fecha_Balance if ultimo else None
    hasta = date.today()

    eventos_por_dia = {}

    def agregar(fecha, texto):
        eventos_por_dia.setdefault(fecha, []).append(texto)

    # ---- Compras ----
    q = sesion.query(Compra)
    if desde:
        q = q.filter(Compra.Fecha_Compra > desde)
    compras = q.all()
    total_compras = 0.0
    ids_movimiento_compra = set()
    for c in compras:
        materia = sesion.get(Materia_Prima, c.Id_Materia_Prima)
        nombre = materia.Descripcion_Materia_Prima if materia else "?"
        unidad = materia.Unidad_Materia_Prima if materia else ""
        agregar(c.Fecha_Compra, f"Compra de: {nombre} {float(c.Cantidad_Compra)} {unidad} a {float(c.Precio_Compra)} Bs")
        total_compras += float(c.Precio_Compra)
        if c.Id_Movimiento:
            ids_movimiento_compra.add(c.Id_Movimiento)

    # ---- Pagos a trabajadores ----
    q = sesion.query(Pago_Trabajador)
    if desde:
        q = q.filter(Pago_Trabajador.Fecha_Pago_Trabajador > desde)
    pagos = q.all()
    total_pagos = 0.0
    ids_movimiento_pago = set()
    for p in pagos:
        trab = sesion.get(Trabajador, p.Id_Trabajador)
        nombre = trab.Nombre_Trabajador if trab else "?"
        agregar(p.Fecha_Pago_Trabajador, f"Pago a: {nombre} {float(p.Monto_Real_Pago)} Bs")
        total_pagos += float(p.Monto_Real_Pago)
        if p.Id_Movimiento:
            ids_movimiento_pago.add(p.Id_Movimiento)

    # ---- Gastos: movimientos SALIDA que no son ni compra ni pago ----
    q = sesion.query(Movimiento).filter(Movimiento.Tipo_Movimiento == "SALIDA")
    if desde:
        q = q.filter(Movimiento.Fecha_Movimiento > desde)
    total_gastos = 0.0
    for m in q.all():
        if m.Id_Movimiento in ids_movimiento_compra or m.Id_Movimiento in ids_movimiento_pago:
            continue
        agregar(m.Fecha_Movimiento, f"Gasto: {m.Descripcion_Movimiento} {float(m.Monto_Movimiento)} Bs")
        total_gastos += float(m.Monto_Movimiento)

    # ---- Producciones intermedias ----
    q = sesion.query(Produccion_Intermedio)
    if desde:
        q = q.filter(Produccion_Intermedio.Fecha_Produccion_Intermedio > desde)
    for p in q.all():
        producto = sesion.get(Producto_Intermedio, p.Id_Producto_Intermedio)
        nombre = producto.Descripcion_Producto_Intermedio if producto else "?"
        agregar(p.Fecha_Produccion_Intermedio, f"Producto Intermedio: {nombre} {float(p.Cantidad_Producida)}")

    # ---- Producciones terminadas ----
    q = sesion.query(Produccion)
    if desde:
        q = q.filter(Produccion.Fecha_Produccion > desde)
    for p in q.all():
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        nombre = producto.Descripcion_Producto_Terminado if producto else "?"
        agregar(p.Fecha_Produccion, f"Producto Terminado: {nombre} {float(p.Cantidad_Producida_Produccion)}")

    # ---- Ventas ----
    q = sesion.query(Venta)
    if desde:
        q = q.filter(Venta.Fecha_Venta > desde)
    total_ventas = 0.0
    for v in q.all():
        cliente = sesion.get(Cliente, v.Id_Cliente)
        nombre = cliente.Nombre_Cliente if cliente else "?"
        detalles = sesion.query(Detalle_Venta).filter_by(Id_Venta=v.Id_Venta).all()
        total_venta = sum(float(d.Cantidad_Venta) * float(d.Precio_Venta_Real) for d in detalles)
        agregar(v.Fecha_Venta, f"Venta a: {nombre} total de {total_venta} Bs")
        total_ventas += total_venta

    dias = [
        {"fecha": str(fecha), "eventos": textos}
        for fecha, textos in sorted(eventos_por_dia.items())
    ]

    return {
        "desde": str(desde) if desde else None,
        "hasta": str(hasta),
        "ventas": round(total_ventas, 2),
        "compras": round(total_compras, 2),
        "gastos": round(total_gastos, 2),
        "pagos": round(total_pagos, 2),
        "dias": dias,
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
        # Suma de valores de activos segun la categoria explicita de su tipo
        # de bien (ver 4.2 en MEJORAS_FUTURAS.md; antes se adivinaba
        # buscando la palabra en el nombre, fragil si el nombre no la tenia).
        def suma_activos_por_categoria(categoria):
            return sesion.query(
                func.coalesce(func.sum(Activo.Valor_Activo), 0)
            ).join(Tipo_Bien, Activo.Id_Tipo_Bien == Tipo_Bien.Id_Tipo_Bien).filter(
                Tipo_Bien.Categoria_Tipo_Bien == categoria
            ).scalar()

        total_inmuebles = suma_activos_por_categoria("INMUEBLE")
        total_equipos = suma_activos_por_categoria("EQUIPO")
        total_otros = suma_activos_por_categoria("OTRO")

        # ===== INVENTARIOS VALORIZADOS =====
        # Stock de materia prima: restante x precio unitario del lote
        compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()
        valor_stock_mp = 0
        for c in compras:
            precio_unit = c.Precio_Compra / c.Cantidad_Compra
            valor_stock_mp += c.Cantidad_Restante_Compra * precio_unit

        # Stock de producto intermedio valorizado (a su costo unitario)
        prods_int = sesion.query(Produccion_Intermedio).filter(
            Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO
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

        # Stock de producto terminado: a precio recomendado de venta (para
        # los escenarios de liquidez) y, aparte, a costo o mercado -el menor-
        # (para el patrimonio contable, ver 4.3 en MEJORAS_FUTURAS.md).
        producciones = sesion.query(Produccion).filter(
            Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO
        ).all()
        valor_stock_pt = 0
        valor_stock_pt_conservador = 0
        detalle_por_producto = {}  # id_producto -> (cantidad, valor)
        for p in producciones:
            producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
            precio_venta = producto.Precio_Venta_Recomendado_Producto_Terminado or 0
            costo = p.Precio_Unitario_Producto_Terminado or 0
            valor = p.Cantidad_Restante_Produccion * precio_venta
            valor_stock_pt += valor
            valor_stock_pt_conservador += p.Cantidad_Restante_Produccion * min(costo, precio_venta)
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

        # Compras: usa el vinculo real Compra.Id_Movimiento, no una suposicion.
        q_compras = sesion.query(Compra)
        if fecha_corte is not None:
            q_compras = q_compras.filter(Compra.Fecha_Compra >= fecha_corte)
        if fecha_balance is not None:
            q_compras = q_compras.filter(Compra.Fecha_Compra <= fecha_balance)
        compras_semana_lista = q_compras.all()
        compras_semana = sum(c.Precio_Compra for c in compras_semana_lista)
        ids_movimiento_compra = {c.Id_Movimiento for c in compras_semana_lista if c.Id_Movimiento}

        # Pagos a trabajadores: tienen su propio vinculo, no son "gasto".
        q_pagos = sesion.query(Pago_Trabajador)
        if fecha_corte is not None:
            q_pagos = q_pagos.filter(Pago_Trabajador.Fecha_Pago_Trabajador >= fecha_corte)
        if fecha_balance is not None:
            q_pagos = q_pagos.filter(Pago_Trabajador.Fecha_Pago_Trabajador <= fecha_balance)
        pagos_semana_lista = q_pagos.all()
        pagos_semana = sum(p.Monto_Real_Pago for p in pagos_semana_lista)
        ids_movimiento_pago = {p.Id_Movimiento for p in pagos_semana_lista if p.Id_Movimiento}

        # Gastos: lo que queda de las SALIDA que no es compra ni pago.
        q_salidas = sesion.query(Movimiento).filter(Movimiento.Tipo_Movimiento == "SALIDA")
        if fecha_corte is not None:
            q_salidas = q_salidas.filter(Movimiento.Fecha_Movimiento >= fecha_corte)
        if fecha_balance is not None:
            q_salidas = q_salidas.filter(Movimiento.Fecha_Movimiento <= fecha_balance)
        gastos_semana = sum(
            m.Monto_Movimiento for m in q_salidas.all()
            if m.Id_Movimiento not in ids_movimiento_compra and m.Id_Movimiento not in ids_movimiento_pago
        )

        # ===== ESCENARIOS y PATRIMONIO =====
        total_activos_fijos = total_inmuebles + total_equipos + total_otros
        escenario_c = total_efectivo - total_deudas
        escenario_b = total_efectivo + valor_stock_mp + valor_stock_intermedio + valor_stock_pt + valor_horas_standby - total_deudas
        escenario_a = total_efectivo + valor_stock_mp + valor_stock_intermedio + valor_stock_pt + valor_horas_standby + total_activos_fijos - total_deudas
        # Patrimonio contable puro (4.3): igual que Escenario A pero con el
        # stock de producto terminado a costo o mercado (el menor), no a
        # precio de venta -no reconoce ganancia de lo que no se vendio-.
        # Ya no es un alias de Escenario A (que sigue siendo la vista de
        # liquidez: "cuanto tendria si liquido todo hoy").
        patrimonio = (
            total_efectivo + valor_stock_mp + valor_stock_intermedio
            + valor_stock_pt_conservador + valor_horas_standby
            + total_activos_fijos - total_deudas
        )

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
            Pagos_Semana=pagos_semana,
            Escenario_A=escenario_a,
            Escenario_B=escenario_b,
            Escenario_C=escenario_c,
            Patrimonio=patrimonio,
            Valor_Stock_Intermedio=valor_stock_intermedio,
            Valor_Horas_Standby=valor_horas_standby,
            Valor_Stock_Producto_Terminado_Conservador=valor_stock_pt_conservador,
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