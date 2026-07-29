"""
gastos_lote.py
Registrar VARIOS gastos de una sola vez, como tabla (misma idea que
compras_lote.py, pero para gastos y con el orden de prioridad INVERTIDO por
defecto: se gasta primero CASA, y cuando ya no alcanza, FABRICA — igual que
ya definia PRIORIDAD_CUENTAS["FAMILIAR"]).

Reemplaza el flujo anterior de "Gasto por prioridad" (proponer un reparto y
ajustar a mano cuanto sale de cada cuenta, un gasto a la vez) por una tabla:
cada linea es un gasto independiente. El tipo se puede cambiar a "FABRICA"
(Fabrica->Casa) si la tabla es de gastos de fabrica.

Bloque C: la cuenta de mayor prioridad se DRENA hasta cero, asi que la linea
que cruza el limite se parte y genera DOS movimientos SALIDA (uno por cuenta).
La descripcion, el grupo y la fecha de los dos son IDENTICOS a los de la linea
original: la particion es una mecanica de pago, no dos gastos distintos, y de
esta forma todos los reportes que agrupan por descripcion o por grupo (el
desglose del balance de 10.26, el Dashboard 10 de Power BI) siguen sumando
exactamente lo mismo que antes. Lo que distingue las dos filas es su cuenta de
origen.

Bloque D: una linea puede venir marcada como PAGADA POR OTRA PERSONA (item
10.23, que hasta ahora solo existia en el formulario de un gasto suelto). Esa
linea NO sale de ninguna cuenta propia: se registra como el par
INGRESO_EXTERNO + SALIDA del mismo monto (saldo neto cero), asi que:

  * queda FUERA del reparto por prioridad. Es la parte que importa: si entrara,
    "gastaria" saldo propio que en realidad nunca salio, y empujaria a las
    lineas siguientes a la segunda cuenta antes de tiempo.
  * la cuenta que se usa para el par es la de mayor prioridad del tipo, sin
    preguntar nada: como el neto es cero, cual sea no cambia ningun saldo, y
    pedirle al usuario que elija una cuenta para plata que no es suya seria
    ruido.
"""

from app.config import PRIORIDAD_CUENTAS
from app.servicios.gastos import _aplicar_gasto, _aplicar_gasto_externo
from app.servicios.reparto import cuenta_unica_de_rol, asignar_cuentas_por_linea


def _es_externa(linea):
    return bool(linea.get("pagado_externo"))


def _asignar(sesion, lineas, tipo):
    """
    Decide de que cuenta(s) sale cada linea. Devuelve `asignaciones` paralelo a
    `lineas`, donde cada elemento es una lista de tramos:
      - linea propia:  [{"rol": "CASA", "monto": ...}, ...]  (1 o 2 tramos)
      - linea externa: [{"rol": "EXTERNO", "monto": ..., "quien": "Juan"}]

    Las externas se apartan ANTES de repartir y se reinsertan en su posicion
    original, para que el drenaje por prioridad solo vea plata propia.
    """
    if tipo not in PRIORIDAD_CUENTAS:
        raise ValueError(f"Tipo de gasto inválido: {tipo}")
    rol_primero, rol_segundo = PRIORIDAD_CUENTAS[tipo][0], PRIORIDAD_CUENTAS[tipo][1]

    cuenta_fabrica = cuenta_unica_de_rol(sesion, "FABRICA")
    cuenta_casa = cuenta_unica_de_rol(sesion, "CASA")
    saldos = {"FABRICA": cuenta_fabrica.Saldo_Actual_Cuenta, "CASA": cuenta_casa.Saldo_Actual_Cuenta}
    cuentas = {"FABRICA": cuenta_fabrica, "CASA": cuenta_casa}

    # Validar acá lo que el reparto no puede ver: una externa sin quién pagó.
    for linea in lineas:
        if _es_externa(linea) and not (linea.get("quien_pago") or "").strip():
            raise ValueError(
                f"Indicá quién pagó el gasto «{linea['descripcion']}» "
                "(está marcado como pagado por otra persona)"
            )

    indices_propias = [i for i, l in enumerate(lineas) if not _es_externa(l)]
    propias = [lineas[i] for i in indices_propias]

    tramos_propias, total_primero, total_segundo = asignar_cuentas_por_linea(
        propias, rol_primero, saldos[rol_primero], rol_segundo, saldos[rol_segundo],
    )

    asignaciones = [None] * len(lineas)
    for pos, i in enumerate(indices_propias):
        asignaciones[i] = tramos_propias[pos]
    for i, linea in enumerate(lineas):
        if asignaciones[i] is None:
            asignaciones[i] = [{
                "rol": "EXTERNO",
                "monto": linea["monto"],
                "quien": linea["quien_pago"].strip(),
            }]

    totales = {rol_primero: total_primero, rol_segundo: total_segundo}
    total_externo = sum(
        (l["monto"] for l in lineas if _es_externa(l)),
        saldos["CASA"] - saldos["CASA"],   # cero del mismo tipo que los montos
    )
    return cuentas, saldos, totales, asignaciones, total_externo, rol_primero


def previsualizar_gastos_lote(sesion, lineas, tipo="FAMILIAR"):
    """Calcula, SIN registrar nada, de que cuenta saldria cada linea."""
    if not lineas:
        raise ValueError("Agrega al menos una línea")
    cuentas, saldos, totales, asignaciones, total_externo, _ = _asignar(sesion, lineas, tipo)
    return {
        "asignaciones": asignaciones,
        "total_fabrica": totales["FABRICA"],
        "total_casa": totales["CASA"],
        "total_externo": total_externo,
        "saldo_fabrica": saldos["FABRICA"],
        "saldo_casa": saldos["CASA"],
    }


def registrar_gastos_lote(sesion, lineas, tipo="FAMILIAR", fecha=None):
    """
    Registra N gastos en una sola transaccion atomica (todo o nada), drenando
    primero la cuenta de mayor prioridad del tipo elegido (Casa para FAMILIAR,
    Fabrica para FABRICA) y luego la otra.

    Una linea que se paga entre las dos cuentas genera un Movimiento SALIDA por
    tramo, con la misma descripcion y grupo. Una linea pagada por otra persona
    genera el par INGRESO_EXTERNO + SALIDA y no toca ningun saldo (ver la nota
    del encabezado).

    lineas: [{monto, descripcion, id_grupo, pagado_externo?, quien_pago?}]
    """
    if not lineas:
        raise ValueError("Agrega al menos una línea")

    cuentas, saldos, totales, asignaciones, total_externo, rol_primero = _asignar(
        sesion, lineas, tipo
    )

    try:
        resultado = []
        for linea, tramos in zip(lineas, asignaciones):
            movimientos = []
            for tramo in tramos:
                if tramo["rol"] == "EXTERNO":
                    # La cuenta es indistinta (el par entra y sale por el mismo
                    # monto): se usa la de mayor prioridad del tipo.
                    movimiento = _aplicar_gasto_externo(
                        sesion,
                        id_cuenta=cuentas[rol_primero].Id_Cuenta,
                        monto=tramo["monto"],
                        descripcion=linea["descripcion"],
                        quien_pago=tramo["quien"],
                        id_grupo=linea.get("id_grupo"),
                        fecha=fecha,
                    )
                else:
                    movimiento = _aplicar_gasto(
                        sesion,
                        id_cuenta=cuentas[tramo["rol"]].Id_Cuenta,
                        monto=tramo["monto"],
                        descripcion=linea["descripcion"],
                        id_grupo=linea.get("id_grupo"),
                        fecha=fecha,
                    )
                movimientos.append({
                    "movimiento_obj": movimiento,
                    "cuenta": tramo["rol"],
                    "monto": tramo["monto"],
                    "quien": tramo.get("quien"),
                })
            resultado.append({
                "tramos": movimientos,
                "partida": len(tramos) > 1,
                "externa": _es_externa(linea),
            })

        sesion.flush()   # asigna los Id_Movimiento de todos los tramos
        for r in resultado:
            for t in r["tramos"]:
                t["id_movimiento"] = t.pop("movimiento_obj").Id_Movimiento

        sesion.commit()
        return {
            "lineas": resultado,
            "total_fabrica": totales["FABRICA"],
            "total_casa": totales["CASA"],
            "total_externo": total_externo,
        }
    except Exception as e:
        sesion.rollback()
        raise e
