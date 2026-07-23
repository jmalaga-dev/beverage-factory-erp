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


def listar_ingresos_externos(sesion):
    """Ingresos externos registrados, con el nombre de la cuenta y si ya fueron
    anulados (para el historial y el boton de anular, item 10a)."""
    ingresos = (
        sesion.query(Movimiento)
        .filter(Movimiento.Tipo_Movimiento == "INGRESO_EXTERNO")
        .order_by(Movimiento.Id_Movimiento.desc())
        .all()
    )
    # Ids de ingresos que ya tienen una anulacion apuntandoles.
    anulados = {
        v for (v,) in sesion.query(Movimiento.Id_Movimiento_Anulado)
        .filter(Movimiento.Tipo_Movimiento == "ANULACION_INGRESO_EXTERNO").distinct()
        if v is not None
    }
    resultado = []
    for m in ingresos:
        cuenta = sesion.get(Cuenta, m.Id_Cuenta_Destino)
        resultado.append({
            "id_movimiento": m.Id_Movimiento,
            "fecha": m.Fecha_Movimiento.isoformat() if m.Fecha_Movimiento else None,
            "cuenta": cuenta.Nombre_Cuenta if cuenta else "?",
            "id_cuenta": m.Id_Cuenta_Destino,
            "monto": float(m.Monto_Movimiento),
            "descripcion": m.Descripcion_Movimiento,
            "anulado": m.Id_Movimiento in anulados,
        })
    return resultado


def anular_ingreso_externo(sesion, id_movimiento, fecha=None):
    """Anula un ingreso externo mal cargado con un movimiento INVERSO (item 10a).
    No borra el original (inmutabilidad): baja el saldo de la cuenta por el mismo
    monto y deja la anulacion enlazada al ingreso. Solo si el saldo alcanza (si
    el dinero ya se movio/gasto, no se puede anular limpio)."""
    mov = sesion.get(Movimiento, id_movimiento)
    if mov is None:
        raise ValueError(f"No existe movimiento con Id {id_movimiento}")
    if mov.Tipo_Movimiento != "INGRESO_EXTERNO":
        raise ValueError("Solo se pueden anular ingresos externos")

    ya_anulado = sesion.query(Movimiento).filter(
        Movimiento.Tipo_Movimiento == "ANULACION_INGRESO_EXTERNO",
        Movimiento.Id_Movimiento_Anulado == id_movimiento,
    ).first()
    if ya_anulado is not None:
        raise ValueError("Este ingreso externo ya fue anulado")

    cuenta = sesion.get(Cuenta, mov.Id_Cuenta_Destino)
    if cuenta is None:
        raise ValueError(f"No existe la cuenta destino (Id {mov.Id_Cuenta_Destino})")
    if cuenta.Saldo_Actual_Cuenta < mov.Monto_Movimiento:
        raise ValueError(
            f"No se puede anular: la cuenta '{cuenta.Nombre_Cuenta}' ya no tiene ese "
            f"saldo ({cuenta.Saldo_Actual_Cuenta} Bs, se necesitan {mov.Monto_Movimiento}). "
            f"El dinero ya se movió o gastó; registrá el ajuste como corresponda."
        )

    try:
        anulacion = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="ANULACION_INGRESO_EXTERNO",
            Id_Cuenta_Origen=cuenta.Id_Cuenta,   # el dinero sale de la cuenta
            Id_Cuenta_Destino=None,
            Monto_Movimiento=mov.Monto_Movimiento,
            Descripcion_Movimiento=f"Anulación de ingreso externo #{id_movimiento}: {mov.Descripcion_Movimiento or ''}".strip(),
            Id_Movimiento_Anulado=id_movimiento,
        )
        sesion.add(anulacion)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - mov.Monto_Movimiento
        sesion.commit()
        return anulacion
    except Exception as e:
        sesion.rollback()
        raise e


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
