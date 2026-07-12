"""
recetas.py
Pre-recetas de produccion intermedia (mejora 3.6).

Una receta define los insumos (MP e intermedios) para producir un producto
intermedio, para un rendimiento base. Al aplicarla para producir una cantidad
X, se escala cada insumo por X / rendimiento y se resuelven los lotes por FIFO
(mejora 3.1). El resultado pre-llena el formulario de produccion; el usuario
lo edita antes de confirmar (las horas de trabajo se agregan aparte).
"""

from app.models import Receta, Receta_Detalle, Materia_Prima, Producto_Intermedio
from app.servicios.fifo import resolver_fifo


def aplicar_receta(sesion, id_receta, cantidad_a_producir):
    """
    Escala la receta a la cantidad pedida y resuelve los lotes por FIFO.

    Devuelve un dict con:
        tipo: INTERMEDIO / TERMINADO (que clase de producto produce)
        id_producto: id del intermedio o terminado que se produce
        cantidad_producir: la cantidad pedida (eco)
        insumos_mp: [{id_compra, cantidad, ...}]  (lotes FIFO de cada MP)
        insumos_intermedio: [{id_prod, cantidad, ...}]  (lotes FIFO de cada intermedio)
        faltantes: [{tipo, id, nombre, faltante}]  materias/intermedios sin stock suficiente

    Insumos repetidos (la misma materia/intermedio en varias filas de la
    receta) se SUMAN antes de resolver FIFO, para no resolver dos veces desde
    el stock completo y terminar tomando el mismo lote dos veces.
    """
    receta = sesion.get(Receta, id_receta)
    if receta is None:
        raise ValueError(f"No existe receta con Id {id_receta}")
    cantidad_a_producir = float(cantidad_a_producir)
    if cantidad_a_producir <= 0:
        raise ValueError("La cantidad a producir debe ser mayor a cero")

    rendimiento = float(receta.Rendimiento_Receta)
    if rendimiento <= 0:
        raise ValueError("La receta tiene un rendimiento inválido")
    factor = cantidad_a_producir / rendimiento

    # 1) Sumar las cantidades escaladas por (tipo de insumo, id), para que un
    #    insumo repetido se resuelva UNA sola vez con su total.
    totales = {}  # (tipo, id) -> cantidad total escalada
    detalles = sesion.query(Receta_Detalle).filter(Receta_Detalle.Id_Receta == id_receta).all()
    for det in detalles:
        cantidad_escalada = float(det.Cantidad_Receta) * factor
        if cantidad_escalada <= 0:
            continue
        id_ins = det.Id_Materia_Prima if det.Tipo_Insumo_Receta == "MP" else det.Id_Producto_Intermedio
        clave = (det.Tipo_Insumo_Receta, id_ins)
        totales[clave] = totales.get(clave, 0) + cantidad_escalada

    # 2) Resolver FIFO una vez por insumo unico.
    insumos_mp = []
    insumos_intermedio = []
    faltantes = []
    for (tipo, id_prod), cantidad_total in totales.items():
        if tipo == "MP":
            resuelto = resolver_fifo(sesion, "MP", id_prod, cantidad_total)
            for a in resuelto["asignaciones"]:
                insumos_mp.append({"id_compra": a["id_lote"], "cantidad": a["cantidad"],
                                   "costo_unitario": a["costo_unitario"]})
            if resuelto["faltante"] > 0:
                mp = sesion.get(Materia_Prima, id_prod)
                faltantes.append({"tipo": "MP", "id": id_prod,
                                  "nombre": mp.Descripcion_Materia_Prima if mp else str(id_prod),
                                  "faltante": resuelto["faltante"]})
        else:  # INTERMEDIO
            resuelto = resolver_fifo(sesion, "INTERMEDIO", id_prod, cantidad_total)
            for a in resuelto["asignaciones"]:
                insumos_intermedio.append({"id_prod": a["id_lote"], "cantidad": a["cantidad"],
                                           "costo_unitario": a["costo_unitario"]})
            if resuelto["faltante"] > 0:
                pi = sesion.get(Producto_Intermedio, id_prod)
                faltantes.append({"tipo": "INTERMEDIO", "id": id_prod,
                                  "nombre": pi.Descripcion_Producto_Intermedio if pi else str(id_prod),
                                  "faltante": resuelto["faltante"]})

    id_producto = receta.Id_Producto_Terminado if receta.Tipo_Receta == "TERMINADO" else receta.Id_Producto_Intermedio
    return {
        "tipo": receta.Tipo_Receta,
        "id_producto": id_producto,
        "cantidad_producir": cantidad_a_producir,
        "insumos_mp": insumos_mp,
        "insumos_intermedio": insumos_intermedio,
        "faltantes": faltantes,
    }
