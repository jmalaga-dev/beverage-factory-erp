"""
saldo_producto.py
Acumulador de inversion/ingresos por producto terminado (mejora 2.C).

Responde "¿este producto ya le devolvio a la fabrica lo que costo producirlo?":
  saldo = ingresos acumulados de sus ventas - inversion acumulada en producirlo
Es un acumulado de TODOS los tiempos, por PRODUCTO (no por lote): sirve de base
para el reparto 70/30 de una venta (100% a Fabrica mientras el saldo sea <= 0;
70/30 sobre el excedente una vez que ya rento).

Se calcula al vuelo (no se guarda en una columna): es una suma sobre datos que
ya existen (Produccion + Detalle_Venta), el volumen es chico, y evita el riesgo
de que un total corriente se desincronice del dato real (mismo criterio que
"no duplicar" usado en 1.4 y en el resto del proyecto).
"""

from app.models import (
    Produccion, Detalle_Venta, Venta, Producto_Terminado, Movimiento_Inventario,
)
from app.config import REPARTO_VENTA_FABRICA


def dividir_ingreso(saldo_actual, ingreso, pct_fabrica=None):
    """Divide el ingreso de una venta entre Fábrica y Casa según el saldo del
    producto (mejora 2.C). Mientras el producto no recuperó su inversión
    (saldo < 0), el 100% va a Fábrica hasta llegar a 0; el excedente (y todo el
    ingreso si el saldo ya es >= 0) se reparte pct_fabrica a Fábrica y el resto
    a Casa. Devuelve (a_fabrica, a_casa). No toca la BD."""
    if pct_fabrica is None:
        pct_fabrica = REPARTO_VENTA_FABRICA
    if saldo_actual >= 0:
        a_fabrica = ingreso * pct_fabrica
    else:
        faltante = -saldo_actual   # cuánto falta para recuperar la inversión
        if ingreso <= faltante:
            a_fabrica = ingreso    # todavía no cruza el cero: todo a Fábrica
        else:
            remanente = ingreso - faltante
            a_fabrica = faltante + remanente * pct_fabrica
    a_casa = ingreso - a_fabrica
    return a_fabrica, a_casa


def _costo_bruto_por_producto(sesion, fecha_corte=None):
    """Suma de cantidad_producida x costo_unitario de todos los lotes de cada
    producto, hasta fecha_corte (o de siempre). Es el costo BRUTO: un reproceso
    lo infla (ver _carried_reproceso_por_producto)."""
    q = sesion.query(Produccion)
    if fecha_corte is not None:
        q = q.filter(Produccion.Fecha_Produccion <= fecha_corte)
    acum = {}
    for p in q.all():
        costo = (p.Cantidad_Producida_Produccion or 0) * (p.Precio_Unitario_Producto_Terminado or 0)
        acum[p.Id_Producto_Terminado] = acum.get(p.Id_Producto_Terminado, 0) + costo
    return acum


def _carried_reproceso_por_producto(sesion, fecha_corte=None):
    """Costo arrastrado por los reprocesos, a restar de la inversion. Al
    reprocesar, las botellas salen de un lote a otro pero la Cantidad_Producida
    del origen no baja: su costo queda contado en AMBOS lotes (origen y nuevo),
    asi que se duplicaria. Devuelve, por producto, ese costo duplicado (para
    restarlo una vez). El reproceso conserva el producto, asi que origen y nuevo
    lote son el mismo producto."""
    q = sesion.query(Movimiento_Inventario).filter(
        Movimiento_Inventario.Tipo_Movimiento_Inventario == "REPROCESO",
        Movimiento_Inventario.Sentido_Movimiento_Inventario == "SALIDA",
        Movimiento_Inventario.Origen_Lote == "PRODUCCION",
    )
    if fecha_corte is not None:
        q = q.filter(Movimiento_Inventario.Fecha_Movimiento_Inventario <= fecha_corte)
    acum = {}
    for m in q.all():
        origen = sesion.get(Produccion, m.Id_Produccion)
        if origen is None:
            continue
        carried = (m.Cantidad_Movimiento_Inventario or 0) * (origen.Precio_Unitario_Producto_Terminado or 0)
        acum[origen.Id_Producto_Terminado] = acum.get(origen.Id_Producto_Terminado, 0) + carried
    return acum


def _inversion_por_producto(sesion, fecha_corte=None):
    """Inversion real en producir cada producto: costo bruto de los lotes menos
    el costo arrastrado por reprocesos (que se contaria dos veces). Hasta
    fecha_corte (o de siempre). Devuelve {id_producto: monto}."""
    bruto = _costo_bruto_por_producto(sesion, fecha_corte)
    carried = _carried_reproceso_por_producto(sesion, fecha_corte)
    ids = set(bruto) | set(carried)
    return {pid: bruto.get(pid, 0) - carried.get(pid, 0) for pid in ids}


def _ingresos_por_producto(sesion, fecha_corte=None):
    """Ingresos totales de las ventas de cada producto, hasta fecha_corte (o de
    siempre). Devuelve {id_producto: monto}."""
    q = (
        sesion.query(Detalle_Venta, Venta, Produccion)
        .join(Venta, Detalle_Venta.Id_Venta == Venta.Id_Venta)
        .join(Produccion, Detalle_Venta.Id_Produccion == Produccion.Id_Produccion)
    )
    if fecha_corte is not None:
        q = q.filter(Venta.Fecha_Venta <= fecha_corte)
    acum = {}
    for detalle, _venta, produccion in q.all():
        ingreso = (detalle.Cantidad_Venta or 0) * (detalle.Precio_Venta_Real or 0)
        acum[produccion.Id_Producto_Terminado] = acum.get(produccion.Id_Producto_Terminado, 0) + ingreso
    return acum


def saldo_de_producto(sesion, id_producto_terminado, fecha_corte=None):
    """Saldo acumulado (ingresos - inversion) de UN producto hasta fecha_corte
    (o de siempre). Es lo que consulta el reparto 70/30 al registrar una venta."""
    inversion = _inversion_por_producto(sesion, fecha_corte).get(id_producto_terminado, 0)
    ingresos = _ingresos_por_producto(sesion, fecha_corte).get(id_producto_terminado, 0)
    return ingresos - inversion


def calcular_saldos(sesion, dias_comparacion=30):
    """
    Saldo acumulado de CADA producto terminado, con su valor de hace
    `dias_comparacion` dias al lado (para ver la tendencia reciente sin
    necesitar Power BI). No es la inversa de sustituir el analisis mensual
    completo (eso sigue en Power BI, 8.1): es solo una senal rapida.
    """
    from datetime import date, timedelta

    hoy = date.today()
    fecha_pasado = hoy - timedelta(days=dias_comparacion)

    inversion_actual = _inversion_por_producto(sesion)
    ingresos_actual = _ingresos_por_producto(sesion)
    inversion_pasado = _inversion_por_producto(sesion, fecha_corte=fecha_pasado)
    ingresos_pasado = _ingresos_por_producto(sesion, fecha_corte=fecha_pasado)

    ids_productos = set(inversion_actual) | set(ingresos_actual)
    resultado = []
    for pid in ids_productos:
        inv = inversion_actual.get(pid, 0)
        ing = ingresos_actual.get(pid, 0)
        saldo = ing - inv
        saldo_pasado = ingresos_pasado.get(pid, 0) - inversion_pasado.get(pid, 0)
        producto = sesion.get(Producto_Terminado, pid)
        resultado.append({
            "id_producto": pid,
            "nombre": producto.Descripcion_Producto_Terminado if producto else "?",
            "inversion_acumulada": inv,
            "ingresos_acumulados": ing,
            "saldo": saldo,
            "recupero_inversion": saldo > 0,
            "saldo_hace_dias": saldo_pasado,
            "dias_comparacion": dias_comparacion,
        })

    resultado.sort(key=lambda r: r["nombre"])
    return resultado
