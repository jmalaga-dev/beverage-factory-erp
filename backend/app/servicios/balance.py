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
from decimal import Decimal
from sqlalchemy import func
from app.config import UMBRAL_STOCK_MINIMO
from app.models import (
    Balance, Balance_Detalle,
    Cliente, Cuenta, Deuda, Activo, Tipo_Bien,
    Compra, Detalle_Venta, Gasto_Extra, Gasto_Extra_Mes, Grupo_Movimiento,
    Item_Absorcion, Materia_Prima, Pago_Trabajador,
    Produccion, Producto_Intermedio, Producto_Terminado, Venta,
    Movimiento, Produccion_Intermedio,
    Registro_Trabajador, Trabajador,
)
from app.servicios.trabajadores import tarifa_hora


def valor_utensilios_sin_absorber(sesion):
    """
    Valor de los items de absorcion (utensilios, feriados) ya comprados pero
    todavia NO trasladados al costo de ninguna botella (mejora 4.8).

    Un item se compra por un costo y se reparte entre N botellas estimadas.
    Mientras queden botellas por absorber, esa fraccion del costo ya se pago
    pero no esta en el costo de ningun producto: es valor que la fabrica
    tiene y que no aparece ni en efectivo, ni en stock, ni en activos fijos.

    La parte sin absorber es proporcional a las botellas que faltan:
        costo * botellas_restantes / botellas_estimadas

    Los items ya agotados (restantes = 0) aportan 0: su costo entero ya vive
    dentro del costo de las botellas que produjeron.

    Devuelve Decimal (no float) porque tomar_balance suma este valor con
    montos que vienen de la BD como Numeric, y Decimal + float es un error
    de tipos en Python. calcular_estado_actual, que trabaja en float, lo
    convierte al recibirlo.
    """
    items = sesion.query(Item_Absorcion).filter(
        Item_Absorcion.Botellas_Restantes_Item_Absorcion > 0,
        Item_Absorcion.Botellas_Estimadas_Item_Absorcion > 0,
    ).all()
    total = Decimal("0")
    for i in items:
        total += (
            i.Costo_Item_Absorcion
            * i.Botellas_Restantes_Item_Absorcion
            / i.Botellas_Estimadas_Item_Absorcion
        )
    return total


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
        # None (no 0), igual que Pagos_Semana: las fotos anteriores a esta
        # columna (021) no tienen el dato. Con 0 la comparativa mostraria un
        # alza inventada (de 0 a lo que valga hoy); con None muestra "—".
        "utensilios_sin_absorber": (
            float(balance.Valor_Utensilios_Sin_Absorber)
            if balance.Valor_Utensilios_Sin_Absorber is not None else None
        ),
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
        "servicios": (
            float(balance.Servicios_Semana) if balance.Servicios_Semana is not None else None
        ),
    }


def calcular_estado_actual(sesion):
    """
    Calcula el estado actual de la fabrica con desglose completo,
    SIN guardar nada (vista previa). Devuelve un dict listo para la API.

    Los escenarios se distinguen por lo que suman al efectivo (menos deudas):
      C = solo efectivo
      B = C + inventarios valorizados + horas en stand-by + utensilios sin absorber
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
        valor_horas += float(j.Horas_Restante_Registro_Trabajador) * float(tarifa_hora(trab)) if trab else 0

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

    # Utensilios/feriados comprados pero todavia no absorbidos (4.8)
    utensilios = float(valor_utensilios_sin_absorber(sesion))

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
    escenario_b = efectivo + stock_mp + stock_int + stock_pt + valor_horas + utensilios - deudas
    escenario_a = escenario_b + activos_fijos
    # Patrimonio contable puro (4.3): igual que Escenario A pero con el stock
    # de producto terminado a costo o mercado (el menor), no a precio de venta.
    patrimonio = (
        efectivo + stock_mp + stock_int + stock_pt_conservador + valor_horas
        + utensilios + activos_fijos - deudas
    )

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
        "utensilios_sin_absorber": round(utensilios, 2),
    }


def resumen_desde_ultima_foto(sesion):
    """
    Resumen dia a dia de lo que paso en la fabrica desde la ultima foto de
    balance guardada hasta hoy, SIN necesidad de tomar una foto nueva. Sirve
    para revisar el avance dia a dia (o notar si algo no se registro) sin
    esperar al cierre semanal. Si no hay ninguna foto guardada, resume desde
    el principio.

    Separa compras / pagos a trabajadores / servicios / gastos usando el
    vinculo real (Compra.Id_Movimiento, Pago_Trabajador.Id_Movimiento,
    Gasto_Extra_Mes.Id_Movimiento) en vez de asumir que toda SALIDA es una
    compra (ese era el bug de 4.1: antes se sumaba todo como "compras_semana"
    y "gastos_semana" quedaba en cero fijo).

    "Gastos" es el residuo: lo que sale y no es ninguna de las otras tres.
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

    # ---- Servicios (gastos extra: luz, agua, internet, telefono, impuestos) ----
    # Cuarta forma en que sale la plata, con su propia tabla igual que las
    # compras y los pagos. El monto sale de Gasto_Extra_Mes, no del libro de
    # movimientos: los meses migrados del excel V1 quedaron pagados sin generar
    # movimiento, asi que contarlos desde Movimiento perderia casi toda la
    # historia. Es el mismo criterio que compras_semana, que suma Compra y no
    # los movimientos (hay compras sin Id_Movimiento y aun asi cuentan).
    q = sesion.query(Gasto_Extra_Mes).filter(
        Gasto_Extra_Mes.Fecha_Pago_Gasto_Extra_Mes.isnot(None)
    )
    if desde:
        q = q.filter(Gasto_Extra_Mes.Fecha_Pago_Gasto_Extra_Mes > desde)
    total_servicios = 0.0
    ids_movimiento_servicio = set()
    for s in q.all():
        gasto = sesion.get(Gasto_Extra, s.Id_Gasto_Extra)
        nombre = gasto.Descripcion_Gasto_Extra if gasto else "?"
        agregar(s.Fecha_Pago_Gasto_Extra_Mes,
                f"Servicio: {nombre} {s.Anio_Mes} {float(s.Monto_Gasto_Extra_Mes)} Bs")
        total_servicios += float(s.Monto_Gasto_Extra_Mes)
        if s.Id_Movimiento:
            ids_movimiento_servicio.add(s.Id_Movimiento)

    # ---- Gastos: movimientos SALIDA que no son ni compra, ni pago, ni servicio ----
    q = sesion.query(Movimiento).filter(Movimiento.Tipo_Movimiento == "SALIDA")
    if desde:
        q = q.filter(Movimiento.Fecha_Movimiento > desde)
    total_gastos = 0.0
    # Desglose por grupo (mejora 10.26): el total solo dice cuanto, no en que.
    # Se acumula aca mismo para no recorrer los movimientos dos veces.
    gastos_por_grupo = {}
    for m in q.all():
        if (m.Id_Movimiento in ids_movimiento_compra
                or m.Id_Movimiento in ids_movimiento_pago
                or m.Id_Movimiento in ids_movimiento_servicio):
            continue
        agregar(m.Fecha_Movimiento, f"Gasto: {m.Descripcion_Movimiento} {float(m.Monto_Movimiento)} Bs")
        total_gastos += float(m.Monto_Movimiento)
        grupo = sesion.get(Grupo_Movimiento, m.Id_Grupo_Movimiento) if m.Id_Grupo_Movimiento else None
        nombre = grupo.Nombre_Grupo_Movimiento if grupo else "(sin grupo)"
        gastos_por_grupo[nombre] = gastos_por_grupo.get(nombre, 0.0) + float(m.Monto_Movimiento)

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
        "servicios": round(total_servicios, 2),
        # De mayor a menor: en pantalla se leen como subcomponentes de "Gastos"
        # y lo util es ver arriba en que se fue la plata.
        "gastos_por_grupo": [
            {"grupo": g, "monto": round(v, 2)}
            for g, v in sorted(gastos_por_grupo.items(), key=lambda x: -x[1])
        ],
        "dias": dias,
    }


def tomar_balance(sesion, fecha_balance=None, dias_semana=7):
    """
    Toma una foto del balance actual de la fabrica.
    fecha_balance: fecha de la foto (referencia para "la semana"). None = hoy.
    dias_semana: cuantos dias hacia atras cuentan como "esta semana".
    Devuelve el objeto Balance creado.
    """
    # Sin fecha explicita, hoy: misma convencion que el resto del backend
    # (6.10). Antes quedaba en None y el INSERT fallaba con un "Error de base
    # de datos" generico; no se notaba porque la pantalla siempre manda fecha.
    fecha_balance = fecha_balance or date.today()

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
        # Mientras se valoriza cada bloque se acumula tambien su detalle por
        # item, para guardarlo en la foto (4.6). Estructura comun:
        #   {tipo: {id_item: [descripcion, cantidad, valor]}}
        detalle_foto = {"MP": {}, "INTERMEDIO": {}, "TERMINADO": {}, "ACTIVO": {},
                        "GASTO_GRUPO": {}}

        def acumular(tipo, id_item, descripcion, cantidad, valor):
            fila = detalle_foto[tipo].setdefault(id_item, [descripcion, 0, 0])
            fila[1] += cantidad
            fila[2] += valor

        compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()
        valor_stock_mp = 0
        for c in compras:
            precio_unit = c.Precio_Compra / c.Cantidad_Compra
            valor = c.Cantidad_Restante_Compra * precio_unit
            valor_stock_mp += valor
            mp = sesion.get(Materia_Prima, c.Id_Materia_Prima)
            acumular("MP", c.Id_Materia_Prima,
                     mp.Descripcion_Materia_Prima if mp else f"(materia {c.Id_Materia_Prima})",
                     c.Cantidad_Restante_Compra, valor)

        # Stock de producto intermedio valorizado (a su costo unitario)
        prods_int = sesion.query(Produccion_Intermedio).filter(
            Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO
        ).all()
        valor_stock_intermedio = 0
        for p in prods_int:
            valor = p.Cantidad_Restante_Producida * (p.Costo_Unitario_Produccion_Intermedio or 0)
            valor_stock_intermedio += valor
            pi = sesion.get(Producto_Intermedio, p.Id_Producto_Intermedio)
            acumular("INTERMEDIO", p.Id_Producto_Intermedio,
                     pi.Descripcion_Producto_Intermedio if pi else f"(intermedio {p.Id_Producto_Intermedio})",
                     p.Cantidad_Restante_Producida, valor)

        # Horas de trabajo en stand-by (registradas pero no consumidas)
        jornadas_pend = sesion.query(Registro_Trabajador).filter(
            Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0
        ).all()
        valor_horas_standby = 0
        for j in jornadas_pend:
            trab = sesion.get(Trabajador, j.Id_Trabajador)
            if trab:
                valor_horas_standby += j.Horas_Restante_Registro_Trabajador * tarifa_hora(trab)

        # Stock de producto terminado: a precio recomendado de venta (para
        # los escenarios de liquidez) y, aparte, a costo o mercado -el menor-
        # (para el patrimonio contable, ver 4.3 en MEJORAS_FUTURAS.md).
        producciones = sesion.query(Produccion).filter(
            Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO
        ).all()
        valor_stock_pt = 0
        valor_stock_pt_conservador = 0
        for p in producciones:
            producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
            precio_venta = producto.Precio_Venta_Recomendado_Producto_Terminado or 0
            costo = p.Precio_Unitario_Producto_Terminado or 0
            valor = p.Cantidad_Restante_Produccion * precio_venta
            valor_stock_pt += valor
            valor_stock_pt_conservador += p.Cantidad_Restante_Produccion * min(costo, precio_venta)
            acumular("TERMINADO", p.Id_Producto_Terminado,
                     producto.Descripcion_Producto_Terminado if producto else f"(producto {p.Id_Producto_Terminado})",
                     p.Cantidad_Restante_Produccion, valor)

        # Detalle de activos fijos: la foto ya guardaba los tres TOTALES
        # (inmuebles/equipos/otros), pero no que activos los componian.
        for a in sesion.query(Activo).all():
            tipo_bien = sesion.get(Tipo_Bien, a.Id_Tipo_Bien) if a.Id_Tipo_Bien else None
            nombre = a.Descripcion_Activo or "(activo sin descripción)"
            if tipo_bien:
                nombre = f"{nombre} ({tipo_bien.Nombre_Tipo_Bien})"
            # Sin cantidad: un activo es una unidad, lo que importa es su valor.
            acumular("ACTIVO", a.Id_Activo, nombre, 0, a.Valor_Activo or 0)

        # Utensilios/feriados comprados pero todavia no absorbidos (4.8)
        valor_utensilios = valor_utensilios_sin_absorber(sesion)

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

        # Servicios (gastos extra): tambien tienen su propio vinculo. El monto
        # sale de Gasto_Extra_Mes, igual que las compras salen de Compra: los
        # meses migrados del excel V1 se pagaron sin generar movimiento, asi
        # que contarlos desde Movimiento perderia casi toda la historia.
        q_serv = sesion.query(Gasto_Extra_Mes).filter(
            Gasto_Extra_Mes.Fecha_Pago_Gasto_Extra_Mes.isnot(None)
        )
        if fecha_corte is not None:
            q_serv = q_serv.filter(Gasto_Extra_Mes.Fecha_Pago_Gasto_Extra_Mes >= fecha_corte)
        if fecha_balance is not None:
            q_serv = q_serv.filter(Gasto_Extra_Mes.Fecha_Pago_Gasto_Extra_Mes <= fecha_balance)
        servicios_semana_lista = q_serv.all()
        servicios_semana = sum(s.Monto_Gasto_Extra_Mes for s in servicios_semana_lista)
        ids_movimiento_servicio = {
            s.Id_Movimiento for s in servicios_semana_lista if s.Id_Movimiento
        }

        # Gastos: lo que queda de las SALIDA que no es compra, ni pago, ni servicio.
        q_salidas = sesion.query(Movimiento).filter(Movimiento.Tipo_Movimiento == "SALIDA")
        if fecha_corte is not None:
            q_salidas = q_salidas.filter(Movimiento.Fecha_Movimiento >= fecha_corte)
        if fecha_balance is not None:
            q_salidas = q_salidas.filter(Movimiento.Fecha_Movimiento <= fecha_balance)
        # Ademas del total, se congela el desglose por grupo (10.26) como un
        # bloque mas del detalle de la foto. Va con la descripcion COPIADA, no
        # por relacion, por el mismo motivo que el resto de los bloques: un
        # grupo puede renombrarse o borrarse y la foto tiene que seguir
        # leyendose tal como era ese dia.
        gastos_semana = 0
        for m in q_salidas.all():
            if (m.Id_Movimiento in ids_movimiento_compra
                    or m.Id_Movimiento in ids_movimiento_pago
                    or m.Id_Movimiento in ids_movimiento_servicio):
                continue
            gastos_semana += m.Monto_Movimiento
            grupo = (sesion.get(Grupo_Movimiento, m.Id_Grupo_Movimiento)
                     if m.Id_Grupo_Movimiento else None)
            acumular("GASTO_GRUPO", m.Id_Grupo_Movimiento or 0,
                     grupo.Nombre_Grupo_Movimiento if grupo else "(sin grupo)",
                     0, m.Monto_Movimiento)

        # ===== ESCENARIOS y PATRIMONIO =====
        total_activos_fijos = total_inmuebles + total_equipos + total_otros
        escenario_c = total_efectivo - total_deudas
        escenario_b = total_efectivo + valor_stock_mp + valor_stock_intermedio + valor_stock_pt + valor_horas_standby + valor_utensilios - total_deudas
        escenario_a = escenario_b + total_activos_fijos
        # Patrimonio contable puro (4.3): igual que Escenario A pero con el
        # stock de producto terminado a costo o mercado (el menor), no a
        # precio de venta -no reconoce ganancia de lo que no se vendio-.
        # Ya no es un alias de Escenario A (que sigue siendo la vista de
        # liquidez: "cuanto tendria si liquido todo hoy").
        patrimonio = (
            total_efectivo + valor_stock_mp + valor_stock_intermedio
            + valor_stock_pt_conservador + valor_horas_standby
            + valor_utensilios + total_activos_fijos - total_deudas
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
            Servicios_Semana=servicios_semana,
            Escenario_A=escenario_a,
            Escenario_B=escenario_b,
            Escenario_C=escenario_c,
            Patrimonio=patrimonio,
            Valor_Stock_Intermedio=valor_stock_intermedio,
            Valor_Horas_Standby=valor_horas_standby,
            Valor_Stock_Producto_Terminado_Conservador=valor_stock_pt_conservador,
            Valor_Utensilios_Sin_Absorber=valor_utensilios,
        )
        sesion.add(balance)
        sesion.flush()  # para obtener el Id_Balance

        # Detalle por item de los cuatro bloques (4.6). La descripcion se
        # guarda copiada: la foto tiene que poder leerse tal como era aunque
        # el item se renombre o se borre despues.
        for tipo, items in detalle_foto.items():
            for id_item, (descripcion, cantidad, valor) in items.items():
                sesion.add(Balance_Detalle(
                    Id_Balance=balance.Id_Balance,
                    Tipo_Detalle=tipo,
                    Id_Item_Balance_Detalle=id_item,
                    Descripcion_Balance_Detalle=descripcion,
                    Cantidad_Balance_Detalle=cantidad,
                    Valor_Balance_Detalle=valor,
                ))

        sesion.commit()
        return balance

    except Exception as e:
        sesion.rollback()
        raise e