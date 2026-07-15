"""
reproceso.py
Reproceso de un lote de producto terminado (mejora 3.3).

Se consume una cantidad PARCIAL de un lote existente (ej. re-tapar 10 de 60
botellas porque se rompio la tapa) y se genera un lote NUEVO del MISMO producto
terminado. El costo del lote nuevo ARRASTRA el costo de las botellas de origen
(costo_unitario_origen x cantidad) mas los insumos nuevos que haga falta (tapas
= materia prima, y trabajo). El lote nuevo queda enlazado al de origen por
Ref_Reproceso en el movimiento de inventario que registra la salida del origen.

No corre absorcion de costos indirectos (1.4): esas botellas ya absorbieron su
parte cuando se produjeron; volver a absorber las cobraria dos veces.

Es un pariente de producir_terminado, pero con una diferencia clave: en vez de
partir de intermedios/MP, parte de un lote de producto TERMINADO ya existente.
"""

from app.models import (
    Produccion, Compra, Registro_Trabajador, Trabajador,
    Detalle_Prod_Materia_Prima, Detalle_Prod_Trabajador,
)
from app.servicios.agrupar import agrupar_pares
from app.servicios.horas import horas_por_unidad
from app.servicios.inventario import _aplicar_movimiento_inventario
from app.servicios.trabajadores import tarifa_hora


def reprocesar(
    sesion, id_produccion_origen, cantidad, cantidad_producida,
    insumos_mp=None, insumos_trabajo=None, motivo=None, fecha=None, _commit=True,
):
    """
    Reprocesa 'cantidad' botellas del lote 'id_produccion_origen' en un lote
    nuevo de 'cantidad_producida' botellas del mismo producto.

    _commit: True cuando es una operacion suelta; False cuando corre dentro de
    otra transaccion (una devolucion que reprocesa), que hace el commit final.

    Devuelve el objeto Produccion (lote nuevo) creado.
    """
    insumos_mp = agrupar_pares(insumos_mp or [])
    insumos_trabajo = agrupar_pares(insumos_trabajo or [])

    # ----- 1. VALIDACIONES y costo total -----
    origen = sesion.get(Produccion, id_produccion_origen)
    if origen is None:
        raise ValueError(f"No existe lote de produccion con Id {id_produccion_origen}")
    if cantidad <= 0:
        raise ValueError("La cantidad a reprocesar debe ser mayor a cero")
    if cantidad_producida <= 0:
        raise ValueError("La cantidad producida debe ser mayor a cero")
    if cantidad_producida > cantidad:
        raise ValueError(
            "La cantidad producida no puede superar la que se reprocesa "
            "(el reproceso no crea producto de la nada)"
        )
    if origen.Cantidad_Restante_Produccion < cantidad:
        raise ValueError(
            f"El lote {id_produccion_origen} no tiene suficiente. "
            f"Restante: {origen.Cantidad_Restante_Produccion}, se pide: {cantidad}"
        )

    # Costo arrastrado de las botellas de origen (ya incluye su absorcion previa)
    costo_total = cantidad * (origen.Precio_Unitario_Producto_Terminado or 0)
    # Horas-hombre (mejora 1.1): hereda las de las botellas de origen que
    # consume + el trabajo nuevo del reproceso.
    horas_directas = sum(horas for _, horas in insumos_trabajo)
    horas_heredadas = cantidad * horas_por_unidad(
        origen.Horas_Acumuladas, origen.Cantidad_Producida_Produccion
    )

    # Insumos nuevos: materia prima directa (tapas, etiquetas...) y trabajo
    for id_compra, cant in insumos_mp:
        compra = sesion.get(Compra, id_compra)
        if compra is None:
            raise ValueError(f"No existe compra (lote MP) con Id {id_compra}")
        if cant <= 0:
            raise ValueError(f"La cantidad usada del lote {id_compra} debe ser mayor a cero")
        if compra.Cantidad_Restante_Compra < cant:
            raise ValueError(
                f"Lote de compra {id_compra} no tiene suficiente. "
                f"Restante: {compra.Cantidad_Restante_Compra}, se pide: {cant}"
            )
        costo_total += cant * (compra.Precio_Compra / compra.Cantidad_Compra)

    for id_registro, horas in insumos_trabajo:
        registro = sesion.get(Registro_Trabajador, id_registro)
        if registro is None:
            raise ValueError(f"No existe jornada (registro) con Id {id_registro}")
        if horas <= 0:
            raise ValueError(f"Las horas usadas de la jornada {id_registro} deben ser mayores a cero")
        if registro.Horas_Restante_Registro_Trabajador < horas:
            raise ValueError(
                f"Jornada {id_registro} no tiene suficientes horas. "
                f"Restante: {registro.Horas_Restante_Registro_Trabajador}, se pide: {horas}"
            )
        trabajador = sesion.get(Trabajador, registro.Id_Trabajador)
        costo_total += horas * tarifa_hora(trabajador)

    # ----- 2. EJECUTAR -----
    try:
        # 2a. Lote nuevo (mismo producto que el origen), con su costo unitario
        nuevo = Produccion(
            Id_Producto_Terminado=origen.Id_Producto_Terminado,
            Fecha_Produccion=fecha,
            Cantidad_Producida_Produccion=cantidad_producida,
            Precio_Unitario_Producto_Terminado=costo_total / cantidad_producida,
            Cantidad_Restante_Produccion=cantidad_producida,
            Horas_Acumuladas=horas_directas + horas_heredadas,
        )
        sesion.add(nuevo)
        sesion.flush()  # para obtener el Id_Produccion del lote nuevo

        # 2b. Consumir los insumos nuevos + su detalle (traza)
        for id_compra, cant in insumos_mp:
            compra = sesion.get(Compra, id_compra)
            sesion.add(Detalle_Prod_Materia_Prima(
                Id_Produccion=nuevo.Id_Produccion,
                Id_Compra=id_compra,
                Cantidad_Usada=cant,
            ))
            compra.Cantidad_Restante_Compra = compra.Cantidad_Restante_Compra - cant

        for id_registro, horas in insumos_trabajo:
            registro = sesion.get(Registro_Trabajador, id_registro)
            sesion.add(Detalle_Prod_Trabajador(
                Id_Produccion=nuevo.Id_Produccion,
                Id_Registro_Trabajador=id_registro,
                Horas_Usadas=horas,
            ))
            registro.Horas_Restante_Registro_Trabajador = (
                registro.Horas_Restante_Registro_Trabajador - horas
            )

        # 2c. Salida del lote origen, marcada REPROCESO y enlazada al lote nuevo
        # (Ref_Reproceso = id del lote nuevo). Descuenta el stock del origen.
        _aplicar_movimiento_inventario(
            sesion, tipo="REPROCESO", sentido="SALIDA", origen_lote="PRODUCCION",
            cantidad=cantidad, id_produccion=id_produccion_origen,
            ref_reproceso=nuevo.Id_Produccion, fecha=fecha,
            motivo=motivo or f"Reproceso del lote {id_produccion_origen}",
            absorber_costo=False,
        )

        if _commit:
            sesion.commit()
        return nuevo

    except Exception as e:
        if _commit:
            sesion.rollback()
        raise e
