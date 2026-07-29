"""
compras_lote.py
Registrar VARIAS compras de materia prima de una sola vez, como tabla
(mejora: tabla de compras + gasto por prioridad Fabrica->Casa).

A diferencia de compra_dividida.py (que reparte UN precio entre varias
materias primas), aca cada linea ya trae su propio precio; lo que se reparte
es DE QUE CUENTA sale cada linea. Si ni juntando ambas cuentas alcanza, no se
registra nada (todo o nada).

Bloque C: la cuenta FABRICA se DRENA hasta cero antes de tocar CASA. Cuando
una linea no entra completa en lo que queda, se parte.

**Partir una compra parte el LOTE, no solo el pago.** Una fila de Compra es un
lote de inventario y enlaza UN solo Id_Movimiento, asi que no puede pagarse
desde dos cuentas. La linea partida se registra entonces como DOS compras del
mismo insumo, mismo proveedor y misma fecha, cada una pagada entera por su
cuenta, repartiendo la cantidad en la misma proporcion que el precio. El
precio unitario resultante es identico en las dos (y al de la linea original),
asi que el costeo, el stock consolidado y el FIFO no cambian: lo unico que
cambia es que el historial de compras muestra dos filas en vez de una. Es el
mismo mecanismo que ya usa la compra dividida por pliego (3.8), que tambien
registra N Compra en una sola transaccion.

La logica de "que cuenta(s) le tocan a cada linea" es generica (ver reparto.py,
compartida con gastos_lote.py, que usa el orden inverso: Casa->Fabrica).
"""

from decimal import Decimal

from app.servicios.compras import _aplicar_compra
from app.servicios.reparto import cuenta_unica_de_rol, asignar_cuentas_por_linea

# Decimales con los que se parte la cantidad de un lote. 6 es la misma
# precision con la que FIFO reparte cantidades entre lotes.
DECIMALES_CANTIDAD = Decimal("0.000001")


def _asignar(sesion, lineas):
    """Resuelve las cuentas Fabrica/Casa y decide de cual(es) sale cada linea
    de compra (drena Fabrica primero, Casa despues)."""
    cuenta_fabrica = cuenta_unica_de_rol(sesion, "FABRICA")
    cuenta_casa = cuenta_unica_de_rol(sesion, "CASA")
    lineas_monto = [{"monto": l["precio_total"]} for l in lineas]
    asignaciones, total_fabrica, total_casa = asignar_cuentas_por_linea(
        lineas_monto, "FABRICA", cuenta_fabrica.Saldo_Actual_Cuenta,
        "CASA", cuenta_casa.Saldo_Actual_Cuenta,
    )
    return cuenta_fabrica, cuenta_casa, asignaciones, total_fabrica, total_casa


def _repartir_cantidad(cantidad, precio_total, tramos):
    """
    Reparte la cantidad del lote entre los tramos, en la misma proporcion que
    el precio. El ULTIMO tramo absorbe el redondeo, para que la suma de las
    cantidades sea exactamente la cantidad original (mismo criterio que la
    compra dividida 3.8 y el prorrateo: nada de restos sueltos).
    """
    if len(tramos) == 1:
        return [cantidad]

    cantidades = []
    asignado = Decimal(0)
    for idx, tramo in enumerate(tramos):
        if idx == len(tramos) - 1:
            parte = cantidad - asignado
        else:
            parte = (cantidad * tramo["monto"] / precio_total).quantize(DECIMALES_CANTIDAD)
            asignado += parte
        if parte <= 0:
            raise ValueError(
                f"No se puede partir la compra entre dos cuentas: la cantidad "
                f"({cantidad}) es demasiado chica para repartirla. Cargá esa línea "
                f"por separado eligiendo la cuenta a mano."
            )
        cantidades.append(parte)
    return cantidades


def previsualizar_compras_lote(sesion, lineas):
    """Calcula, SIN registrar nada, de que cuenta saldria cada linea. Sirve
    para mostrar la suma en vivo en el frontend antes de confirmar."""
    if not lineas:
        raise ValueError("Agrega al menos una línea")
    cuenta_fabrica, cuenta_casa, asignaciones, total_fabrica, total_casa = _asignar(sesion, lineas)
    return {
        "asignaciones": asignaciones,
        "total_fabrica": total_fabrica,
        "total_casa": total_casa,
        "saldo_fabrica": cuenta_fabrica.Saldo_Actual_Cuenta,
        "saldo_casa": cuenta_casa.Saldo_Actual_Cuenta,
    }


def registrar_compras_lote(sesion, lineas, fecha=None):
    """
    Registra las compras en una sola transaccion atomica (todo o nada),
    drenando primero la cuenta FABRICA y luego CASA. Una linea que se paga
    entre las dos cuentas genera DOS Compra (ver la nota del encabezado).

    lineas: [{id_materia_prima, cantidad, precio_total, id_proveedor}]
    Cada compra se registra de contado y recibida (sin credito ni pedido
    pendiente; para esos casos se sigue usando el formulario simple).
    """
    if not lineas:
        raise ValueError("Agrega al menos una línea")

    cuenta_fabrica, cuenta_casa, asignaciones, total_fabrica, total_casa = _asignar(sesion, lineas)
    cuentas = {"FABRICA": cuenta_fabrica, "CASA": cuenta_casa}

    try:
        resultado = []
        for linea, tramos in zip(lineas, asignaciones):
            cantidades = _repartir_cantidad(linea["cantidad"], linea["precio_total"], tramos)
            compras = []
            for tramo, cantidad in zip(tramos, cantidades):
                compra = _aplicar_compra(
                    sesion,
                    id_materia_prima=linea["id_materia_prima"],
                    id_cuenta=cuentas[tramo["rol"]].Id_Cuenta,
                    cantidad=cantidad,
                    precio_total=tramo["monto"],
                    fecha=fecha,
                    id_proveedor=linea["id_proveedor"],
                    monto_pagado=None,
                    recibida=True,
                )
                compras.append({"compra_obj": compra, "cuenta": tramo["rol"],
                                "monto": tramo["monto"], "cantidad": cantidad})
            resultado.append({"tramos": compras, "partida": len(tramos) > 1})

        sesion.flush()   # asigna los Id_Compra de todos los tramos
        for r in resultado:
            for t in r["tramos"]:
                t["id_compra"] = t.pop("compra_obj").Id_Compra

        sesion.commit()
        return {
            "lineas": resultado,
            "total_fabrica": total_fabrica,
            "total_casa": total_casa,
        }
    except Exception as e:
        sesion.rollback()
        raise e
