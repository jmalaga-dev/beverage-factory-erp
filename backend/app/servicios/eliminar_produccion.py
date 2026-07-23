"""
eliminar_produccion.py
Eliminar una produccion (intermedia o terminada) recien creada, SOLO si esta
"intacta" (item 6a). Mismo criterio que las jornadas (mejora 3.4): sirve para
corregir un error de tipeo apenas hecho (ej. se cargó el insumo equivocado),
antes de que nada dependa de esa produccion.

"Intacta" = su lote sigue exactamente como se produjo (nada consumido, vendido,
mermado ni reprocesado desde el). Si ya se uso, no se puede eliminar: hay que ir
por merma/reproceso (que respetan la inmutabilidad del historico registrando un
evento nuevo). Al eliminar, se DESHACE todo lo que la produccion habia hecho:
devuelve el stock de los insumos consumidos, las horas de las jornadas, y —en
terminado— las botellas a los items de absorcion. Todo atomico.

Editar = eliminar + volver a crear con los datos corregidos (lo hace el frontend
reutilizando el formulario de produccion), asi no hay que recalcular en cascada.
"""

from app.models import (
    Produccion, Produccion_Intermedio,
    Detalle_PI_Materia_Prima, Detalle_PI_Trabajo, Detalle_PI_Intermedio,
    Detalle_Prod_Intermedio, Detalle_Prod_Materia_Prima, Detalle_Prod_Trabajador,
    Compra, Registro_Trabajador,
    Absorcion_Produccion, Item_Absorcion,
    Detalle_Venta, Movimiento_Inventario,
)


def eliminar_produccion_intermedia(sesion, id_produccion_intermedio):
    """Elimina una produccion intermedia intacta, devolviendo sus insumos."""
    prod = sesion.get(Produccion_Intermedio, id_produccion_intermedio)
    if prod is None:
        raise ValueError(f"No existe produccion intermedia con Id {id_produccion_intermedio}")

    # ----- Guard "intacta" -----
    if prod.Cantidad_Restante_Producida != prod.Cantidad_Producida:
        raise ValueError(
            "No se puede eliminar: ya se consumió parte de este lote. "
            "Para corregirlo ahora hay que registrar una merma o un reproceso."
        )
    # Nadie aguas abajo lo consumio (otra produccion intermedia o un terminado)
    usado_en_intermedio = sesion.query(Detalle_PI_Intermedio).filter(
        Detalle_PI_Intermedio.Id_Produccion_Intermedio_Origen == id_produccion_intermedio
    ).first()
    usado_en_terminado = sesion.query(Detalle_Prod_Intermedio).filter(
        Detalle_Prod_Intermedio.Id_Produccion_Intermedio == id_produccion_intermedio
    ).first()
    mermado = sesion.query(Movimiento_Inventario).filter(
        Movimiento_Inventario.Id_Produccion_Intermedio == id_produccion_intermedio
    ).first()
    if usado_en_intermedio or usado_en_terminado or mermado:
        raise ValueError(
            "No se puede eliminar: este lote ya se usó (en otra producción o una "
            "merma). Corrígelo con merma/reproceso en su lugar."
        )

    try:
        # Devolver materia prima
        for det in sesion.query(Detalle_PI_Materia_Prima).filter_by(
            Id_Produccion_Intermedio=id_produccion_intermedio
        ).all():
            compra = sesion.get(Compra, det.Id_Compra)
            if compra is not None:
                compra.Cantidad_Restante_Compra = compra.Cantidad_Restante_Compra + det.Cantidad_Usada
            sesion.delete(det)

        # Devolver horas de trabajo
        for det in sesion.query(Detalle_PI_Trabajo).filter_by(
            Id_Produccion_Intermedio=id_produccion_intermedio
        ).all():
            registro = sesion.get(Registro_Trabajador, det.Id_Registro_Trabajador)
            if registro is not None:
                registro.Horas_Restante_Registro_Trabajador = (
                    registro.Horas_Restante_Registro_Trabajador + det.Horas_Usadas
                )
            sesion.delete(det)

        # Devolver intermedios consumidos
        for det in sesion.query(Detalle_PI_Intermedio).filter_by(
            Id_Produccion_Intermedio=id_produccion_intermedio
        ).all():
            origen = sesion.get(Produccion_Intermedio, det.Id_Produccion_Intermedio_Origen)
            if origen is not None:
                origen.Cantidad_Restante_Producida = (
                    origen.Cantidad_Restante_Producida + det.Cantidad_Usada
                )
            sesion.delete(det)

        sesion.delete(prod)
        sesion.commit()
        return {"mensaje": "Producción intermedia eliminada", "id": id_produccion_intermedio}
    except Exception as e:
        sesion.rollback()
        raise e


def eliminar_produccion_terminada(sesion, id_produccion):
    """Elimina una produccion terminada intacta, devolviendo insumos y
    revirtiendo la absorcion (las botellas vuelven a sus items)."""
    prod = sesion.get(Produccion, id_produccion)
    if prod is None:
        raise ValueError(f"No existe producción terminada con Id {id_produccion}")

    # ----- Guard "intacta" -----
    if prod.Cantidad_Restante_Produccion != prod.Cantidad_Producida_Produccion:
        raise ValueError(
            "No se puede eliminar: ya se vendió o consumió parte de este lote. "
            "Para corregirlo ahora hay que registrar una devolución, merma o reproceso."
        )
    vendido = sesion.query(Detalle_Venta).filter(
        Detalle_Venta.Id_Produccion == id_produccion
    ).first()
    movimiento = sesion.query(Movimiento_Inventario).filter(
        Movimiento_Inventario.Id_Produccion == id_produccion
    ).first()
    # Reproceso que genero ESTE lote (es un lote derivado, no una produccion normal)
    reproceso_destino = sesion.query(Movimiento_Inventario).filter(
        Movimiento_Inventario.Ref_Reproceso == id_produccion
    ).first()
    if vendido or movimiento or reproceso_destino:
        raise ValueError(
            "No se puede eliminar: este lote ya se usó (venta, merma, devolución o "
            "reproceso). Corrígelo con esos flujos en su lugar."
        )

    try:
        # Devolver intermedios consumidos
        for det in sesion.query(Detalle_Prod_Intermedio).filter_by(
            Id_Produccion=id_produccion
        ).all():
            origen = sesion.get(Produccion_Intermedio, det.Id_Produccion_Intermedio)
            if origen is not None:
                origen.Cantidad_Restante_Producida = (
                    origen.Cantidad_Restante_Producida + det.Cantidad_Usada
                )
            sesion.delete(det)

        # Devolver materia prima
        for det in sesion.query(Detalle_Prod_Materia_Prima).filter_by(
            Id_Produccion=id_produccion
        ).all():
            compra = sesion.get(Compra, det.Id_Compra)
            if compra is not None:
                compra.Cantidad_Restante_Compra = compra.Cantidad_Restante_Compra + det.Cantidad_Usada
            sesion.delete(det)

        # Devolver horas de trabajo (si el cierre ya asigno alguna)
        for det in sesion.query(Detalle_Prod_Trabajador).filter_by(
            Id_Produccion=id_produccion
        ).all():
            registro = sesion.get(Registro_Trabajador, det.Id_Registro_Trabajador)
            if registro is not None:
                registro.Horas_Restante_Registro_Trabajador = (
                    registro.Horas_Restante_Registro_Trabajador + det.Horas_Usadas
                )
            sesion.delete(det)

        # Revertir la absorcion: cada item recupera las botellas que este lote
        # le habia descontado, y se borra el registro de absorcion.
        for absor in sesion.query(Absorcion_Produccion).filter_by(
            Id_Produccion=id_produccion
        ).all():
            item = sesion.get(Item_Absorcion, absor.Id_Item_Absorcion)
            if item is not None:
                item.Botellas_Restantes_Item_Absorcion = (
                    item.Botellas_Restantes_Item_Absorcion + absor.Botellas_Absorbidas
                )
            sesion.delete(absor)

        sesion.delete(prod)
        sesion.commit()
        return {"mensaje": "Producción terminada eliminada", "id": id_produccion}
    except Exception as e:
        sesion.rollback()
        raise e
