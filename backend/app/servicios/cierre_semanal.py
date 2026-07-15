"""
cierre_semanal.py
Cierre de produccion con prorrateo de horas standby (mejora 3.7).

En la practica no hay un capataz que mida cuantas horas se dedico a cada
producto, y una produccion puede quedar a medias hasta el dia siguiente. Por
eso, durante el periodo, los terminados se producen SOLO con materia prima e
intermedios (sin asignar trabajo), y las jornadas quedan en "standby" (horas
registradas sin consumir). Al cerrar un rango de fechas, este servicio reparte
las horas standby de ese rango entre los terminados producidos en el mismo
rango, en proporcion a sus botellas producidas, y le suma a cada lote su costo
de trabajo.

Reglas:
- Cada jornada standby del rango se reparte ENTERA entre los terminados, con el
  mismo porcentaje por botellas (ej. 20/32, 7/32, 5/32). Asi cada jornada queda
  totalmente consumida (su standby pasa a 0).
- El peso es la cantidad PRODUCIDA del lote (no la restante): la mano de obra
  fue para producir todo el lote, aunque ya se haya vendido parte.
- Solo entran los terminados del rango que AUN NO tienen trabajo asignado (los
  que ya lo tienen se consideran cerrados; no se duplica).
- Solo terminados: los intermedios del rango no reciben horas (decision de
  negocio, mejora 3.7). El modelo de horas heredadas es aparte (1.1).
- El costo del lote se ACTUALIZA sumandole su trabajo (no se recalculan MP,
  intermedios ni absorcion, que ya estaban en el costo al producir sin trabajo).
"""

from decimal import Decimal

from app.models import (
    Produccion, Producto_Terminado, Registro_Trabajador, Trabajador,
    Detalle_Prod_Trabajador,
)
from app.servicios.trabajadores import tarifa_hora


def _redondear(valor, decimales=4):
    return valor.quantize(Decimal(10) ** -decimales)


def calcular_cierre(sesion, fecha_desde, fecha_hasta):
    """
    Calcula el reparto de horas standby del rango entre los terminados del
    rango, SIN tocar la base. Devuelve un dict con el plan completo (lo usan
    tanto la vista previa como la ejecucion, para que den los mismos numeros).
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("La fecha desde no puede ser posterior a la fecha hasta")

    # --- Jornadas en standby dentro del rango (horas registradas sin consumir) ---
    jornadas = (
        sesion.query(Registro_Trabajador)
        .filter(
            Registro_Trabajador.Fecha_Registro_Trabajador >= fecha_desde,
            Registro_Trabajador.Fecha_Registro_Trabajador <= fecha_hasta,
            Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0,
        )
        .order_by(Registro_Trabajador.Id_Registro_Trabajador)
        .all()
    )

    # --- Terminados producidos en el rango que AUN NO tienen trabajo asignado ---
    producciones = (
        sesion.query(Produccion)
        .filter(
            Produccion.Fecha_Produccion >= fecha_desde,
            Produccion.Fecha_Produccion <= fecha_hasta,
        )
        .order_by(Produccion.Id_Produccion)
        .all()
    )
    elegibles = []
    for p in producciones:
        ya_tiene_trabajo = (
            sesion.query(Detalle_Prod_Trabajador)
            .filter_by(Id_Produccion=p.Id_Produccion)
            .count()
        )
        if not ya_tiene_trabajo:
            elegibles.append(p)

    # --- Datos de jornadas (con tarifa y valor) ---
    jornadas_info = []
    total_horas = Decimal(0)
    total_valor = Decimal(0)
    for j in jornadas:
        trab = sesion.get(Trabajador, j.Id_Trabajador)
        tarifa = tarifa_hora(trab)
        horas = j.Horas_Restante_Registro_Trabajador
        jornadas_info.append({
            "id_jornada": j.Id_Registro_Trabajador,
            "nombre_trabajador": trab.Nombre_Trabajador if trab else "?",
            "fecha": str(j.Fecha_Registro_Trabajador),
            "horas": horas,
            "tarifa": tarifa,
            "valor": horas * tarifa,
        })
        total_horas += horas
        total_valor += horas * tarifa

    # --- Casos sin datos ---
    total_botellas = sum(p.Cantidad_Producida_Produccion for p in elegibles) if elegibles else Decimal(0)
    if not jornadas_info:
        return {"sin_datos": "No hay jornadas en standby en ese rango.", "jornadas": [],
                "productos": [], "total_botellas": Decimal(0), "total_horas": Decimal(0),
                "total_valor_trabajo": Decimal(0), "desde": str(fecha_desde), "hasta": str(fecha_hasta)}
    if not elegibles or total_botellas <= 0:
        return {"sin_datos": "No hay terminados sin trabajo asignado en ese rango.", "jornadas": jornadas_info,
                "productos": [], "total_botellas": Decimal(0), "total_horas": total_horas,
                "total_valor_trabajo": total_valor, "desde": str(fecha_desde), "hasta": str(fecha_hasta)}

    # --- Reparto: cada jornada entera se reparte por botellas entre los lotes ---
    # Estructura por producto: proporcion, costo de trabajo, y sus asignaciones
    # (una por jornada). La ULTIMA linea de cada jornada absorbe el redondeo,
    # para que la suma de horas repartidas sea exactamente las horas de la
    # jornada (y su standby quede en 0 exacto).
    productos = []
    for p in elegibles:
        prod = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        productos.append({
            "id_produccion": p.Id_Produccion,
            "nombre": prod.Descripcion_Producto_Terminado if prod else "?",
            "botellas": p.Cantidad_Producida_Produccion,
            "proporcion": p.Cantidad_Producida_Produccion / total_botellas,
            "costo_unit_actual": p.Precio_Unitario_Producto_Terminado or Decimal(0),
            "cantidad_producida": p.Cantidad_Producida_Produccion,
            "costo_trabajo": Decimal(0),
            "asignaciones": [],
        })

    n = len(productos)
    for j in jornadas_info:
        horas_j = j["horas"]
        asignado = Decimal(0)
        for idx, prod in enumerate(productos):
            if idx == n - 1:
                horas = horas_j - asignado  # la ultima absorbe el redondeo
            else:
                horas = _redondear(horas_j * prod["proporcion"], 4)
                asignado += horas
            if horas <= 0:
                continue
            prod["asignaciones"].append({
                "id_jornada": j["id_jornada"],
                "nombre_trabajador": j["nombre_trabajador"],
                "horas": horas,
            })
            prod["costo_trabajo"] += horas * j["tarifa"]

    # Costo unitario nuevo = actual + trabajo/botellas producidas
    total_costo_trabajo = Decimal(0)
    for prod in productos:
        prod["costo_unit_nuevo"] = prod["costo_unit_actual"] + prod["costo_trabajo"] / prod["cantidad_producida"]
        total_costo_trabajo += prod["costo_trabajo"]

    return {
        "sin_datos": None,
        "desde": str(fecha_desde),
        "hasta": str(fecha_hasta),
        "jornadas": jornadas_info,
        "productos": productos,
        "total_botellas": total_botellas,
        "total_horas": total_horas,
        "total_valor_trabajo": total_costo_trabajo,
    }


def ejecutar_cierre(sesion, fecha_desde, fecha_hasta):
    """
    Aplica el cierre: crea los Detalle_Prod_Trabajador del reparto, consume las
    horas standby de las jornadas y actualiza el costo de cada lote. Atomico.
    Recalcula el plan desde la BD (no confia en numeros del cliente).
    """
    plan = calcular_cierre(sesion, fecha_desde, fecha_hasta)
    if plan["sin_datos"]:
        raise ValueError(plan["sin_datos"])

    try:
        # Horas consumidas por jornada (para descontar su standby una sola vez)
        consumido_por_jornada = {}
        for prod in plan["productos"]:
            produccion = sesion.get(Produccion, prod["id_produccion"])
            for a in prod["asignaciones"]:
                sesion.add(Detalle_Prod_Trabajador(
                    Id_Produccion=prod["id_produccion"],
                    Id_Registro_Trabajador=a["id_jornada"],
                    Horas_Usadas=a["horas"],
                ))
                consumido_por_jornada[a["id_jornada"]] = (
                    consumido_por_jornada.get(a["id_jornada"], Decimal(0)) + a["horas"]
                )
            # Actualizar el costo del lote sumandole su trabajo
            produccion.Precio_Unitario_Producto_Terminado = prod["costo_unit_nuevo"]
            # Sumar las horas directas asignadas a las horas acumuladas (1.1):
            # el lote nacio solo con las heredadas de sus intermedios.
            horas_asignadas = sum(a["horas"] for a in prod["asignaciones"])
            produccion.Horas_Acumuladas = (produccion.Horas_Acumuladas or Decimal(0)) + horas_asignadas

        # Descontar las horas consumidas de cada jornada (quedan en standby 0)
        for id_jornada, horas in consumido_por_jornada.items():
            jornada = sesion.get(Registro_Trabajador, id_jornada)
            jornada.Horas_Restante_Registro_Trabajador = (
                jornada.Horas_Restante_Registro_Trabajador - horas
            )

        sesion.commit()
        return {
            "lotes_cerrados": len(plan["productos"]),
            "jornadas_repartidas": len(consumido_por_jornada),
            "total_horas": float(plan["total_horas"]),
            "total_costo_trabajo": float(plan["total_valor_trabajo"]),
        }

    except Exception as e:
        sesion.rollback()
        raise e
