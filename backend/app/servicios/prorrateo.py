"""
prorrateo.py
Cierre de mes (mejora 1.1): reparte los gastos extra del mes entre los
productos terminados según las horas-hombre que cada uno "usó la fábrica" ese
mes, y genera una foto congelada (Prorrateo_Mensual).

Las horas ya NO se cargan a mano: se calculan sumando el `Horas_Acumuladas`
(directas + heredadas) de las producciones terminadas del mes, agrupadas por
producto (atribución por mes de producción = mes de consumo de los intermedios).
Los montos salen de `Gasto_Extra_Mes` (el monto real de cada gasto ese mes), y
solo se puede prorratear cuando TODOS los gastos del mes están pagados.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from app.models import (
    Horas_Producto_Mes, Prorrateo_Mensual, Gasto_Extra, Gasto_Extra_Mes,
    Produccion, Producto_Terminado,
)


def _rango_mes(anio_mes):
    y, m = int(anio_mes[:4]), int(anio_mes[5:7])
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _horas_por_producto(sesion, anio_mes):
    """Horas-hombre por producto terminado producido en el mes (suma del
    Horas_Acumuladas de sus producciones del mes). Devuelve {id_producto: horas}."""
    desde, hasta = _rango_mes(anio_mes)
    prods = (
        sesion.query(Produccion)
        .filter(Produccion.Fecha_Produccion >= desde, Produccion.Fecha_Produccion <= hasta)
        .all()
    )
    acum = {}
    for p in prods:
        acum[p.Id_Producto_Terminado] = acum.get(p.Id_Producto_Terminado, Decimal(0)) + (p.Horas_Acumuladas or Decimal(0))
    return acum


def _ya_prorrateado(sesion, anio_mes):
    hpm_ids = [
        h.Id_Horas_Producto_Mes
        for h in sesion.query(Horas_Producto_Mes).filter_by(Anio_Mes=anio_mes).all()
    ]
    if not hpm_ids:
        return False
    return sesion.query(Prorrateo_Mensual).filter(
        Prorrateo_Mensual.Id_Horas_Producto_Mes.in_(hpm_ids)
    ).first() is not None


def preview_prorrateo(sesion, anio_mes):
    """Arma la vista previa del prorrateo del mes SIN tocar nada: horas por
    producto, gastos del mes y el reparto, más si se puede ejecutar y por qué no."""
    horas = _horas_por_producto(sesion, anio_mes)
    total_horas = sum(horas.values(), Decimal(0))

    gastos_mes = sesion.query(Gasto_Extra_Mes).filter_by(Anio_Mes=anio_mes).all()
    total_gastos = sum((g.Monto_Gasto_Extra_Mes for g in gastos_mes), Decimal(0))
    sin_pagar = [g for g in gastos_mes if g.Fecha_Pago_Gasto_Extra_Mes is None]
    ya = _ya_prorrateado(sesion, anio_mes)

    # ¿Se puede ejecutar? y si no, por qué
    motivo = None
    if ya:
        motivo = "El mes ya fue prorrateado."
    elif not gastos_mes:
        motivo = "No hay gastos registrados para el mes."
    elif sin_pagar:
        motivo = f"Faltan pagar {len(sin_pagar)} gasto(s) del mes."
    elif total_horas <= 0:
        motivo = "No hubo producción con horas ese mes."
    puede = motivo is None

    productos = []
    for id_prod, h in sorted(horas.items()):
        if h <= 0:
            continue
        prod = sesion.get(Producto_Terminado, id_prod)
        fraccion = (h / total_horas) if total_horas > 0 else Decimal(0)
        productos.append({
            "id_producto": id_prod,
            "nombre": prod.Descripcion_Producto_Terminado if prod else "?",
            "horas": float(h),
            "fraccion": round(float(fraccion) * 100, 2),
            "asignado_total": round(float(total_gastos * fraccion), 2),
        })

    gastos_detalle = []
    for g in gastos_mes:
        ge = sesion.get(Gasto_Extra, g.Id_Gasto_Extra)
        gastos_detalle.append({
            "descripcion": ge.Descripcion_Gasto_Extra if ge else "?",
            "monto": float(g.Monto_Gasto_Extra_Mes),
            "pagado": g.Fecha_Pago_Gasto_Extra_Mes is not None,
        })

    return {
        "anio_mes": anio_mes,
        "total_horas": float(total_horas),
        "total_gastos": float(total_gastos),
        "ya_prorrateado": ya,
        "puede": puede,
        "motivo": motivo,
        "gastos": gastos_detalle,
        "productos": productos,
    }


def ejecutar_prorrateo(sesion, anio_mes):
    """Reparte los gastos del mes entre los productos según sus horas y crea la
    foto (Prorrateo_Mensual). Exige: gastos registrados, todos pagados, horas > 0
    y que el mes no se haya prorrateado antes. Atómico."""
    if _ya_prorrateado(sesion, anio_mes):
        raise ValueError(f"El mes {anio_mes} ya fue prorrateado")

    gastos_mes = sesion.query(Gasto_Extra_Mes).filter_by(Anio_Mes=anio_mes).all()
    if not gastos_mes:
        raise ValueError(f"No hay gastos registrados para el mes {anio_mes}")
    sin_pagar = [g for g in gastos_mes if g.Fecha_Pago_Gasto_Extra_Mes is None]
    if sin_pagar:
        raise ValueError(f"Faltan pagar {len(sin_pagar)} gasto(s) del mes {anio_mes}")

    horas = _horas_por_producto(sesion, anio_mes)
    items = [(pid, h) for pid, h in sorted(horas.items()) if h > 0]
    total_horas = sum((h for _, h in items), Decimal(0))
    if total_horas <= 0:
        raise ValueError(f"No hubo producción con horas en el mes {anio_mes}")

    try:
        # Upsert de Horas_Producto_Mes (ancla de la foto), desde lo computado
        hpm_por_prod = {}
        for pid, h in items:
            fila = (
                sesion.query(Horas_Producto_Mes)
                .filter_by(Anio_Mes=anio_mes, Id_Producto_Terminado=pid)
                .first()
            )
            if fila is None:
                fila = Horas_Producto_Mes(
                    Id_Producto_Terminado=pid, Anio_Mes=anio_mes, Horas_Producto_Mes=h,
                )
                sesion.add(fila)
                sesion.flush()
            else:
                fila.Horas_Producto_Mes = h
            hpm_por_prod[pid] = fila.Id_Horas_Producto_Mes

        # Repartir cada gasto entre los productos; la última línea absorbe el
        # redondeo para que la suma cierre exacta con el monto del gasto.
        creados = 0
        n = len(items)
        for g in gastos_mes:
            asignado_acum = Decimal(0)
            for idx, (pid, h) in enumerate(items):
                if idx == n - 1:
                    asignado = g.Monto_Gasto_Extra_Mes - asignado_acum
                else:
                    asignado = (g.Monto_Gasto_Extra_Mes * (h / total_horas)).quantize(Decimal("0.01"))
                    asignado_acum += asignado
                sesion.add(Prorrateo_Mensual(
                    Id_Horas_Producto_Mes=hpm_por_prod[pid],
                    Id_Gasto_Extra=g.Id_Gasto_Extra,
                    Gasto_Extra_Asignado=asignado,
                ))
                creados += 1

        sesion.commit()
        return {"anio_mes": anio_mes, "asignaciones": creados, "productos": n, "gastos": len(gastos_mes)}

    except Exception as e:
        sesion.rollback()
        raise e
