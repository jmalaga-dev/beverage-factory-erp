"""
simulacion.py
Simulacion de costo de un producto nuevo (mejora 1.5), replica de la hoja de
simulacion del Excel.

Es de SOLO LECTURA: no toca stock, ni dinero, ni crea registros. Se le pasa
una receta hipotetica ("20 L de jarabe base + 5 kg de azucar para 30 L") y
devuelve el costo unitario en 3 escenarios, segun el historico real de cada
insumo: la vez mas barata, el promedio ponderado y la vez mas cara.

Dos decisiones de negocio que definen los numeros (jul 2026):

1. VENTANA DE TIEMPO CONFIGURABLE (12 meses por defecto). Con todo el
   historico, el escenario barato queda anclado a precios de hace anios: hay
   insumos cuyo minimo historico es 17x mas barato que cualquier compra del
   ultimo anio, asi que el escenario optimista dejaria de ser accionable.
   Un insumo sin compras en la ventana cae a su ultimo precio conocido y se
   marca con un aviso, en vez de quedar en cero y ensuciar el total.

2. PROMEDIO PONDERADO POR CANTIDAD (Bs totales / cantidad total), no promedio
   simple de precios: una compra de 1 kg no puede pesar lo mismo que una de
   100 kg. Es el mismo criterio del costo promedio del stock consolidado, asi
   que los numeros son comparables entre pantallas.

La mano de obra NO entra en los escenarios (igual que en las recetas de 3.6):
las horas de un producto que todavia no existe no se saben, e inventarlas
ensuciaria la comparacion. En su lugar se devuelven tres indicadores de
referencia en Bs/botella (mano de obra, absorcion y gastos extra), calculados
del historico real, para sumarlos aparte y ver el costo con carga completa.
"""

import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import func

from app.models import (
    Absorcion_Produccion,
    Compra,
    Gasto_Extra_Mes,
    Materia_Prima,
    Produccion,
    Produccion_Intermedio,
    Producto_Intermedio,
    Registro_Trabajador,
    Trabajador,
    Detalle_Prod_Trabajador,
)

CERO = Decimal(0)


def _restar_meses(f, meses):
    """
    Resta meses calendario a una fecha, sin dependencias externas (el proyecto
    no usa dateutil y no vale la pena sumar una libreria por esto). Ajusta el
    dia al ultimo del mes destino cuando no existe: 31 de marzo menos 1 mes es
    28/29 de febrero, no una fecha invalida.
    """
    total = f.year * 12 + (f.month - 1) - int(meses)
    anio, mes = divmod(total, 12)
    mes += 1
    return date(anio, mes, min(f.day, calendar.monthrange(anio, mes)[1]))


def _ventana(meses):
    """Rango [desde, hasta] de la ventana. meses <= 0 = todo el historico."""
    hasta = date.today()
    if not meses or int(meses) <= 0:
        return None, hasta
    return _restar_meses(hasta, meses), hasta


def _resumen(pares):
    """
    De una lista de (cantidad, importe) saca min / promedio ponderado / max del
    precio unitario. `pares` ya viene filtrado a la ventana.

    El promedio es ponderado: sum(importe) / sum(cantidad). Las filas con
    cantidad <= 0 se descartan (no se puede derivar un precio unitario de
    ellas, y dividir por cero rompe el calculo).
    """
    unitarios = []
    total_cant = CERO
    total_importe = CERO
    for cantidad, importe in pares:
        cantidad = Decimal(cantidad or 0)
        importe = Decimal(importe or 0)
        if cantidad <= 0:
            continue
        unitarios.append(importe / cantidad)
        total_cant += cantidad
        total_importe += importe
    if not unitarios:
        return None
    return {
        "barato": min(unitarios),
        "promedio": total_importe / total_cant if total_cant > 0 else CERO,
        "caro": max(unitarios),
        "n": len(unitarios),
    }


def _historico_mp(sesion, id_mp, desde, hasta):
    """(cantidad, importe) de cada compra de una materia prima."""
    q = sesion.query(Compra.Cantidad_Compra, Compra.Precio_Compra).filter(
        Compra.Id_Materia_Prima == id_mp
    )
    if desde is not None:
        q = q.filter(Compra.Fecha_Compra >= desde, Compra.Fecha_Compra <= hasta)
    return q.all()


def _historico_intermedio(sesion, id_pi, desde, hasta):
    """
    (cantidad, importe) de cada produccion de un intermedio. El costo unitario
    ya esta calculado por lote, asi que el importe se reconstruye como
    cantidad x costo_unitario para poder ponderar igual que las compras.
    """
    q = sesion.query(
        Produccion_Intermedio.Cantidad_Producida,
        Produccion_Intermedio.Costo_Unitario_Produccion_Intermedio,
    ).filter(Produccion_Intermedio.Id_Producto_Intermedio == id_pi)
    if desde is not None:
        q = q.filter(
            Produccion_Intermedio.Fecha_Produccion_Intermedio >= desde,
            Produccion_Intermedio.Fecha_Produccion_Intermedio <= hasta,
        )
    pares = []
    for cantidad, costo_unit in q.all():
        cantidad = Decimal(cantidad or 0)
        pares.append((cantidad, cantidad * Decimal(costo_unit or 0)))
    return pares


def precios_insumo(sesion, tipo, id_insumo, meses):
    """
    Los 3 precios unitarios historicos de un insumo dentro de la ventana.

    Si no hubo movimiento en la ventana, cae a TODO el historico y lo marca en
    `aviso`: es mejor un precio viejo senializado que un cero silencioso que
    haria ver el producto mas barato de lo que es.
    """
    desde, hasta = _ventana(meses)
    if tipo == "MP":
        obj = sesion.get(Materia_Prima, id_insumo)
        nombre = obj.Descripcion_Materia_Prima if obj else "?"
        unidad = obj.Unidad_Materia_Prima if obj else None
        pares = _historico_mp(sesion, id_insumo, desde, hasta)
        completo = _historico_mp(sesion, id_insumo, None, hasta)
    else:
        obj = sesion.get(Producto_Intermedio, id_insumo)
        nombre = obj.Descripcion_Producto_Intermedio if obj else "?"
        unidad = obj.Unidad_Producto_Intermedio if obj else None
        pares = _historico_intermedio(sesion, id_insumo, desde, hasta)
        completo = _historico_intermedio(sesion, id_insumo, None, hasta)

    resumen = _resumen(pares)
    aviso = None
    if resumen is None:
        resumen = _resumen(completo)
        if resumen is None:
            return {
                "tipo": tipo, "id_insumo": id_insumo, "nombre": nombre, "unidad": unidad,
                "barato": None, "promedio": None, "caro": None, "n": 0,
                "aviso": "Sin historial: nunca se compró/produjo, no se puede estimar su costo",
            }
        aviso = "Sin movimiento en la ventana elegida: se usó todo el histórico"

    return {
        "tipo": tipo, "id_insumo": id_insumo, "nombre": nombre, "unidad": unidad,
        "barato": float(resumen["barato"]),
        "promedio": float(resumen["promedio"]),
        "caro": float(resumen["caro"]),
        "n": resumen["n"],
        "aviso": aviso,
    }


def indicadores_referencia(sesion, meses):
    """
    Carga fija promedio por botella, del historico real: mano de obra,
    absorcion (1.4) y gastos extra prorrateados (1.1).

    Los tres se calculan como TOTAL Bs / TOTAL botellas del periodo, no como
    promedio de los ratios mensuales. Con el promedio de ratios, un mes de
    poca produccion pesa igual que uno de mucha, y como los meses flacos
    tienen ratios altisimos el resultado se infla (en los datos reales, un
    17% mas alto). El total sobre total responde de verdad "cuanto carga una
    botella".

    No entran en los escenarios: se devuelven aparte para sumarlos y ver el
    costo con carga completa (decision de jul 2026).
    """
    desde, hasta = _ventana(meses)

    q_bot = sesion.query(func.sum(Produccion.Cantidad_Producida_Produccion))
    if desde is not None:
        q_bot = q_bot.filter(Produccion.Fecha_Produccion >= desde, Produccion.Fecha_Produccion <= hasta)
    botellas = Decimal(q_bot.scalar() or 0)

    if botellas <= 0:
        return {"mano_obra": 0.0, "absorcion": 0.0, "gastos_extra": 0.0, "total": 0.0,
                "botellas_periodo": 0.0}

    # Mano de obra: horas usadas x tarifa del trabajador (sueldo / horas base).
    q_trab = (
        sesion.query(func.sum(
            Detalle_Prod_Trabajador.Horas_Usadas
            * (Trabajador.Pago_Trabajador / func.nullif(Trabajador.Horas_Base_Trabajador, 0))
        ))
        .join(Registro_Trabajador,
              Registro_Trabajador.Id_Registro_Trabajador == Detalle_Prod_Trabajador.Id_Registro_Trabajador)
        .join(Trabajador, Trabajador.Id_Trabajador == Registro_Trabajador.Id_Trabajador)
        .join(Produccion, Produccion.Id_Produccion == Detalle_Prod_Trabajador.Id_Produccion)
    )
    if desde is not None:
        q_trab = q_trab.filter(Produccion.Fecha_Produccion >= desde, Produccion.Fecha_Produccion <= hasta)
    mano_obra = Decimal(q_trab.scalar() or 0)

    # Absorcion de utensilios/feriados/mermas ya repartida en producciones.
    q_abs = (
        sesion.query(func.sum(Absorcion_Produccion.Monto_Absorbido))
        .join(Produccion, Produccion.Id_Produccion == Absorcion_Produccion.Id_Produccion)
    )
    if desde is not None:
        q_abs = q_abs.filter(Produccion.Fecha_Produccion >= desde, Produccion.Fecha_Produccion <= hasta)
    absorcion = Decimal(q_abs.scalar() or 0)

    # Gastos extra del mes (luz, agua, internet...). Anio_Mes es texto 'YYYY-MM',
    # asi que la ventana se filtra comparando contra el mes de `desde`.
    q_gas = sesion.query(func.sum(Gasto_Extra_Mes.Monto_Gasto_Extra_Mes))
    if desde is not None:
        q_gas = q_gas.filter(Gasto_Extra_Mes.Anio_Mes >= desde.strftime("%Y-%m"),
                             Gasto_Extra_Mes.Anio_Mes <= hasta.strftime("%Y-%m"))
    gastos = Decimal(q_gas.scalar() or 0)

    mo = mano_obra / botellas
    ab = absorcion / botellas
    ge = gastos / botellas
    return {
        "mano_obra": float(mo),
        "absorcion": float(ab),
        "gastos_extra": float(ge),
        "total": float(mo + ab + ge),
        "botellas_periodo": float(botellas),
    }


def simular(sesion, insumos, rendimiento, litros_por_botella, botellas_por_paquete, meses=12):
    """
    Corazon de la simulacion. `insumos` = [{tipo, id_insumo, cantidad}].

    `rendimiento` es cuanto sale de la receta en la unidad del producto (ej.
    30 litros). Con `litros_por_botella` se convierte a botellas, y con
    `botellas_por_paquete` a paquetes.

    Devuelve los 3 escenarios (costo total, por unidad, por botella, por
    paquete), el detalle por insumo, y los indicadores de referencia con los
    3 escenarios ya sumados a esa carga fija.
    """
    if rendimiento is None or Decimal(rendimiento) <= 0:
        raise ValueError("El rendimiento debe ser mayor a cero")
    rendimiento = Decimal(rendimiento)

    detalle = []
    totales = {"barato": CERO, "promedio": CERO, "caro": CERO}
    incompleto = False

    for ins in insumos:
        cantidad = Decimal(ins["cantidad"])
        if cantidad <= 0:
            raise ValueError(f"La cantidad de cada insumo debe ser mayor a cero")
        precios = precios_insumo(sesion, ins["tipo"], ins["id_insumo"], meses)
        fila = dict(precios)
        fila["cantidad"] = float(cantidad)
        if precios["barato"] is None:
            incompleto = True
            fila["costo_barato"] = fila["costo_promedio"] = fila["costo_caro"] = None
        else:
            for k in ("barato", "promedio", "caro"):
                costo = cantidad * Decimal(str(precios[k]))
                fila[f"costo_{k}"] = float(costo)
                totales[k] += costo
        detalle.append(fila)

    botellas = (rendimiento / Decimal(str(litros_por_botella))
                if litros_por_botella and Decimal(str(litros_por_botella)) > 0 else None)
    bpp = Decimal(str(botellas_por_paquete or 1))

    referencia = indicadores_referencia(sesion, meses)
    carga = Decimal(str(referencia["total"]))

    escenarios = {}
    for k in ("barato", "promedio", "caro"):
        total = totales[k]
        por_botella = (total / botellas) if botellas and botellas > 0 else None
        escenarios[k] = {
            "costo_total": float(total),
            "por_unidad": float(total / rendimiento),
            "por_botella": float(por_botella) if por_botella is not None else None,
            "por_paquete": float(por_botella * bpp) if por_botella is not None else None,
            # Mismo escenario, pero cargando ademas la mano de obra, la
            # absorcion y los gastos extra promedio (referencia de arriba).
            "por_botella_con_carga": float(por_botella + carga) if por_botella is not None else None,
            "por_paquete_con_carga": float((por_botella + carga) * bpp) if por_botella is not None else None,
        }

    desde, hasta = _ventana(meses)
    return {
        "ventana": {
            "meses": meses,
            "desde": desde.isoformat() if desde else None,
            "hasta": hasta.isoformat(),
        },
        "rendimiento": float(rendimiento),
        "litros_por_botella": float(litros_por_botella) if litros_por_botella else None,
        "botellas_por_paquete": int(bpp),
        "botellas_resultantes": float(botellas) if botellas is not None else None,
        "insumos": detalle,
        "escenarios": escenarios,
        "referencia": referencia,
        "incompleto": incompleto,
    }
