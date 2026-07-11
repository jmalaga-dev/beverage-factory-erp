"""
transferencias.py
Logica de negocio para mover dinero entre cuentas propias (transferencia) y
para registrar dinero que entra desde fuera de la fabrica (ingreso externo,
ej. un aporte del conyuge o del banco). Ninguna de las dos es una venta ni
un gasto, por eso usan su propio Tipo_Movimiento ("TRANSFERENCIA" /
"INGRESO_EXTERNO") en vez de "ENTRADA"/"SALIDA": si usaran esos, el balance
las contaria por descarte como venta o como gasto de la semana (mismo
principio de "categorizar sin adivinar" de la mejora 4.1). Atomico.
"""

from app.models import Cuenta, Movimiento


def registrar_transferencia(sesion, id_cuenta_origen, id_cuenta_destino, monto, descripcion, fecha=None):
    """
    Mueve dinero de una cuenta propia a otra.

    Devuelve: el objeto Movimiento creado.
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES -----

    if id_cuenta_origen == id_cuenta_destino:
        raise ValueError("La cuenta de origen y destino no pueden ser la misma")

    origen = sesion.get(Cuenta, id_cuenta_origen)
    if origen is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta_origen}")

    destino = sesion.get(Cuenta, id_cuenta_destino)
    if destino is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta_destino}")

    if monto <= 0:
        raise ValueError("El monto de la transferencia debe ser mayor a cero")

    if origen.Saldo_Actual_Cuenta < monto:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{origen.Nombre_Cuenta}' tiene "
            f"{origen.Saldo_Actual_Cuenta} Bs y la transferencia es de {monto} Bs"
        )

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="TRANSFERENCIA",
            Id_Cuenta_Origen=id_cuenta_origen,
            Id_Cuenta_Destino=id_cuenta_destino,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=descripcion,
        )
        sesion.add(movimiento)

        origen.Saldo_Actual_Cuenta = origen.Saldo_Actual_Cuenta - monto
        destino.Saldo_Actual_Cuenta = destino.Saldo_Actual_Cuenta + monto

        sesion.commit()
        return movimiento

    except Exception as e:
        sesion.rollback()
        raise e


def registrar_ingreso_externo(sesion, id_cuenta_destino, monto, descripcion, fecha=None):
    """
    Registra dinero que entra a una cuenta desde fuera de la fabrica
    (aporte externo), sin salir de ninguna otra cuenta propia.

    Devuelve: el objeto Movimiento creado.
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES -----

    destino = sesion.get(Cuenta, id_cuenta_destino)
    if destino is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta_destino}")

    if monto <= 0:
        raise ValueError("El monto del ingreso debe ser mayor a cero")

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="INGRESO_EXTERNO",
            Id_Cuenta_Origen=None,
            Id_Cuenta_Destino=id_cuenta_destino,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=descripcion,
        )
        sesion.add(movimiento)

        destino.Saldo_Actual_Cuenta = destino.Saldo_Actual_Cuenta + monto

        sesion.commit()
        return movimiento

    except Exception as e:
        sesion.rollback()
        raise e
