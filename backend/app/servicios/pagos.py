"""
pagos.py
Logica de negocio para el pago semanal a un trabajador.
Calcula el monto sugerido (horas no pagadas x tarifa pactada), registra el
monto real pagado (que puede diferir), mueve el dinero y marca las jornadas
cubiertas como pagadas. Todo atomico.
"""

from app.models import (
    Trabajador, Registro_Trabajador, Pago_Trabajador, Cuenta, Movimiento
)
from app.servicios.trabajadores import tarifa_hora


def calcular_pago_sugerido(sesion, id_trabajador):
    """
    Calcula cuanto se le debe pagar a un trabajador: suma las horas de sus
    jornadas NO pagadas y las multiplica por su tarifa pactada.
    Devuelve (monto_sugerido, lista_de_jornadas_pendientes).
    """
    trabajador = sesion.get(Trabajador, id_trabajador)
    if trabajador is None:
        raise ValueError(f"No existe trabajador con Id {id_trabajador}")

    # Jornadas no pagadas = las que tienen Id_Pago_Trabajador en None
    pendientes = (
        sesion.query(Registro_Trabajador)
        .filter_by(Id_Trabajador=id_trabajador, Id_Pago_Trabajador=None)
        .all()
    )

    total_horas = sum(j.Horas_Registro_Trabajador for j in pendientes)
    sugerido = total_horas * tarifa_hora(trabajador)

    return sugerido, pendientes


def listar_trabajadores_con_deuda(sesion):
    """
    Trabajadores (habilitados o no) que tienen jornadas sin pagar, con el monto
    sugerido y cuántas jornadas pendientes. Pensado para el desplegable de
    Pagos (item 12): no tiene sentido elegir a alguien a quien no se le debe
    nada, y los deshabilitados con deuda deben poder verse igual para cerrar
    su cuenta pendiente (ver mejora 6.5 en DECISIONES_DISENO).
    """
    pendientes = (
        sesion.query(Registro_Trabajador)
        .filter(Registro_Trabajador.Id_Pago_Trabajador.is_(None))
        .all()
    )
    por_trabajador = {}
    for jornada in pendientes:
        por_trabajador.setdefault(jornada.Id_Trabajador, []).append(jornada)

    resultado = []
    for id_trabajador, jornadas in por_trabajador.items():
        trabajador = sesion.get(Trabajador, id_trabajador)
        total_horas = sum(j.Horas_Registro_Trabajador for j in jornadas)
        sugerido = total_horas * tarifa_hora(trabajador)
        resultado.append({
            "id_trabajador": id_trabajador,
            "nombre": trabajador.Nombre_Trabajador,
            "habilitado": trabajador.Habilitado_Trabajador,
            "jornadas_pendientes": len(jornadas),
            "monto_sugerido": sugerido,
        })
    return resultado


def registrar_pago_semanal(sesion, id_trabajador, id_cuenta, monto_real, fecha=None):
    """
    Registra el pago semanal a un trabajador.

    Parametros:
        sesion: la sesion de SQLAlchemy
        id_trabajador: a quien se paga
        id_cuenta: de que cuenta sale el dinero
        monto_real: cuanto se paga realmente (lo decides tu, puede diferir del sugerido)
        fecha: fecha del pago

    Devuelve: el objeto Pago_Trabajador creado.
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES y calculo del sugerido -----

    sugerido, pendientes = calcular_pago_sugerido(sesion, id_trabajador)

    if len(pendientes) == 0:
        raise ValueError("Este trabajador no tiene jornadas pendientes de pago")

    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")

    if monto_real <= 0:
        raise ValueError("El monto real a pagar debe ser mayor a cero")

    if cuenta.Saldo_Actual_Cuenta < monto_real:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el pago es de {monto_real} Bs"
        )

    # ----- 2. EJECUTAR (todo o nada) -----

    try:
        trabajador = sesion.get(Trabajador, id_trabajador)

        # 2a. Movimiento de dinero (SALIDA)
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,
            Monto_Movimiento=monto_real,
            Descripcion_Movimiento=f"Pago semanal a {trabajador.Nombre_Trabajador}",
        )
        sesion.add(movimiento)
        sesion.flush()

        # 2b. Descontar de la cuenta
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto_real

        # 2c. Crear el registro de pago (sugerido y real)
        pago = Pago_Trabajador(
            Id_Trabajador=id_trabajador,
            Fecha_Pago_Trabajador=fecha,
            Monto_Sugerido_Pago=sugerido,
            Monto_Real_Pago=monto_real,
            Id_Movimiento=movimiento.Id_Movimiento,
        )
        sesion.add(pago)
        sesion.flush()   # para obtener el Id_Pago_Trabajador

        # 2d. Marcar todas las jornadas pendientes como pagadas
        for jornada in pendientes:
            jornada.Id_Pago_Trabajador = pago.Id_Pago_Trabajador

        # 2e. Confirmar todo junto
        sesion.commit()

        return pago

    except Exception as e:
        sesion.rollback()
        raise e