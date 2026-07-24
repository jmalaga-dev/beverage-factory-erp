"""
gastos.py
Logica de negocio para registrar un gasto diario.
Un gasto sale de UNA cuenta, pertenece a un grupo (etiqueta validada para
analisis), y descuenta el saldo. No toca inventario.
"""

from app.models import Gasto_Extra, Cuenta, Movimiento, Grupo_Movimiento


def _aplicar_gasto(sesion, id_cuenta, monto, descripcion, id_grupo=None, fecha=None):
    """
    Aplica un gasto SIN hacer commit: valida y descuenta la cuenta. Se deja
    sin commit para poder COMPONER varios gastos en una sola transaccion
    (la tabla de gastos = N gastos que se registran todos o ninguno; ver
    gastos_lote.py).

    Parametros:
        sesion: la sesion de SQLAlchemy
        id_cuenta: de que cuenta sale el dinero
        monto: cuanto se gasta
        descripcion: en que se gasto
        id_grupo: etiqueta de grupo (comida, mantenimiento, limpieza...), opcional
        fecha: fecha del gasto

    Devuelve: el objeto Movimiento creado (sin commit).
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES -----

    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")

    if monto <= 0:
        raise ValueError("El monto del gasto debe ser mayor a cero")

    # Si se indica grupo, debe existir (lista validada)
    if id_grupo is not None:
        grupo = sesion.get(Grupo_Movimiento, id_grupo)
        if grupo is None:
            raise ValueError(f"No existe grupo de movimiento con Id {id_grupo}")

    # Validacion clave: la cuenta debe tener saldo suficiente
    if cuenta.Saldo_Actual_Cuenta < monto:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el gasto es de {monto} Bs"
        )

    # ----- 2. EJECUTAR (sin commit) -----

    # Movimiento de SALIDA (sale de la cuenta, sin destino: gasto real)
    movimiento = Movimiento(
        Fecha_Movimiento=fecha,
        Tipo_Movimiento="SALIDA",
        Id_Cuenta_Origen=id_cuenta,
        Id_Cuenta_Destino=None,
        Monto_Movimiento=monto,
        Descripcion_Movimiento=descripcion,
        Id_Grupo_Movimiento=id_grupo,
    )
    sesion.add(movimiento)

    # Descontar el saldo de la cuenta
    cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto

    return movimiento


def registrar_gasto(sesion, id_cuenta, monto, descripcion, id_grupo=None, fecha=None):
    """Registra un gasto suelto y hace commit. Envuelve a _aplicar_gasto."""
    try:
        movimiento = _aplicar_gasto(
            sesion, id_cuenta, monto, descripcion, id_grupo=id_grupo, fecha=fecha,
        )
        sesion.commit()
        return movimiento
    except Exception as e:
        sesion.rollback()
        raise e


def registrar_gasto_cubierto_externo(sesion, id_cuenta, monto, descripcion,
                                     quien_pago, id_grupo=None, fecha=None):
    """Registra un gasto que pagó alguien de afuera (ej. la cónyuge): el gasto
    se registra igual (cuenta en los reportes de gastos), pero NO reduce tus
    cuentas — lo financia un aporte externo del mismo monto (item 10b, replica
    el "gasto de otro lado que dio ingreso" del Excel).

    Concretamente, en la MISMA transacción: un INGRESO_EXTERNO que entra a la
    cuenta (+monto) y la SALIDA del gasto (-monto). El saldo de la cuenta queda
    IGUAL (neto cero); el gasto aparece como gasto y queda registrado quién lo
    cubrió. Atómico."""
    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")
    if monto <= 0:
        raise ValueError("El monto del gasto debe ser mayor a cero")
    if not quien_pago or not quien_pago.strip():
        raise ValueError("Indicá quién pagó el gasto (el aporte externo)")
    if id_grupo is not None and sesion.get(Grupo_Movimiento, id_grupo) is None:
        raise ValueError(f"No existe grupo de movimiento con Id {id_grupo}")

    try:
        # 1) El aporte externo entra a la cuenta (dinero de fuera de la fábrica)
        ingreso = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="INGRESO_EXTERNO",
            Id_Cuenta_Origen=None,
            Id_Cuenta_Destino=id_cuenta,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=f"Aporte de {quien_pago.strip()} para: {descripcion}",
        )
        sesion.add(ingreso)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta + monto

        # 2) El gasto sale (SALIDA, cuenta como gasto igual que cualquier otro)
        gasto = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=f"{descripcion} (pagado por {quien_pago.strip()})",
            Id_Grupo_Movimiento=id_grupo,
        )
        sesion.add(gasto)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto

        sesion.commit()
        return gasto
    except Exception as e:
        sesion.rollback()
        raise e