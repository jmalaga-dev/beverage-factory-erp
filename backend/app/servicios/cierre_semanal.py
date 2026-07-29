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
  mismo porcentaje (ej. 20/32, 7/32, 5/32). Asi cada jornada queda totalmente
  consumida (su standby pasa a 0).
- El peso del reparto depende de la BASE elegida:
    * "botellas" (por defecto, la mejora 3.7): peso = cantidad PRODUCIDA del lote.
    * "paquetes": peso = cantidad producida / Botellas_Por_Paquete (paquetes
      equivalentes, como lo hacia el Excel antes). Solo cambia el resultado
      cuando los productos empacan distinto (bpp distinto entre ellos).
  El costo por botella sigue siendo trabajo / botellas producidas: la base solo
  cambia COMO se reparten las horas entre productos, no sobre cuantas unidades
  se prorratea el costo de cada lote.
- El peso usa la cantidad PRODUCIDA (no la restante): la mano de obra fue para
  producir todo el lote, aunque ya se haya vendido parte.
- Solo entran los terminados del rango que AUN NO tienen trabajo asignado (los
  que ya lo tienen se consideran cerrados; no se duplica).
- Solo terminados: los intermedios del rango no reciben horas (decision de
  negocio, mejora 3.7). El modelo de horas heredadas es aparte (1.1).
- El costo del lote se ACTUALIZA sumandole su trabajo (no se recalculan MP,
  intermedios ni absorcion, que ya estaban en el costo al producir sin trabajo).

GASTOS DE FABRICA (bloque E)
El cierre reparte, ademas de las horas, los GASTOS de los grupos marcados con
Prorratea_Cierre_Produccion (migracion 031) -- tipicamente extras que se le
dan al trabajador ademas del sueldo, sin ser insumo de produccion. Se reparten
entre los mismos lotes y con la MISMA base que las horas, y se suman al costo
unitario igual que el trabajo.

Que gastos entran: las SALIDA del rango cuyo grupo esta marcado y que TODAVIA
no se repartieron (no figuran en el libro Gasto_Cierre_Produccion). Ese libro
es lo que hace que re-correr el cierre sea seguro, igual que el standby en
cero lo hace para las horas.

Si hay gastos marcados pero ningun lote elegible, los gastos NO se reparten y
quedan pendientes: los toma el proximo cierre que si tenga produccion
(decision de negocio, jul 2026). La vista previa lo avisa para que no pase
inadvertido.

Limitacion conocida (acotada): los gastos van a los mismos lotes elegibles que
las horas, o sea los que AUN NO TIENEN TRABAJO ASIGNADO. Verificado: un gasto
cargado despues de haber repartido gastos sobre esos lotes se reparte igual
(el libro solo bloquea repetir el mismo movimiento, no volver al mismo lote), y
el costo se le SUMA al que ya tenia, sin recalcular lo anterior. Recien cuando
un cierre les asigna horas los lotes salen del conjunto elegible, y ahi si un
gasto posterior de esa misma semana queda pendiente para el proximo cierre con
produccion. En la practica los gastos se cargan el dia que ocurren y las horas
se cierran al final de la semana, asi que el caso es raro; el aviso de la vista
previa lo hace visible cuando pasa.
"""

from decimal import Decimal

from app.models import (
    Produccion, Producto_Terminado, Registro_Trabajador, Trabajador,
    Detalle_Prod_Trabajador, Movimiento, Grupo_Movimiento, Gasto_Cierre_Produccion,
)
from app.servicios.trabajadores import tarifa_hora
from app.servicios.balance import ids_salidas_anuladas


BASES_VALIDAS = ("botellas", "paquetes")


def _redondear(valor, decimales=4):
    return valor.quantize(Decimal(10) ** -decimales)


def _peso_item(item, base):
    """Peso de un lote en el reparto segun la base ('botellas' o 'paquetes')."""
    if base == "paquetes":
        bpp = item["bpp"] if item["bpp"] and item["bpp"] > 0 else Decimal(1)
        return item["cantidad_producida"] / bpp
    return item["cantidad_producida"]


def _repartir(items, jornadas_info, gastos_info, base):
    """
    Reparte entre los lotes, segun su peso en la base dada:
      - cada jornada standby entera (horas -> costo de trabajo), y
      - cada gasto de fabrica entero (bloque E).

    Devuelve un dict id_produccion -> {proporcion, costo_trabajo, horas_total,
    asignaciones, costo_gasto, asignaciones_gasto, costo_unit_nuevo}. La ULTIMA
    linea de cada jornada y de cada gasto absorbe el redondeo, para que se
    repartan enteros y sin fugas. No toca la base.
    """
    pesos = {it["id_produccion"]: _peso_item(it, base) for it in items}
    total_peso = sum(pesos.values()) if items else Decimal(0)

    res = {}
    for it in items:
        prop = pesos[it["id_produccion"]] / total_peso if total_peso > 0 else Decimal(0)
        res[it["id_produccion"]] = {
            "proporcion": prop,
            "costo_trabajo": Decimal(0),
            "horas_total": Decimal(0),
            "asignaciones": [],
            "costo_gasto": Decimal(0),
            "asignaciones_gasto": [],
        }

    n = len(items)
    for j in jornadas_info:
        horas_j = j["horas"]
        asignado = Decimal(0)
        for idx, it in enumerate(items):
            r = res[it["id_produccion"]]
            if idx == n - 1:
                horas = horas_j - asignado  # la ultima absorbe el redondeo
            else:
                horas = _redondear(horas_j * r["proporcion"], 4)
                asignado += horas
            if horas <= 0:
                continue
            r["asignaciones"].append({
                "id_jornada": j["id_jornada"],
                "nombre_trabajador": j["nombre_trabajador"],
                "horas": horas,
            })
            r["costo_trabajo"] += horas * j["tarifa"]
            r["horas_total"] += horas

    # Gastos de fabrica: mismo mecanismo que las jornadas, en Bs en vez de horas.
    for g in gastos_info:
        monto_g = g["monto"]
        asignado = Decimal(0)
        for idx, it in enumerate(items):
            r = res[it["id_produccion"]]
            if idx == n - 1:
                monto = monto_g - asignado  # la ultima absorbe el redondeo
            else:
                monto = _redondear(monto_g * r["proporcion"], 2)
                asignado += monto
            if monto <= 0:
                continue
            r["asignaciones_gasto"].append({
                "id_movimiento": g["id_movimiento"],
                "descripcion": g["descripcion"],
                "monto": monto,
            })
            r["costo_gasto"] += monto

    for it in items:
        r = res[it["id_produccion"]]
        # El costo por botella se prorratea siempre sobre las botellas
        # producidas del lote: la base solo cambia COMO se reparte entre
        # productos, no sobre cuantas unidades se divide el costo de cada uno.
        r["costo_unit_nuevo"] = (
            it["costo_unit_actual"]
            + (r["costo_trabajo"] + r["costo_gasto"]) / it["cantidad_producida"]
        )

    return res, total_peso


def calcular_cierre(sesion, fecha_desde, fecha_hasta, base="botellas"):
    """
    Calcula el reparto de horas standby del rango entre los terminados del
    rango, SIN tocar la base. Devuelve un dict con el plan completo (lo usan
    tanto la vista previa como la ejecucion, para que den los mismos numeros).

    `base` decide el peso del reparto ('botellas' o 'paquetes'); el plan trae
    ademas los numeros de la OTRA base por producto, para ver cuanto varia.
    """
    if base not in BASES_VALIDAS:
        raise ValueError(f"Base de reparto invalida: {base}")
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

    # --- Gastos de fabrica del rango, aun sin repartir (bloque E) ---
    gastos_info = []
    total_gastos = Decimal(0)
    grupos_marcados = [
        g.Id_Grupo_Movimiento
        for g in sesion.query(Grupo_Movimiento)
        .filter(Grupo_Movimiento.Prorratea_Cierre_Produccion.is_(True)).all()
    ]
    if grupos_marcados:
        # Ya repartidos: un movimiento que figura en el libro no vuelve a
        # entrar (es lo que hace seguro re-correr el cierre).
        ya_repartidos = {
            v for (v,) in sesion.query(Gasto_Cierre_Produccion.Id_Movimiento).distinct()
        }
        # Una salida anulada devolvio su plata: no debe encarecer ninguna
        # botella. Hoy no puede pasar (solo se anulan pagos de servicios, que
        # no llevan grupo), pero la regla queda escrita.
        anuladas = ids_salidas_anuladas(sesion)
        movimientos = (
            sesion.query(Movimiento)
            .filter(
                Movimiento.Tipo_Movimiento == "SALIDA",
                Movimiento.Fecha_Movimiento >= fecha_desde,
                Movimiento.Fecha_Movimiento <= fecha_hasta,
                Movimiento.Id_Grupo_Movimiento.in_(grupos_marcados),
            )
            .order_by(Movimiento.Id_Movimiento)
            .all()
        )
        for m in movimientos:
            if m.Id_Movimiento in ya_repartidos or m.Id_Movimiento in anuladas:
                continue
            grupo = sesion.get(Grupo_Movimiento, m.Id_Grupo_Movimiento)
            gastos_info.append({
                "id_movimiento": m.Id_Movimiento,
                "descripcion": m.Descripcion_Movimiento or "(sin descripción)",
                "grupo": grupo.Nombre_Grupo_Movimiento if grupo else "?",
                "fecha": str(m.Fecha_Movimiento),
                "monto": m.Monto_Movimiento,
            })
            total_gastos += m.Monto_Movimiento

    # --- Casos sin datos ---
    # Un cierre tiene sentido si hay ALGO que repartir: horas standby o gastos
    # de fabrica. Una semana sin horas pendientes pero con gastos marcados es
    # un cierre valido (solo reparte los gastos).
    total_botellas = sum(p.Cantidad_Producida_Produccion for p in elegibles) if elegibles else Decimal(0)
    vacio = {
        "jornadas": [], "gastos": [], "productos": [],
        "total_botellas": Decimal(0), "total_paquetes": Decimal(0),
        "total_horas": Decimal(0), "total_valor_trabajo": Decimal(0),
        "total_gastos": Decimal(0), "gastos_pendientes": [],
        "base": base, "desde": str(fecha_desde), "hasta": str(fecha_hasta),
    }
    if not jornadas_info and not gastos_info:
        return {**vacio, "sin_datos": "No hay horas en standby ni gastos de fábrica por repartir en ese rango."}
    if not elegibles or total_botellas <= 0:
        # Los gastos encontrados no se pierden: quedan pendientes para el
        # proximo cierre que si tenga produccion (decision de negocio).
        return {**vacio, "sin_datos": "No hay terminados sin trabajo asignado en ese rango.",
                "jornadas": jornadas_info, "gastos": gastos_info,
                "total_horas": total_horas, "total_valor_trabajo": total_valor,
                "total_gastos": total_gastos, "gastos_pendientes": gastos_info}

    # --- Datos estaticos de cada lote (botellas, paquetes, costo actual) ---
    items = []
    for p in elegibles:
        prod = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        bpp = Decimal(prod.Botellas_Por_Paquete) if prod and prod.Botellas_Por_Paquete else Decimal(1)
        items.append({
            "id_produccion": p.Id_Produccion,
            "nombre": prod.Descripcion_Producto_Terminado if prod else "?",
            "cantidad_producida": p.Cantidad_Producida_Produccion,
            "bpp": bpp,
            "costo_unit_actual": p.Precio_Unitario_Producto_Terminado or Decimal(0),
        })

    # Reparto en la base elegida (con detalle de asignaciones) y en la otra
    # base (solo para mostrar cuanto varia). El total de dinero de trabajo es el
    # mismo en ambas: solo cambia como se reparte entre productos.
    otra = "paquetes" if base == "botellas" else "botellas"
    res_sel, _ = _repartir(items, jornadas_info, gastos_info, base)
    res_alt, total_paquetes_o_bot = _repartir(items, jornadas_info, gastos_info, otra)

    total_paquetes = sum(_peso_item(it, "paquetes") for it in items)

    productos = []
    total_costo_trabajo = Decimal(0)
    total_costo_gasto = Decimal(0)
    for it in items:
        sel = res_sel[it["id_produccion"]]
        alt = res_alt[it["id_produccion"]]
        total_costo_trabajo += sel["costo_trabajo"]
        total_costo_gasto += sel["costo_gasto"]
        productos.append({
            "id_produccion": it["id_produccion"],
            "nombre": it["nombre"],
            "botellas": it["cantidad_producida"],
            "paquetes": _peso_item(it, "paquetes"),
            "cantidad_producida": it["cantidad_producida"],
            "costo_unit_actual": it["costo_unit_actual"],
            # Base seleccionada (lo que se confirma):
            "proporcion": sel["proporcion"],
            "horas_total": sel["horas_total"],
            "costo_trabajo": sel["costo_trabajo"],
            "costo_gasto": sel["costo_gasto"],
            "costo_unit_nuevo": sel["costo_unit_nuevo"],
            "asignaciones": sel["asignaciones"],
            "asignaciones_gasto": sel["asignaciones_gasto"],
            # Otra base (solo comparacion):
            "proporcion_alt": alt["proporcion"],
            "horas_total_alt": alt["horas_total"],
            "costo_trabajo_alt": alt["costo_trabajo"],
            "costo_gasto_alt": alt["costo_gasto"],
            "costo_unit_nuevo_alt": alt["costo_unit_nuevo"],
        })

    return {
        "sin_datos": None,
        "base": base,
        "base_alt": otra,
        "desde": str(fecha_desde),
        "hasta": str(fecha_hasta),
        "jornadas": jornadas_info,
        "gastos": gastos_info,
        "gastos_pendientes": [],
        "productos": productos,
        "total_botellas": total_botellas,
        "total_paquetes": total_paquetes,
        "total_horas": total_horas,
        "total_valor_trabajo": total_costo_trabajo,
        "total_gastos": total_costo_gasto,
    }


def ejecutar_cierre(sesion, fecha_desde, fecha_hasta, base="botellas"):
    """
    Aplica el cierre: crea los Detalle_Prod_Trabajador del reparto, consume las
    horas standby de las jornadas, anota en el libro los gastos de fabrica
    repartidos (bloque E) y actualiza el costo de cada lote. Atomico.
    Recalcula el plan desde la BD (no confia en numeros del cliente).

    `base` ('botellas' o 'paquetes') decide el reparto que se escribe.
    """
    plan = calcular_cierre(sesion, fecha_desde, fecha_hasta, base)
    if plan["sin_datos"]:
        raise ValueError(plan["sin_datos"])

    try:
        # Horas consumidas por jornada (para descontar su standby una sola vez)
        consumido_por_jornada = {}
        gastos_repartidos = set()
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
            # Libro de gastos de fabrica: deja el rastro Y es lo que impide
            # repartir dos veces el mismo movimiento en un cierre posterior.
            for a in prod["asignaciones_gasto"]:
                sesion.add(Gasto_Cierre_Produccion(
                    Id_Movimiento=a["id_movimiento"],
                    Id_Produccion=prod["id_produccion"],
                    Monto_Asignado=a["monto"],
                    Fecha_Cierre=fecha_hasta,
                ))
                gastos_repartidos.add(a["id_movimiento"])
            # Actualizar el costo del lote sumandole su trabajo y sus gastos
            produccion.Precio_Unitario_Producto_Terminado = prod["costo_unit_nuevo"]
            # Sumar las horas directas asignadas a las horas acumuladas (1.1):
            # el lote nacio solo con las heredadas de sus intermedios. Los
            # gastos NO suman horas: son dinero, no trabajo.
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
            "gastos_repartidos": len(gastos_repartidos),
            "total_horas": float(plan["total_horas"]),
            "total_costo_trabajo": float(plan["total_valor_trabajo"]),
            "total_gastos": float(plan["total_gastos"]),
        }

    except Exception as e:
        sesion.rollback()
        raise e
