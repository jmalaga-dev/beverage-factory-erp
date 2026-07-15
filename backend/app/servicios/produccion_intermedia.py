"""
produccion_intermedia.py
Logica para producir un producto intermedio.
Consume lotes especificos de materia prima, horas de trabajo y/o productos
intermedios previos. Valida stock de cada lote, descuenta, calcula costo
unitario y registra todo con trazabilidad. Atomico.
"""

from app.models import (
    Producto_Intermedio, Produccion_Intermedio,
    Detalle_PI_Materia_Prima, Detalle_PI_Trabajo, Detalle_PI_Intermedio,
    Compra, Registro_Trabajador, Trabajador,
)
from app.servicios.agrupar import agrupar_pares
from app.servicios.horas import horas_heredadas_de
from app.servicios.trabajadores import tarifa_hora


def producir_intermedio(
    sesion,
    id_producto_intermedio,
    cantidad_producida,
    insumos_mp=None,          # lista de (id_compra, cantidad)
    insumos_trabajo=None,     # lista de (id_registro_trabajador, horas)
    insumos_intermedio=None,  # lista de (id_produccion_intermedio_origen, cantidad)
    fecha=None,
):
    """
    Produce un producto intermedio consumiendo lotes especificos de insumos.
    Devuelve el objeto Produccion_Intermedio creado, con su costo unitario calculado.
    Lanza ValueError si algun lote no tiene suficiente restante o no existe.
    """

    # Agrupar lotes repetidos (5+5 del mismo lote = 10), para que la validacion
    # de stock y el descuento usen la cantidad total real y no se pueda dejar
    # el lote en negativo.
    insumos_mp = agrupar_pares(insumos_mp or [])
    insumos_trabajo = agrupar_pares(insumos_trabajo or [])
    insumos_intermedio = agrupar_pares(insumos_intermedio or [])

    # ----- 1. VALIDACIONES y calculo del costo total -----

    producto = sesion.get(Producto_Intermedio, id_producto_intermedio)
    if producto is None:
        raise ValueError(f"No existe producto intermedio con Id {id_producto_intermedio}")

    if cantidad_producida <= 0:
        raise ValueError("La cantidad producida debe ser mayor a cero")

    if not insumos_mp and not insumos_trabajo and not insumos_intermedio:
        raise ValueError("Debe consumir al menos un insumo para producir")

    costo_total = 0
    # Horas-hombre del lote (mejora 1.1): directas (jornadas) + heredadas
    # (de los intermedios consumidos).
    horas_directas = sum(horas for _, horas in insumos_trabajo)
    horas_heredadas = 0

    # Materia prima: validar lote y sumar su costo (precio real del lote)
    for id_compra, cantidad in insumos_mp:
        compra = sesion.get(Compra, id_compra)
        if compra is None:
            raise ValueError(f"No existe compra (lote MP) con Id {id_compra}")
        if cantidad <= 0:
            raise ValueError(f"La cantidad usada del lote {id_compra} debe ser mayor a cero")
        if compra.Cantidad_Restante_Compra < cantidad:
            raise ValueError(
                f"Lote de compra {id_compra} no tiene suficiente. "
                f"Restante: {compra.Cantidad_Restante_Compra}, se pide: {cantidad}"
            )
        precio_unitario = compra.Precio_Compra / compra.Cantidad_Compra
        costo_total += cantidad * precio_unitario

    # Trabajo: validar jornada y sumar su costo (tarifa pactada)
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

    # Intermedios previos: validar lote y sumar su costo (costo unitario x cantidad)
    for id_prod_origen, cantidad in insumos_intermedio:
        prod_origen = sesion.get(Produccion_Intermedio, id_prod_origen)
        if prod_origen is None:
            raise ValueError(f"No existe produccion intermedia con Id {id_prod_origen}")
        if cantidad <= 0:
            raise ValueError(f"La cantidad usada del intermedio {id_prod_origen} debe ser mayor a cero")
        if prod_origen.Cantidad_Restante_Producida < cantidad:
            raise ValueError(
                f"Produccion intermedia {id_prod_origen} no tiene suficiente. "
                f"Restante: {prod_origen.Cantidad_Restante_Producida}, se pide: {cantidad}"
            )
        # Costo del intermedio previo = su costo unitario x cantidad usada
        costo_unitario_origen = prod_origen.Costo_Unitario_Produccion_Intermedio
        if costo_unitario_origen is None:
            raise ValueError(
                f"La produccion intermedia {id_prod_origen} no tiene costo unitario calculado"
            )
        costo_total += cantidad * costo_unitario_origen
        # Hereda las horas del intermedio consumido (mejora 1.1)
        horas_heredadas += horas_heredadas_de(prod_origen, cantidad)

    # Costo unitario del producto que estamos produciendo
    costo_unitario = costo_total / cantidad_producida
    horas_acumuladas = horas_directas + horas_heredadas

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        # 2a. Cabecera de produccion, ya con su costo unitario
        produccion = Produccion_Intermedio(
            Id_Producto_Intermedio=id_producto_intermedio,
            Fecha_Produccion_Intermedio=fecha,
            Cantidad_Producida=cantidad_producida,
            Cantidad_Restante_Producida=cantidad_producida,
            Costo_Unitario_Produccion_Intermedio=costo_unitario,
            Horas_Acumuladas=horas_acumuladas,
        )
        sesion.add(produccion)
        sesion.flush()

        # 2b. Materia prima: detalle + descuento del lote
        for id_compra, cantidad in insumos_mp:
            compra = sesion.get(Compra, id_compra)
            sesion.add(Detalle_PI_Materia_Prima(
                Id_Produccion_Intermedio=produccion.Id_Produccion_Intermedio,
                Id_Compra=id_compra,
                Cantidad_Usada=cantidad,
            ))
            compra.Cantidad_Restante_Compra = compra.Cantidad_Restante_Compra - cantidad

        # 2c. Trabajo: detalle + descuento de horas
        for id_registro, horas in insumos_trabajo:
            registro = sesion.get(Registro_Trabajador, id_registro)
            sesion.add(Detalle_PI_Trabajo(
                Id_Produccion_Intermedio=produccion.Id_Produccion_Intermedio,
                Id_Registro_Trabajador=id_registro,
                Horas_Usadas=horas,
            ))
            registro.Horas_Restante_Registro_Trabajador = (
                registro.Horas_Restante_Registro_Trabajador - horas
            )

        # 2d. Intermedios previos: detalle + descuento
        for id_prod_origen, cantidad in insumos_intermedio:
            prod_origen = sesion.get(Produccion_Intermedio, id_prod_origen)
            sesion.add(Detalle_PI_Intermedio(
                Id_Produccion_Intermedio=produccion.Id_Produccion_Intermedio,
                Id_Produccion_Intermedio_Origen=id_prod_origen,
                Cantidad_Usada=cantidad,
            ))
            prod_origen.Cantidad_Restante_Producida = (
                prod_origen.Cantidad_Restante_Producida - cantidad
            )

        # 2e. Confirmar todo
        sesion.commit()

        return produccion

    except Exception as e:
        sesion.rollback()
        raise e