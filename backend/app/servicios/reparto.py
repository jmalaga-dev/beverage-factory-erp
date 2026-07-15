"""
reparto.py
Helpers compartidos para repartir un gasto entre la cuenta FABRICA y la
cuenta CASA por prioridad, usados por las "tablas" de compras y de gastos
(compras_lote.py y gastos_lote.py): cada linea de la tabla ya trae su propio
monto, y lo que se decide es de que cuenta sale CADA LINEA COMPLETA (no se
parte una misma linea entre las dos cuentas).
"""

from app.models import Cuenta


def cuenta_unica_de_rol(sesion, rol):
    """Exige que exista exactamente una cuenta habilitada con ese rol (mismo
    requisito que ya usa el reparto 70/30 de ventas)."""
    cuentas = (
        sesion.query(Cuenta)
        .filter(Cuenta.Rol_Cuenta == rol, Cuenta.Habilitado_Cuenta.is_(True))
        .all()
    )
    if len(cuentas) != 1:
        raise ValueError(
            f"Debe haber exactamente una cuenta habilitada con rol {rol} "
            f"para repartir el gasto (hay {len(cuentas)}). Revisa Cuentas."
        )
    return cuentas[0]


def asignar_cuentas_por_linea(lineas, rol_primero, saldo_primero, rol_segundo, saldo_segundo):
    """
    Recorre las lineas (cada dict con su propio "monto") en el orden dado y
    decide de que cuenta sale cada una COMPLETA: mientras la suma acumulada
    (incluyendo la linea actual) quepa en saldo_primero, esa linea sale de
    rol_primero; apenas una linea no entra completa, esa y TODAS las que
    siguen salen de rol_segundo (no vuelve a intentar rol_primero despues).

    Devuelve (asignaciones, total_primero, total_segundo): asignaciones es
    una lista paralela a lineas con rol_primero o rol_segundo.
    Lanza ValueError si ni juntando ambas cuentas alcanza.
    """
    asignaciones = []
    acumulado_primero = 0
    en_primero = True
    for linea in lineas:
        monto = linea["monto"]
        if en_primero and acumulado_primero + monto <= saldo_primero:
            asignaciones.append(rol_primero)
            acumulado_primero += monto
        else:
            en_primero = False
            asignaciones.append(rol_segundo)

    total_primero = acumulado_primero
    total_segundo = sum(
        l["monto"] for l, a in zip(lineas, asignaciones) if a == rol_segundo
    )

    if total_segundo > saldo_segundo:
        faltante = total_segundo - saldo_segundo
        raise ValueError(
            f"Saldo insuficiente entre ambas cuentas: faltan {faltante} Bs "
            f"({rol_primero} cubre {total_primero} Bs; {rol_segundo} necesitaría "
            f"{total_segundo} Bs pero solo tiene {saldo_segundo} Bs)."
        )

    return asignaciones, total_primero, total_segundo
