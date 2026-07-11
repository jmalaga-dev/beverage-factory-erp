"""
produccion_terminado.py
Logica para producir un producto terminado (lo que se vende).
Consume lotes especificos de producciones intermedias, materia prima directa
y/o horas de trabajo. Valida stock de cada lote, descuenta, calcula costo
unitario y registra todo con trazabilidad. Atomico.
"""

from app.models import (
    Producto_Terminado, Produccion,
    Detalle_Prod_Intermedio, Detalle_Prod_Materia_Prima, Detalle_Prod_Trabajador,
    Produccion_Intermedio, Compra, Registro_Trabajador, Trabajador,
)
from app.servicios.absorcion import absorber_en_produccion


def producir_terminado(
    sesion,
    id_producto_terminado,
    cantidad_producida,
    insumos_intermedio=None,  # lista de (id_produccion_intermedio, cantidad)
    insumos_mp=None,          # lista de (id_compra, cantidad)
    insumos_trabajo=None,     # lista de (id_registro_trabajador, horas)
    fecha=None,
):
    """
    Produce un producto terminado consumiendo lotes especificos de insumos.
    Devuelve el objeto Produccion creado, con su costo unitario calculado.
    Lanza ValueError si algun lote no tiene suficiente restante o no existe.
    """

    insumos_intermedio = insumos_intermedio or []
    insumos_mp = insumos_mp or []
    insumos_trabajo = insumos_trabajo or []

    # ----- 1. VALIDACIONES y calculo del costo total -----

    producto = sesion.get(Producto_Terminado, id_producto_terminado)
    if producto is None:
        raise ValueError(f"No existe producto terminado con Id {id_producto_terminado}")

    if cantidad_producida <= 0:
        raise ValueError("La cantidad producida debe ser mayor a cero")

    if not insumos_intermedio and not insumos_mp and not insumos_trabajo:
        raise ValueError("Debe consumir al menos un insumo para producir")

    costo_total = 0

    # Producciones intermedias: validar lote, costo y stock
    for id_prod_int, cantidad in insumos_intermedio:
        prod_int = sesion.get(Produccion_Intermedio, id_prod_int)
        if prod_int is None:
            raise ValueError(f"No existe produccion intermedia con Id {id_prod_int}")
        if cantidad <= 0:
            raise ValueError(f"La cantidad usada del intermedio {id_prod_int} debe ser mayor a cero")
        if prod_int.Cantidad_Restante_Producida < cantidad:
            raise ValueError(
                f"Produccion intermedia {id_prod_int} no tiene suficiente. "
                f"Restante: {prod_int.Cantidad_Restante_Producida}, se pide: {cantidad}"
            )
        costo_unitario_int = prod_int.Costo_Unitario_Produccion_Intermedio
        if costo_unitario_int is None:
            raise ValueError(
                f"La produccion intermedia {id_prod_int} no tiene costo unitario calculado"
            )
        costo_total += cantidad * costo_unitario_int

    # Materia prima directa: validar lote, costo (precio real del lote) y stock
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

    # Trabajo: validar jornada, costo (tarifa pactada) y horas restantes
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
        costo_total += horas * trabajador.Pago_Trabajador

    # ----- 2. EJECUTAR (todo o nada) -----
    # El costo unitario se fija DESPUES de la absorcion (2f), porque esta
    # depende del Id_Produccion (que se asigna al hacer flush).

    try:
        # 2a. Cabecera de produccion (el costo unitario se completa en 2f)
        produccion = Produccion(
            Id_Producto_Terminado=id_producto_terminado,
            Fecha_Produccion=fecha,
            Cantidad_Producida_Produccion=cantidad_producida,
            Precio_Unitario_Producto_Terminado=None,
            Cantidad_Restante_Produccion=cantidad_producida,
        )
        sesion.add(produccion)
        sesion.flush()  # para obtener el Id_Produccion

        # 2b. Intermedios: detalle + descuento
        for id_prod_int, cantidad in insumos_intermedio:
            prod_int = sesion.get(Produccion_Intermedio, id_prod_int)
            sesion.add(Detalle_Prod_Intermedio(
                Id_Produccion=produccion.Id_Produccion,
                Id_Produccion_Intermedio=id_prod_int,
                Cantidad_Usada=cantidad,
            ))
            prod_int.Cantidad_Restante_Producida = (
                prod_int.Cantidad_Restante_Producida - cantidad
            )

        # 2c. Materia prima directa: detalle + descuento
        for id_compra, cantidad in insumos_mp:
            compra = sesion.get(Compra, id_compra)
            sesion.add(Detalle_Prod_Materia_Prima(
                Id_Produccion=produccion.Id_Produccion,
                Id_Compra=id_compra,
                Cantidad_Usada=cantidad,
            ))
            compra.Cantidad_Restante_Compra = compra.Cantidad_Restante_Compra - cantidad

        # 2d. Trabajo: detalle + descuento de horas
        for id_registro, horas in insumos_trabajo:
            registro = sesion.get(Registro_Trabajador, id_registro)
            sesion.add(Detalle_Prod_Trabajador(
                Id_Produccion=produccion.Id_Produccion,
                Id_Registro_Trabajador=id_registro,
                Horas_Usadas=horas,
            ))
            registro.Horas_Restante_Registro_Trabajador = (
                registro.Horas_Restante_Registro_Trabajador - horas
            )

        # 2e. Absorcion de costos indirectos por botella (mejora 1.4): los
        # utensilios/feriados/mermas con saldo cargan su parte a estas botellas.
        costo_absorbido = absorber_en_produccion(sesion, produccion.Id_Produccion, cantidad_producida)

        # 2f. Fijar el costo unitario final (insumos + absorcion)
        produccion.Precio_Unitario_Producto_Terminado = (costo_total + costo_absorbido) / cantidad_producida

        # 2g. Confirmar todo
        sesion.commit()

        return produccion

    except Exception as e:
        sesion.rollback()
        raise e