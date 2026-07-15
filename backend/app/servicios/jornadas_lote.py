"""
jornadas_lote.py
Registrar VARIAS jornadas de un mismo dia de una sola vez, como tabla (mismo
patron que compras_lote.py / gastos_lote.py: se compone todo en una sola
transaccion con _aplicar_jornada, sin commit, y se hace un unico commit al
final -- todo o nada).

Pensado para el pase de lista diario: una fila por trabajador habilitado, con
sus horas de ese dia. Una fila en 0 o vacia significa que esa persona no vino
ese dia, y simplemente se omite (no es un error).
"""

from app.servicios.trabajadores import _aplicar_jornada


def registrar_jornadas_lote(sesion, lineas, fecha=None):
    """
    Registra una jornada por cada linea con horas > 0 (las de horas 0/None se
    omiten: significan que esa persona no trabajo ese dia). Atomico: si
    cualquier linea con horas > 0 falla su validacion, no se registra ninguna.

    lineas: [{id_trabajador, horas}]
    Devuelve: lista de [{id_trabajador, id_jornada, horas}] creadas (una por
    trabajador con horas > 0).
    Lanza ValueError si ninguna linea tiene horas > 0, o si alguna es invalida.
    """
    con_horas = [l for l in lineas if l.get("horas") and l["horas"] > 0]
    if not con_horas:
        raise ValueError("Ningún trabajador tiene horas cargadas")

    try:
        jornadas = [
            _aplicar_jornada(sesion, id_trabajador=l["id_trabajador"], horas=l["horas"], fecha=fecha)
            for l in con_horas
        ]
        sesion.flush()   # asigna los Id_Registro_Trabajador de todas las lineas
        resultado = [
            {"id_trabajador": j.Id_Trabajador, "id_jornada": j.Id_Registro_Trabajador, "horas": j.Horas_Registro_Trabajador}
            for j in jornadas
        ]
        sesion.commit()
        return resultado
    except Exception as e:
        sesion.rollback()
        raise e
