"""
ventas.py
Logica para registrar una venta a un cliente.
Una venta tiene varios productos (lineas). Por cada linea:
  - se vende de un lote especifico de producto terminado (descuenta su stock),
  - tiene un precio real de venta,
  - entra dinero a una cuenta (que puede ser distinta por producto).
Todo atomico: o se registra la venta completa, o nada.
"""

from app.models import (
    Venta, Detalle_Venta, Cliente, Produccion, Cuenta, Movimiento
)


def registrar_venta(sesion, id_cliente, lineas, fecha=None):
    """
    Registra una venta con varias lineas de producto.

    Parametros:
        sesion: la sesion de SQLAlchemy
        id_cliente: a quien se vende
        lineas: lista de dicts, cada uno con:
            {
                "id_produccion": <lote de producto terminado>,
                "cantidad": <cuanto se vende>,
                "precio_real": <precio unitario real de venta>,
                "id_cuenta": <a que cuenta entra el dinero>,
            }
        fecha: fecha de la venta

    Devuelve: el objeto Venta creado.
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES (todo antes de tocar nada) -----

    cliente = sesion.get(Cliente, id_cliente)
    if cliente is None:
        raise ValueError(f"No existe cliente con Id {id_cliente}")

    if not lineas:
        raise ValueError("La venta debe tener al menos un producto")

    # Cantidad total pedida por lote (un mismo lote puede venir en varias
    # lineas, ej. a distinto precio): el stock se valida sobre la SUMA, no
    # linea por linea, para no dejar el lote en negativo al descontar.
    pedido_por_lote = {}
    for linea in lineas:
        produccion = sesion.get(Produccion, linea["id_produccion"])
        if produccion is None:
            raise ValueError(f"No existe lote de produccion con Id {linea['id_produccion']}")

        if linea["cantidad"] <= 0:
            raise ValueError(f"La cantidad del lote {linea['id_produccion']} debe ser mayor a cero")

        if linea["precio_real"] <= 0:
            raise ValueError("El precio real de venta debe ser mayor a cero")

        cuenta = sesion.get(Cuenta, linea["id_cuenta"])
        if cuenta is None:
            raise ValueError(f"No existe cuenta con Id {linea['id_cuenta']}")

        pedido_por_lote[linea["id_produccion"]] = pedido_por_lote.get(linea["id_produccion"], 0) + linea["cantidad"]

    for id_produccion, total_pedido in pedido_por_lote.items():
        produccion = sesion.get(Produccion, id_produccion)
        if produccion.Cantidad_Restante_Produccion < total_pedido:
            raise ValueError(
                f"Lote {id_produccion} no tiene suficiente stock. "
                f"Restante: {produccion.Cantidad_Restante_Produccion}, se pide: {total_pedido}"
            )

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        # 2a. Cabecera de la venta
        venta = Venta(
            Id_Cliente=id_cliente,
            Fecha_Venta=fecha,
        )
        sesion.add(venta)
        sesion.flush()  # para obtener el Id_Venta

        # 2b. Cada linea: movimiento de entrada, sube saldo, detalle, descuenta stock
        for linea in lineas:
            produccion = sesion.get(Produccion, linea["id_produccion"])
            cuenta = sesion.get(Cuenta, linea["id_cuenta"])
            total_linea = linea["cantidad"] * linea["precio_real"]

            # Movimiento de ENTRADA de dinero (entra a la cuenta de esta linea)
            movimiento = Movimiento(
                Fecha_Movimiento=fecha,
                Tipo_Movimiento="ENTRADA",
                Id_Cuenta_Origen=None,             # viene de fuera (el cliente paga)
                Id_Cuenta_Destino=linea["id_cuenta"],
                Monto_Movimiento=total_linea,
                Descripcion_Movimiento=f"Venta a {cliente.Nombre_Cliente}",
            )
            sesion.add(movimiento)
            sesion.flush()  # para obtener el Id_Movimiento

            # Subir el saldo de la cuenta
            cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta + total_linea

            # Crear la linea de venta, vinculada al movimiento
            sesion.add(Detalle_Venta(
                Id_Venta=venta.Id_Venta,
                Id_Produccion=linea["id_produccion"],
                Cantidad_Venta=linea["cantidad"],
                Precio_Venta_Real=linea["precio_real"],
                Id_Movimiento=movimiento.Id_Movimiento,
            ))

            # Descontar el stock del lote
            produccion.Cantidad_Restante_Produccion = (
                produccion.Cantidad_Restante_Produccion - linea["cantidad"]
            )

        # 2c. Confirmar todo
        sesion.commit()

        return venta

    except Exception as e:
        sesion.rollback()
        raise e