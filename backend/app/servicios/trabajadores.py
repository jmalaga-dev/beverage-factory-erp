"""
trabajadores.py
Logica de negocio para registrar jornadas de trabajo.
Registrar una jornada solo guarda las horas trabajadas; NO mueve dinero
(el pago a los trabajadores es semanal y se hace en una operacion aparte).
"""

from app.models import Registro_Trabajador, Trabajador


def registrar_jornada(sesion, id_trabajador, horas, fecha=None):
    """
    Registra una jornada de trabajo de un trabajador.

    Parametros:
        sesion: la sesion de SQLAlchemy
        id_trabajador: quien trabajo
        horas: cuantas horas trabajo ese dia
        fecha: fecha de la jornada

    Devuelve: el objeto Registro_Trabajador creado.
    Lanza ValueError si algo no es valido.
    """

    # ----- 1. VALIDACIONES -----

    # El trabajador debe existir
    trabajador = sesion.get(Trabajador, id_trabajador)
    if trabajador is None:
        raise ValueError(f"No existe trabajador con Id {id_trabajador}")

    # Las horas deben ser positivas y razonables
    if horas <= 0:
        raise ValueError("Las horas deben ser mayores a cero")
    if horas > 24:
        raise ValueError("Las horas de una jornada no pueden superar 24")

    # ----- 2. EJECUTAR -----

    try:
        jornada = Registro_Trabajador(
            Id_Trabajador=id_trabajador,
            Fecha_Registro_Trabajador=fecha,
            Horas_Registro_Trabajador=horas,
            Horas_Restante_Registro_Trabajador=horas,  # al registrar, todas las horas estan disponibles
            Id_Movimiento=None,                          # no hay pago aun
        )
        sesion.add(jornada)
        sesion.commit()
        return jornada

    except Exception as e:
        sesion.rollback()
        raise e