"""
ventas.py
Logica para registrar una venta a un cliente.
Una venta tiene varios productos (lineas). Por cada linea:
  - se vende de un lote especifico de producto terminado (descuenta su stock),
  - tiene un precio real de venta,
  - entra dinero.

Por defecto (reparto=True, mejora 2.C) el ingreso de cada linea se reparte
AUTOMATICAMENTE entre la cuenta FABRICA y la CASA segun el 70/30 con
recuperacion de inversion: mientras el producto no recupero lo invertido, el
100% va a Fabrica; despues, el excedente se reparte 70/30. Con reparto=False
vuelve al modo clasico (una cuenta explicita por linea).
Todo atomico: o se registra la venta completa, o nada.
"""

from app.models import (
    Venta, Detalle_Venta, Cliente, Produccion, Cuenta, Movimiento
)
from app.servicios.saldo_producto import saldo_de_producto, dividir_ingreso


def _cuentas_reparto(sesion):
    """(cuenta_fabrica, cuenta_casa) para el reparto 70/30. Exige exactamente
    una cuenta habilitada de cada rol."""
    def unica(rol):
        cs = sesion.query(Cuenta).filter(
            Cuenta.Habilitado_Cuenta.is_(True), Cuenta.Rol_Cuenta == rol
        ).all()
        if len(cs) == 0:
            raise ValueError(
                f"No hay una cuenta con rol {rol} para el reparto 70/30. "
                "Asigná el rol en el catálogo de Cuentas."
            )
        if len(cs) > 1:
            raise ValueError(
                f"Hay más de una cuenta con rol {rol}; el reparto 70/30 necesita "
                "una sola. Ajustá los roles en el catálogo de Cuentas."
            )
        return cs[0]
    return unica("FABRICA"), unica("CASA")


def registrar_venta(sesion, id_cliente, lineas, fecha=None, reparto=True):
    """
    Registra una venta con varias lineas de producto.

    lineas: lista de dicts con id_produccion, cantidad, precio_real y (solo si
    reparto=False) id_cuenta.
    reparto: True = reparto 70/30 automatico Fabrica/Casa (mejora 2.C);
             False = una cuenta explicita por linea (modo clasico).

    Devuelve el objeto Venta creado. Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES (todo antes de tocar nada) -----

    cliente = sesion.get(Cliente, id_cliente)
    if cliente is None:
        raise ValueError(f"No existe cliente con Id {id_cliente}")

    if not lineas:
        raise ValueError("La venta debe tener al menos un producto")

    cuenta_fabrica = cuenta_casa = None
    if reparto:
        cuenta_fabrica, cuenta_casa = _cuentas_reparto(sesion)

    pedido_por_lote = {}
    for linea in lineas:
        produccion = sesion.get(Produccion, linea["id_produccion"])
        if produccion is None:
            raise ValueError(f"No existe lote de produccion con Id {linea['id_produccion']}")

        if linea["cantidad"] <= 0:
            raise ValueError(f"La cantidad del lote {linea['id_produccion']} debe ser mayor a cero")

        if linea["precio_real"] <= 0:
            raise ValueError("El precio real de venta debe ser mayor a cero")

        if not reparto:
            if sesion.get(Cuenta, linea.get("id_cuenta")) is None:
                raise ValueError(f"No existe cuenta con Id {linea.get('id_cuenta')}")

        pedido_por_lote[linea["id_produccion"]] = pedido_por_lote.get(linea["id_produccion"], 0) + linea["cantidad"]

    for id_produccion, total_pedido in pedido_por_lote.items():
        produccion = sesion.get(Produccion, id_produccion)
        if produccion.Cantidad_Restante_Produccion < total_pedido:
            raise ValueError(
                f"Lote {id_produccion} no tiene suficiente stock. "
                f"Restante: {produccion.Cantidad_Restante_Produccion}, se pide: {total_pedido}"
            )

    # Saldo inicial de cada producto de la venta (para el reparto 70/30). Se
    # arranca del saldo real en la BD y se va acumulando linea por linea, asi
    # dos lineas del mismo producto respetan el cruce del cero.
    saldo_por_producto = {}
    if reparto:
        for id_produccion in pedido_por_lote:
            pid = sesion.get(Produccion, id_produccion).Id_Producto_Terminado
            if pid not in saldo_por_producto:
                saldo_por_producto[pid] = saldo_de_producto(sesion, pid)

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        venta = Venta(Id_Cliente=id_cliente, Fecha_Venta=fecha)
        sesion.add(venta)
        sesion.flush()

        for linea in lineas:
            produccion = sesion.get(Produccion, linea["id_produccion"])
            total_linea = linea["cantidad"] * linea["precio_real"]

            # Determinar a qué cuenta(s) entra el dinero
            if reparto:
                pid = produccion.Id_Producto_Terminado
                a_fabrica, a_casa = dividir_ingreso(saldo_por_producto[pid], total_linea)
                saldo_por_producto[pid] = saldo_por_producto[pid] + total_linea
                destinos = [(cuenta_fabrica, a_fabrica), (cuenta_casa, a_casa)]
            else:
                destinos = [(sesion.get(Cuenta, linea["id_cuenta"]), total_linea)]

            # Una ENTRADA por destino con monto > 0 (Fabrica y/o Casa)
            mov_principal = None
            for cuenta, monto in destinos:
                if monto <= 0:
                    continue
                movimiento = Movimiento(
                    Fecha_Movimiento=fecha,
                    Tipo_Movimiento="ENTRADA",
                    Id_Cuenta_Origen=None,             # viene de fuera (el cliente paga)
                    Id_Cuenta_Destino=cuenta.Id_Cuenta,
                    Monto_Movimiento=monto,
                    Descripcion_Movimiento=f"Venta a {cliente.Nombre_Cliente}",
                )
                sesion.add(movimiento)
                sesion.flush()
                cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta + monto
                if mov_principal is None:
                    mov_principal = movimiento

            # Linea de venta, vinculada a uno de los movimientos (traza)
            sesion.add(Detalle_Venta(
                Id_Venta=venta.Id_Venta,
                Id_Produccion=linea["id_produccion"],
                Cantidad_Venta=linea["cantidad"],
                Precio_Venta_Real=linea["precio_real"],
                Id_Movimiento=mov_principal.Id_Movimiento if mov_principal else None,
            ))

            produccion.Cantidad_Restante_Produccion = (
                produccion.Cantidad_Restante_Produccion - linea["cantidad"]
            )

        sesion.commit()
        return venta

    except Exception as e:
        sesion.rollback()
        raise e