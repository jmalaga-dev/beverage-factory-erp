"""
gastos.py
Logica de negocio para registrar un gasto diario.
Un gasto sale de UNA cuenta, pertenece a un grupo (etiqueta validada para
analisis), y descuenta el saldo. No toca inventario. Atomico.

Nota: la logica de reparto entre varias cuentas por prioridad se construye
aparte (ver DECISIONES_DISENO.md). Esta es la operacion base que esa capa
invocara una vez por cada cuenta.
"""

from app.models import Gasto_Extra, Cuenta, Movimiento, Grupo_Movimiento


def registrar_gasto(sesion, id_cuenta, monto, descripcion,
                    id_grupo=None, fecha=None):
    """
    Registra un gasto que sale de una cuenta.

    Parametros:
        sesion: la sesion de SQLAlchemy
        id_cuenta: de que cuenta sale el dinero
        monto: cuanto se gasta
        descripcion: en que se gasto
        id_grupo: etiqueta de grupo (comida, mantenimiento, limpieza...), opcional
        fecha: fecha del gasto

    Devuelve: el objeto Movimiento creado.
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

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
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

        sesion.commit()
        return movimiento

    except Exception as e:
        sesion.rollback()
        raise e