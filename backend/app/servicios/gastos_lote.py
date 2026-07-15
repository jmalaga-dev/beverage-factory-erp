"""
gastos_lote.py
Registrar VARIOS gastos de una sola vez, como tabla (misma idea que
compras_lote.py, pero para gastos y con el orden de prioridad INVERTIDO por
defecto: se gasta primero CASA linea por linea, y cuando ya no alcanza,
FABRICA — igual que ya definia PRIORIDAD_CUENTAS["FAMILIAR"]).

Reemplaza el flujo anterior de "Gasto por prioridad" (proponer un reparto y
ajustar a mano cuanto sale de cada cuenta, un gasto a la vez) por una tabla:
cada linea es un gasto independiente que sale ENTERO de una sola cuenta (no
se parte una misma linea entre las dos cuentas). El tipo se puede cambiar a
"FABRICA" (Fabrica->Casa) si la tabla es de gastos de fabrica.
"""

from app.config import PRIORIDAD_CUENTAS
from app.servicios.gastos import _aplicar_gasto
from app.servicios.reparto import cuenta_unica_de_rol, asignar_cuentas_por_linea


def _asignar(sesion, lineas, tipo):
    if tipo not in PRIORIDAD_CUENTAS:
        raise ValueError(f"Tipo de gasto inválido: {tipo}")
    rol_primero, rol_segundo = PRIORIDAD_CUENTAS[tipo][0], PRIORIDAD_CUENTAS[tipo][1]

    cuenta_fabrica = cuenta_unica_de_rol(sesion, "FABRICA")
    cuenta_casa = cuenta_unica_de_rol(sesion, "CASA")
    saldos = {"FABRICA": cuenta_fabrica.Saldo_Actual_Cuenta, "CASA": cuenta_casa.Saldo_Actual_Cuenta}
    cuentas = {"FABRICA": cuenta_fabrica, "CASA": cuenta_casa}

    asignaciones, total_primero, total_segundo = asignar_cuentas_por_linea(
        lineas, rol_primero, saldos[rol_primero], rol_segundo, saldos[rol_segundo],
    )
    totales = {rol_primero: total_primero, rol_segundo: total_segundo}
    return cuentas, saldos, totales, asignaciones


def previsualizar_gastos_lote(sesion, lineas, tipo="FAMILIAR"):
    """Calcula, SIN registrar nada, de que cuenta saldria cada linea."""
    if not lineas:
        raise ValueError("Agrega al menos una línea")
    cuentas, saldos, totales, asignaciones = _asignar(sesion, lineas, tipo)
    return {
        "asignaciones": asignaciones,
        "total_fabrica": totales["FABRICA"],
        "total_casa": totales["CASA"],
        "saldo_fabrica": saldos["FABRICA"],
        "saldo_casa": saldos["CASA"],
    }


def registrar_gastos_lote(sesion, lineas, tipo="FAMILIAR", fecha=None):
    """
    Registra N gastos (un Movimiento SALIDA por linea) en una sola
    transaccion atomica (todo o nada), pagando primero desde la cuenta de
    mayor prioridad del tipo elegido (Casa para FAMILIAR, Fabrica para
    FABRICA) y luego desde la otra.

    lineas: [{monto, descripcion, id_grupo}]
    """
    if not lineas:
        raise ValueError("Agrega al menos una línea")

    cuentas, saldos, totales, asignaciones = _asignar(sesion, lineas, tipo)

    try:
        resultado = []
        for linea, rol in zip(lineas, asignaciones):
            cuenta = cuentas[rol]
            movimiento = _aplicar_gasto(
                sesion,
                id_cuenta=cuenta.Id_Cuenta,
                monto=linea["monto"],
                descripcion=linea["descripcion"],
                id_grupo=linea.get("id_grupo"),
                fecha=fecha,
            )
            resultado.append({"movimiento_obj": movimiento, "cuenta": rol})

        sesion.flush()   # asigna los Id_Movimiento de todas las lineas
        for r in resultado:
            r["id_movimiento"] = r.pop("movimiento_obj").Id_Movimiento

        sesion.commit()
        return {
            "lineas": resultado,
            "total_fabrica": totales["FABRICA"],
            "total_casa": totales["CASA"],
        }
    except Exception as e:
        sesion.rollback()
        raise e
