"""
fifo.py
Resolucion FIFO (primero en entrar, primero en salir) de lotes (mejora 3.1).

Dado un producto (materia prima, intermedio o terminado) y una cantidad,
devuelve que lotes consumir del mas antiguo al mas nuevo, respetando el
restante de cada uno. Es una SUGERENCIA: el frontend la usa para pre-llenar
las listas de insumos/lineas, y el usuario puede editarla antes de confirmar.
Los servicios de produccion/venta siguen recibiendo lotes explicitos.

Es la base de las pre-recetas (3.6) y de la venta con lotes automaticos
(6.12), que llaman a este resolver.
"""

from app.models import Compra, Produccion_Intermedio, Produccion, Materia_Prima, Producto_Intermedio, Producto_Terminado
from app.config import UMBRAL_STOCK_MINIMO


# Config por origen: modelo, campo de la FK al producto, campo de restante,
# campo de fecha, campo de id, y como sacar el costo unitario de un lote.
def _lotes_ordenados(sesion, origen, id_producto):
    """Lotes con stock del producto, del mas antiguo al mas nuevo."""
    if origen == "MP":
        q = (sesion.query(Compra)
             .filter(Compra.Id_Materia_Prima == id_producto,
                     Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO)
             .order_by(Compra.Fecha_Compra, Compra.Id_Compra))
        return [
            {"id_lote": c.Id_Compra,
             "restante": float(c.Cantidad_Restante_Compra),
             "fecha": c.Fecha_Compra.isoformat() if c.Fecha_Compra else None,
             "costo_unitario": float(c.Precio_Compra / c.Cantidad_Compra) if c.Cantidad_Compra else 0}
            for c in q.all()
        ]
    if origen == "INTERMEDIO":
        q = (sesion.query(Produccion_Intermedio)
             .filter(Produccion_Intermedio.Id_Producto_Intermedio == id_producto,
                     Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO)
             .order_by(Produccion_Intermedio.Fecha_Produccion_Intermedio, Produccion_Intermedio.Id_Produccion_Intermedio))
        return [
            {"id_lote": p.Id_Produccion_Intermedio,
             "restante": float(p.Cantidad_Restante_Producida),
             "fecha": p.Fecha_Produccion_Intermedio.isoformat() if p.Fecha_Produccion_Intermedio else None,
             "costo_unitario": float(p.Costo_Unitario_Produccion_Intermedio or 0)}
            for p in q.all()
        ]
    if origen == "TERMINADO":
        q = (sesion.query(Produccion)
             .filter(Produccion.Id_Producto_Terminado == id_producto,
                     Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO)
             .order_by(Produccion.Fecha_Produccion, Produccion.Id_Produccion))
        return [
            {"id_lote": p.Id_Produccion,
             "restante": float(p.Cantidad_Restante_Produccion),
             "fecha": p.Fecha_Produccion.isoformat() if p.Fecha_Produccion else None,
             "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0)}
            for p in q.all()
        ]
    raise ValueError(f"Origen FIFO invalido: {origen} (usar MP / INTERMEDIO / TERMINADO)")


def resolver_fifo(sesion, origen, id_producto, cantidad):
    """
    Reparte 'cantidad' entre los lotes del producto, del mas antiguo al mas
    nuevo. Devuelve un dict:
        {
          "asignaciones": [{id_lote, cantidad, restante, fecha, costo_unitario}, ...],
          "faltante": <cuanto no se pudo cubrir> (0 si alcanzo),
        }
    No toca la BD: solo propone. El faltante > 0 avisa que no hay stock
    suficiente (el frontend lo muestra; el backend igual valida al confirmar).
    """
    cantidad = float(cantidad)
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero")

    lotes = _lotes_ordenados(sesion, origen, id_producto)
    asignaciones = []
    pendiente = cantidad
    for lote in lotes:
        if pendiente <= 0:
            break
        usar = min(pendiente, lote["restante"])
        if usar <= 0:
            continue
        asignaciones.append({
            "id_lote": lote["id_lote"],
            "cantidad": round(usar, 6),
            "restante": lote["restante"],
            "fecha": lote["fecha"],
            "costo_unitario": lote["costo_unitario"],
        })
        pendiente -= usar

    return {"asignaciones": asignaciones, "faltante": round(max(pendiente, 0), 6)}
