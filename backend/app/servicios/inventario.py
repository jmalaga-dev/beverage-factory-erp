"""
inventario.py
Logica para movimientos de inventario: mermas, ajustes, devoluciones, reprocesos.
Principio: nunca se borra stock, se registra el evento. Una SALIDA resta del
lote, una ENTRADA suma. El reproceso son dos registros enlazados por Ref_Reproceso.
"""

from app.models import (
    Movimiento_Inventario, Compra, Produccion, Produccion_Intermedio
)
from app.servicios.absorcion import crear_item_merma


def _get_lote(sesion, origen_lote, id_compra, id_produccion, id_prod_intermedio):
    """Devuelve el objeto lote segun su tipo, o lanza error si no existe."""
    if origen_lote == "COMPRA":
        lote = sesion.get(Compra, id_compra)
        campo = "Cantidad_Restante_Compra"
    elif origen_lote == "PRODUCCION":
        lote = sesion.get(Produccion, id_produccion)
        campo = "Cantidad_Restante_Produccion"
    elif origen_lote == "PRODUCCION_INTERMEDIO":
        lote = sesion.get(Produccion_Intermedio, id_prod_intermedio)
        campo = "Cantidad_Restante_Producida"
    else:
        raise ValueError(f"Origen de lote invalido: {origen_lote}")

    if lote is None:
        raise ValueError(f"No existe el lote indicado ({origen_lote})")

    return lote, campo


def _costo_unitario_lote(lote, origen_lote):
    """Costo unitario del lote, para valorar el stock que se pierde en una
    merma (mejora 1.4). Cada origen guarda su costo de forma distinta."""
    if origen_lote == "COMPRA":
        if not lote.Cantidad_Compra:
            return 0
        return lote.Precio_Compra / lote.Cantidad_Compra
    if origen_lote == "PRODUCCION":
        return lote.Precio_Unitario_Producto_Terminado or 0
    if origen_lote == "PRODUCCION_INTERMEDIO":
        return lote.Costo_Unitario_Produccion_Intermedio or 0
    return 0


def registrar_movimiento_inventario(
    sesion, tipo, sentido, origen_lote, cantidad, motivo=None,
    id_compra=None, id_produccion=None, id_prod_intermedio=None,
    ref_reproceso=None, fecha=None,
    absorber_costo=True, botellas_estimadas_absorcion=None,
):
    """
    Registra un movimiento de inventario sobre un lote.

    tipo: MERMA, AJUSTE, DEVOLUCION o REPROCESO
    sentido: SALIDA (resta del lote) o ENTRADA (suma al lote)
    origen_lote: COMPRA, PRODUCCION o PRODUCCION_INTERMEDIO
    cantidad: cuanto se mueve
    Devuelve el Movimiento_Inventario creado.
    """

    # ----- VALIDACIONES -----
    if tipo not in ("MERMA", "AJUSTE", "DEVOLUCION", "REPROCESO"):
        raise ValueError(f"Tipo invalido: {tipo}")
    if sentido not in ("SALIDA", "ENTRADA"):
        raise ValueError(f"Sentido invalido: {sentido}")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero")

    lote, campo = _get_lote(sesion, origen_lote, id_compra, id_produccion, id_prod_intermedio)

    # Si es SALIDA, validar que el lote tenga suficiente para restar
    restante_actual = getattr(lote, campo)
    if sentido == "SALIDA" and restante_actual < cantidad:
        raise ValueError(
            f"El lote no tiene suficiente. Restante: {restante_actual}, se pide: {cantidad}"
        )

    # ----- EJECUTAR -----
    try:
        movimiento = Movimiento_Inventario(
            Fecha_Movimiento_Inventario=fecha,
            Tipo_Movimiento_Inventario=tipo,
            Sentido_Movimiento_Inventario=sentido,
            Origen_Lote=origen_lote,
            Id_Compra=id_compra,
            Id_Produccion=id_produccion,
            Id_Produccion_Intermedio=id_prod_intermedio,
            Cantidad_Movimiento_Inventario=cantidad,
            Motivo_Movimiento_Inventario=motivo,
            Ref_Reproceso=ref_reproceso,
        )
        sesion.add(movimiento)

        # Ajustar el restante del lote segun el sentido
        if sentido == "SALIDA":
            setattr(lote, campo, restante_actual - cantidad)
        else:  # ENTRADA
            setattr(lote, campo, restante_actual + cantidad)

        # Absorcion del costo de la merma (mejora 1.4): solo una MERMA real
        # (perdida de stock) genera un costo a repartir entre las botellas
        # futuras, y solo si el usuario lo pidio (absorber_costo). Ajustes/
        # devoluciones/reprocesos nunca. Las botellas estimadas las decide la
        # pantalla de Mermas (o la tasa por defecto si no se indican).
        if tipo == "MERMA" and sentido == "SALIDA" and absorber_costo:
            costo_perdido = cantidad * _costo_unitario_lote(lote, origen_lote)
            if costo_perdido > 0:
                desc = motivo.strip() if motivo and motivo.strip() else f"Merma de lote {origen_lote}"
                crear_item_merma(sesion, costo_perdido, f"Merma: {desc}", fecha,
                                 botellas_estimadas=botellas_estimadas_absorcion)

        sesion.commit()
        return movimiento

    except Exception as e:
        sesion.rollback()
        raise e