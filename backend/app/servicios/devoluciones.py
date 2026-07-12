"""
devoluciones.py
Devolucion completa de una venta (mejora 3.3).

Una devolucion combina, de forma atomica:
  1. DINERO: sale un reembolso de una cuenta (Movimiento SALIDA). Puede ser 0
     si no se devuelve plata (ej. cambio por otro producto).
  2. PRODUCTO: el producto devuelto SIEMPRE vuelve primero al stock del lote
     original (Movimiento_Inventario DEVOLUCION ENTRADA), y luego, segun el
     destino elegido:
       - STOCK    -> se queda (esta bueno, se puede revender).
       - MERMA    -> se desecha; su costo lo absorben las botellas futuras (1.4).
       - REPROCESO-> se reprocesa en un lote nuevo (ver reproceso.py).

El "volver al stock y luego mermarlo/reprocesarlo" deja el rastro completo en
inventario (entro y despues salio), que es justo lo que paso en la realidad.

Opcionalmente se vincula a la venta original (id_venta) para validar que ese
lote se vendio ahi y que no se devuelva mas de lo vendido.
"""

from app.models import Produccion, Cuenta, Movimiento, Venta, Detalle_Venta
from app.servicios.inventario import _aplicar_movimiento_inventario
from app.servicios.reproceso import reprocesar


def registrar_devolucion(
    sesion, id_produccion, cantidad, id_cuenta, monto_reembolso, destino,
    id_venta=None, motivo=None, fecha=None,
    absorber_costo=True, botellas_estimadas_absorcion=None, reproceso=None,
):
    """
    Registra una devolucion completa.

    destino: STOCK / MERMA / REPROCESO
    reproceso: (solo si destino=REPROCESO) dict con:
        {"cantidad_producida": Decimal,
         "insumos_mp": [(id_compra, cantidad), ...],
         "insumos_trabajo": [(id_registro, horas), ...]}
    Devuelve un dict con el resultado.
    """

    # ----- VALIDACIONES -----
    if destino not in ("STOCK", "MERMA", "REPROCESO"):
        raise ValueError(f"Destino invalido: {destino}")

    produccion = sesion.get(Produccion, id_produccion)
    if produccion is None:
        raise ValueError(f"No existe lote de produccion con Id {id_produccion}")
    if cantidad <= 0:
        raise ValueError("La cantidad devuelta debe ser mayor a cero")

    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")
    if monto_reembolso < 0:
        raise ValueError("El monto de reembolso no puede ser negativo")
    if cuenta.Saldo_Actual_Cuenta < monto_reembolso:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el reembolso es de {monto_reembolso} Bs"
        )

    # Vinculo opcional con la venta original: el lote debe haberse vendido ahi
    # y no se puede devolver mas de lo que se vendio de ese lote en esa venta.
    if id_venta is not None:
        venta = sesion.get(Venta, id_venta)
        if venta is None:
            raise ValueError(f"No existe venta con Id {id_venta}")
        vendido = sum(
            float(d.Cantidad_Venta)
            for d in sesion.query(Detalle_Venta)
            .filter_by(Id_Venta=id_venta, Id_Produccion=id_produccion).all()
        )
        if vendido <= 0:
            raise ValueError(f"La venta {id_venta} no incluye el lote {id_produccion}")
        if float(cantidad) > vendido:
            raise ValueError(
                f"No se puede devolver {cantidad}: en la venta {id_venta} se "
                f"vendieron {vendido} de ese lote"
            )

    if destino == "REPROCESO" and not reproceso:
        raise ValueError("Falta la informacion del reproceso (cantidad producida e insumos)")

    # ----- EJECUTAR (todo o nada) -----
    try:
        desc = motivo.strip() if motivo and motivo.strip() else "Devolucion de venta"
        if id_venta is not None:
            desc = f"{desc} (venta {id_venta})"

        # 1. Reembolso: SALIDA de dinero de la cuenta (si hay monto)
        if monto_reembolso > 0:
            movimiento = Movimiento(
                Fecha_Movimiento=fecha,
                Tipo_Movimiento="SALIDA",
                Id_Cuenta_Origen=id_cuenta,
                Id_Cuenta_Destino=None,
                Monto_Movimiento=monto_reembolso,
                Descripcion_Movimiento=f"Reembolso: {desc}",
            )
            sesion.add(movimiento)
            cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto_reembolso

        # 2. El producto vuelve al stock del lote original (siempre)
        _aplicar_movimiento_inventario(
            sesion, tipo="DEVOLUCION", sentido="ENTRADA", origen_lote="PRODUCCION",
            cantidad=cantidad, id_produccion=id_produccion, fecha=fecha,
            motivo=desc, absorber_costo=False,
        )

        # 3. Destino del producto devuelto
        if destino == "MERMA":
            _aplicar_movimiento_inventario(
                sesion, tipo="MERMA", sentido="SALIDA", origen_lote="PRODUCCION",
                cantidad=cantidad, id_produccion=id_produccion, fecha=fecha,
                motivo=f"Devolucion desechada: {desc}",
                absorber_costo=absorber_costo,
                botellas_estimadas_absorcion=botellas_estimadas_absorcion,
            )
            resultado_extra = {}
        elif destino == "REPROCESO":
            nuevo = reprocesar(
                sesion, id_produccion_origen=id_produccion, cantidad=cantidad,
                cantidad_producida=reproceso["cantidad_producida"],
                insumos_mp=reproceso.get("insumos_mp"),
                insumos_trabajo=reproceso.get("insumos_trabajo"),
                motivo=f"Reproceso de devolucion: {desc}", fecha=fecha, _commit=False,
            )
            resultado_extra = {
                "id_produccion_nuevo": nuevo.Id_Produccion,
                "costo_unitario_nuevo": float(nuevo.Precio_Unitario_Producto_Terminado),
            }
        else:  # STOCK
            resultado_extra = {}

        sesion.commit()
        return {"id_produccion": id_produccion, "destino": destino, **resultado_extra}

    except Exception as e:
        sesion.rollback()
        raise e
