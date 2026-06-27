"""
prorrateo.py
Logica del cierre de mes: reparte cada gasto extra entre los productos segun
las horas que cada uno uso ese mes (proporcional). Genera una "foto" congelada.

Requiere que antes existan las filas de Horas_Producto_Mes del mes (cuantas
horas uso cada producto). El reparto crea las filas de Prorrateo_Mensual.
"""

from app.models import Horas_Producto_Mes, Prorrateo_Mensual, Gasto_Extra


def calcular_prorrateo_mensual(sesion, anio_mes):
    """
    Reparte todos los gastos extra del mes entre los productos, proporcional
    a las horas que cada producto uso ese mes.

    anio_mes: string tipo '2026-05'
    Devuelve: lista de Prorrateo_Mensual creados.
    Lanza ValueError si no hay horas registradas o si ya se prorrateo el mes.
    """

    # ----- 1. VALIDACIONES y datos base -----

    # Horas de cada producto en el mes
    horas_productos = (
        sesion.query(Horas_Producto_Mes)
        .filter_by(Anio_Mes=anio_mes)
        .all()
    )
    if not horas_productos:
        raise ValueError(f"No hay horas registradas para el mes {anio_mes}")

    # Verificar que no se haya prorrateado ya (evitar duplicar la foto)
    ids_horas = [h.Id_Horas_Producto_Mes for h in horas_productos]
    ya_existe = (
        sesion.query(Prorrateo_Mensual)
        .filter(Prorrateo_Mensual.Id_Horas_Producto_Mes.in_(ids_horas))
        .first()
    )
    if ya_existe is not None:
        raise ValueError(f"El mes {anio_mes} ya fue prorrateado")

    # Total de horas del mes (suma de todos los productos)
    total_horas = sum(h.Horas_Producto_Mes for h in horas_productos)
    if total_horas <= 0:
        raise ValueError("El total de horas del mes es cero, no se puede prorratear")

    # Todos los gastos extra a repartir
    gastos = sesion.query(Gasto_Extra).all()
    if not gastos:
        raise ValueError("No hay gastos extra para repartir")

    # ----- 2. EJECUTAR: repartir cada gasto entre cada producto -----

    try:
        creados = []
        for hp in horas_productos:
            # Que fraccion del mes uso este producto
            fraccion = hp.Horas_Producto_Mes / total_horas

            for gasto in gastos:
                asignado = gasto.Precio_Mensual_Gasto_Extra * fraccion

                prorrateo = Prorrateo_Mensual(
                    Id_Horas_Producto_Mes=hp.Id_Horas_Producto_Mes,
                    Id_Gasto_Extra=gasto.Id_Gasto_Extra,
                    Gasto_Extra_Asignado=asignado,
                )
                sesion.add(prorrateo)
                creados.append(prorrateo)

        sesion.commit()
        return creados

    except Exception as e:
        sesion.rollback()
        raise e