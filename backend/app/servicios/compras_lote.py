"""
compras_lote.py
Registrar VARIAS compras de materia prima de una sola vez, como tabla
(mejora: tabla de compras + gasto por prioridad Fabrica->Casa).

A diferencia de compra_dividida.py (que reparte UN precio entre varias
materias primas), aca cada linea ya trae su propio precio; lo que se reparte
es DE QUE CUENTA sale cada linea: se gasta la cuenta FABRICA linea por linea,
en el orden en que se cargaron, hasta que ya no alcanza para cubrir la
siguiente linea COMPLETA; de ahi en adelante (esa linea incluida) todo sale
de la cuenta CASA. No se parte una misma compra entre las dos cuentas.
Si ni juntando ambas cuentas alcanza, no se registra nada (todo o nada).

La logica de "que cuenta le toca a cada linea" es generica (ver reparto.py,
compartida con gastos_lote.py, que usa el orden inverso: Casa->Fabrica).
"""

from app.servicios.compras import _aplicar_compra
from app.servicios.reparto import cuenta_unica_de_rol, asignar_cuentas_por_linea


def _asignar(sesion, lineas):
    """Resuelve las cuentas Fabrica/Casa y decide de cual sale cada linea de
    compra (Fabrica primero, Casa despues)."""
    cuenta_fabrica = cuenta_unica_de_rol(sesion, "FABRICA")
    cuenta_casa = cuenta_unica_de_rol(sesion, "CASA")
    lineas_monto = [{"monto": l["precio_total"]} for l in lineas]
    asignaciones, total_fabrica, total_casa = asignar_cuentas_por_linea(
        lineas_monto, "FABRICA", cuenta_fabrica.Saldo_Actual_Cuenta,
        "CASA", cuenta_casa.Saldo_Actual_Cuenta,
    )
    return cuenta_fabrica, cuenta_casa, asignaciones, total_fabrica, total_casa


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
    Registra N compras (una Compra normal por linea) en una sola transaccion
    atomica (todo o nada), pagando primero desde la cuenta FABRICA y luego
    desde CASA.

    lineas: [{id_materia_prima, cantidad, precio_total, id_proveedor}]
    Cada compra se registra de contado y recibida (sin credito ni pedido
    pendiente; para esos casos se sigue usando el formulario simple).
    """
    if not lineas:
        raise ValueError("Agrega al menos una línea")

    cuenta_fabrica, cuenta_casa, asignaciones, total_fabrica, total_casa = _asignar(sesion, lineas)

    try:
        resultado = []
        for linea, rol in zip(lineas, asignaciones):
            id_cuenta = (
                cuenta_fabrica.Id_Cuenta if rol == "FABRICA" else cuenta_casa.Id_Cuenta
            )
            compra = _aplicar_compra(
                sesion,
                id_materia_prima=linea["id_materia_prima"],
                id_cuenta=id_cuenta,
                cantidad=linea["cantidad"],
                precio_total=linea["precio_total"],
                fecha=fecha,
                id_proveedor=linea["id_proveedor"],
                monto_pagado=None,
                recibida=True,
            )
            resultado.append({"compra_obj": compra, "cuenta": rol})

        sesion.flush()   # asigna los Id_Compra de todas las lineas
        for r in resultado:
            r["id_compra"] = r.pop("compra_obj").Id_Compra

        sesion.commit()
        return {
            "lineas": resultado,
            "total_fabrica": total_fabrica,
            "total_casa": total_casa,
        }
    except Exception as e:
        sesion.rollback()
        raise e
