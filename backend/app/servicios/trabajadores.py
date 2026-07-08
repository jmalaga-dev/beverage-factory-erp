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


def _validar_jornada_intacta(jornada):
    """
    Una jornada solo se puede corregir o anular si esta intacta: nada de
    sus horas se uso como insumo en una produccion, y no fue pagada. Si
    cualquiera de las dos ya paso, editarla o borrarla dejaria
    inconsistente un costo de produccion o un pago ya registrados.
    """
    if jornada.Id_Pago_Trabajador is not None:
        raise ValueError("No se puede modificar: esta jornada ya fue pagada")
    if jornada.Horas_Restante_Registro_Trabajador != jornada.Horas_Registro_Trabajador:
        raise ValueError("No se puede modificar: parte de sus horas ya se usaron en una producción")


def editar_jornada(sesion, id_jornada, id_trabajador=None, horas=None, fecha=None):
    """
    Corrige una jornada mal registrada (trabajador equivocado, horas
    equivocadas, fecha equivocada). Solo si esta intacta (ver
    _validar_jornada_intacta). Los parametros None no se tocan.
    """
    jornada = sesion.get(Registro_Trabajador, id_jornada)
    if jornada is None:
        raise ValueError(f"No existe jornada con Id {id_jornada}")

    _validar_jornada_intacta(jornada)

    if id_trabajador is not None:
        trabajador = sesion.get(Trabajador, id_trabajador)
        if trabajador is None:
            raise ValueError(f"No existe trabajador con Id {id_trabajador}")
        jornada.Id_Trabajador = id_trabajador

    if horas is not None:
        if horas <= 0:
            raise ValueError("Las horas deben ser mayores a cero")
        if horas > 24:
            raise ValueError("Las horas de una jornada no pueden superar 24")
        jornada.Horas_Registro_Trabajador = horas
        jornada.Horas_Restante_Registro_Trabajador = horas  # sigue intacta: todas siguen disponibles

    if fecha is not None:
        jornada.Fecha_Registro_Trabajador = fecha

    try:
        sesion.commit()
        return jornada
    except Exception as e:
        sesion.rollback()
        raise e


def eliminar_jornada(sesion, id_jornada):
    """
    Anula una jornada mal registrada. Solo si esta intacta (ver
    _validar_jornada_intacta). Al no tener nada que dependa de ella
    (no genera movimiento de dinero), es seguro borrarla de verdad,
    a diferencia del resto del historico que nunca se borra.
    """
    jornada = sesion.get(Registro_Trabajador, id_jornada)
    if jornada is None:
        raise ValueError(f"No existe jornada con Id {id_jornada}")

    _validar_jornada_intacta(jornada)

    try:
        sesion.delete(jornada)
        sesion.commit()
    except Exception as e:
        sesion.rollback()
        raise e