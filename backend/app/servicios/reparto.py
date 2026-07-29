"""
reparto.py
Helpers compartidos para repartir gastos y compras entre la cuenta FABRICA y
la cuenta CASA por prioridad, usados por las "tablas" de compras y de gastos
(compras_lote.py y gastos_lote.py).

Regla del negocio (bloque C): se DRENA la cuenta de mayor prioridad hasta
dejarla en cero antes de tocar la otra. Si una linea no entra completa en lo
que queda, esa linea se PARTE: una parte sale de la primera cuenta (justo lo
que quedaba) y el resto de la segunda.

Antes se asignaba cada linea ENTERA a una sola cuenta, y apenas una linea no
entraba se pasaban esa y TODAS las siguientes a la segunda cuenta, sin volver
a mirar la primera. Eso dejaba plata muerta en la primera billetera: con
saldos Casa 150 / Fabrica 500 y gastos de 50, 60, 70, 45 y 15, Casa se quedaba
con 40 Bs sin usar y los ultimos dos gastos (que si entraban) se iban a
Fabrica. En la practica se gasta una billetera hasta terminarla y recien ahi
se saca de la otra, aunque un mismo item quede pagado a medias entre las dos.
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
    decide de que cuenta(s) sale cada una, DRENANDO primero rol_primero.

    Devuelve (asignaciones, total_primero, total_segundo), donde `asignaciones`
    es una lista paralela a `lineas` y cada elemento es una lista de TRAMOS:
        [{"rol": "CASA", "monto": Decimal("40")},
         {"rol": "FABRICA", "monto": Decimal("30")}]
    Una linea que sale entera de una sola cuenta tiene un unico tramo; una
    linea partida tiene dos. Nunca se emite un tramo de monto cero.

    Los montos de los tramos suman EXACTO el monto de su linea (se reparte por
    diferencia, sin redondeos intermedios), asi que no hay centavos perdidos.

    Lanza ValueError si ni juntando ambas cuentas alcanza.
    """
    asignaciones = []
    disponible_primero = saldo_primero

    for linea in lineas:
        pendiente = linea["monto"]
        tramos = []

        # Lo que quede en la primera cuenta se usa hasta agotarlo.
        if disponible_primero > 0 and pendiente > 0:
            usar = min(pendiente, disponible_primero)
            tramos.append({"rol": rol_primero, "monto": usar})
            disponible_primero -= usar
            pendiente -= usar

        # El resto (si quedo algo) va a la segunda cuenta.
        if pendiente > 0:
            tramos.append({"rol": rol_segundo, "monto": pendiente})

        asignaciones.append(tramos)

    total_primero = saldo_primero - disponible_primero
    # Suma acumulada a mano (y no sum(), que necesitaria un cero del mismo tipo
    # para no mezclar int con Decimal en el primer termino).
    total_segundo = saldo_segundo - saldo_segundo   # cero del mismo tipo que los montos
    for tramos in asignaciones:
        for t in tramos:
            if t["rol"] == rol_segundo:
                total_segundo += t["monto"]

    if total_segundo > saldo_segundo:
        faltante = total_segundo - saldo_segundo
        raise ValueError(
            f"Saldo insuficiente entre ambas cuentas: faltan {faltante} Bs "
            f"({rol_primero} cubre {total_primero} Bs; {rol_segundo} necesitaría "
            f"{total_segundo} Bs pero solo tiene {saldo_segundo} Bs)."
        )

    return asignaciones, total_primero, total_segundo
