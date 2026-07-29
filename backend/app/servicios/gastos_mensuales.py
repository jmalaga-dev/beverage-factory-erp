"""
gastos_mensuales.py
Monto real de cada gasto extra en un mes concreto y su pago (mejora 1.1).

Gasto_Extra guarda el gasto recurrente (luz, agua...) y su monto tipico.
Gasto_Extra_Mes guarda el MONTO REAL de un mes y su pago (SALIDA de una cuenta).
El prorrateo del mes usa estos montos y exige que todos esten pagados.
"""

from app.models import Gasto_Extra, Gasto_Extra_Mes, Cuenta, Movimiento
from app.servicios.prorrateo import _ya_prorrateado


def registrar_monto_mes(sesion, id_gasto_extra, anio_mes, monto):
    """Fija (o actualiza) el monto de un gasto recurrente en un mes concreto.
    No se puede cambiar si ese gasto del mes ya fue pagado."""
    gasto = sesion.get(Gasto_Extra, id_gasto_extra)
    if gasto is None:
        raise ValueError(f"No existe gasto extra con Id {id_gasto_extra}")
    if monto is None or monto <= 0:
        raise ValueError("El monto debe ser mayor a cero")

    fila = (
        sesion.query(Gasto_Extra_Mes)
        .filter_by(Id_Gasto_Extra=id_gasto_extra, Anio_Mes=anio_mes)
        .first()
    )
    try:
        if fila is None:
            fila = Gasto_Extra_Mes(
                Id_Gasto_Extra=id_gasto_extra, Anio_Mes=anio_mes,
                Monto_Gasto_Extra_Mes=monto,
            )
            sesion.add(fila)
        else:
            if fila.Fecha_Pago_Gasto_Extra_Mes is not None:
                raise ValueError("Ese gasto del mes ya está pagado; no se puede cambiar el monto")
            fila.Monto_Gasto_Extra_Mes = monto
        sesion.commit()
        return fila
    except Exception as e:
        sesion.rollback()
        raise e


def pagar_monto_mes(sesion, id_gasto_extra_mes, id_cuenta, fecha=None):
    """Paga el gasto del mes: SALIDA de la cuenta + marca pagado (fecha, cuenta
    y el Movimiento). Atomico."""
    fila = sesion.get(Gasto_Extra_Mes, id_gasto_extra_mes)
    if fila is None:
        raise ValueError(f"No existe gasto del mes con Id {id_gasto_extra_mes}")
    if fila.Fecha_Pago_Gasto_Extra_Mes is not None:
        raise ValueError("Ese gasto del mes ya estaba pagado")
    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")
    monto = fila.Monto_Gasto_Extra_Mes
    if cuenta.Saldo_Actual_Cuenta < monto:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el gasto es de {monto} Bs"
        )
    gasto = sesion.get(Gasto_Extra, fila.Id_Gasto_Extra)
    try:
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=f"Gasto {gasto.Descripcion_Gasto_Extra} {fila.Anio_Mes}",
        )
        sesion.add(movimiento)
        sesion.flush()
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto
        fila.Fecha_Pago_Gasto_Extra_Mes = fecha
        fila.Id_Cuenta_Pago = id_cuenta
        fila.Id_Movimiento = movimiento.Id_Movimiento
        sesion.commit()
        return fila
    except Exception as e:
        sesion.rollback()
        raise e


def anular_pago_mes(sesion, id_gasto_extra_mes, fecha=None):
    """Anula el pago de un gasto del mes con un movimiento INVERSO (bloque B).

    Caso real: se pago 10 Bs de telefono y eran 20 (o eran 5 y sobran 5). Como
    registrar_monto_mes no deja tocar el monto de un gasto ya pagado, hacia
    falta poder deshacer el pago primero.

    NO borra el movimiento original (inmutabilidad del libro): crea una
    ANULACION_SALIDA que devuelve el dinero a la misma cuenta de la que salio,
    enlazada al pago por Id_Movimiento_Anulado, y deja la fila del mes como no
    pagada -- lista para corregir el monto y volver a pagarla. Atomico.

    No valida saldo: a diferencia de anular un ingreso (donde el dinero puede
    haberse gastado ya), aca se esta DEVOLVIENDO plata a la cuenta, y eso
    siempre se puede.
    """
    fila = sesion.get(Gasto_Extra_Mes, id_gasto_extra_mes)
    if fila is None:
        raise ValueError(f"No existe gasto del mes con Id {id_gasto_extra_mes}")
    if fila.Fecha_Pago_Gasto_Extra_Mes is None:
        raise ValueError("Ese gasto del mes no está pagado, no hay pago que anular")

    # El prorrateo del mes es una foto congelada calculada con ESTE monto: si ya
    # se corrio, cambiar el pago dejaria el reparto mintiendo. Primero habria que
    # poder anular el prorrateo (pendiente, no existe todavia).
    if _ya_prorrateado(sesion, fila.Anio_Mes):
        raise ValueError(
            f"El mes {fila.Anio_Mes} ya fue prorrateado: el reparto entre productos "
            "se calculó con este monto. No se puede anular el pago sin deshacer antes "
            "el prorrateo."
        )

    # Los pagos que vinieron de la migracion del excel quedaron marcados como
    # pagados SIN generar movimiento de caja (ver 10.25): esa plata salio hace
    # años y el saldo actual ya la tiene descontada. Crear el inverso ahora
    # inventaria un ingreso que nunca existio.
    if fila.Id_Movimiento is None:
        raise ValueError(
            "Ese pago no tiene movimiento de caja asociado (viene de la migración "
            "del Excel): no se puede anular desde la app."
        )

    mov = sesion.get(Movimiento, fila.Id_Movimiento)
    if mov is None:
        raise ValueError(f"No existe el movimiento del pago (Id {fila.Id_Movimiento})")

    ya_anulado = sesion.query(Movimiento).filter(
        Movimiento.Tipo_Movimiento == "ANULACION_SALIDA",
        Movimiento.Id_Movimiento_Anulado == mov.Id_Movimiento,
    ).first()
    if ya_anulado is not None:
        raise ValueError("Ese pago ya fue anulado")

    cuenta = sesion.get(Cuenta, mov.Id_Cuenta_Origen)
    if cuenta is None:
        raise ValueError(f"No existe la cuenta del pago (Id {mov.Id_Cuenta_Origen})")

    gasto = sesion.get(Gasto_Extra, fila.Id_Gasto_Extra)
    nombre = gasto.Descripcion_Gasto_Extra if gasto else "?"

    try:
        anulacion = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="ANULACION_SALIDA",
            Id_Cuenta_Origen=None,
            Id_Cuenta_Destino=cuenta.Id_Cuenta,   # el dinero vuelve a la cuenta
            Monto_Movimiento=mov.Monto_Movimiento,
            Descripcion_Movimiento=(
                f"Anulación de pago #{mov.Id_Movimiento}: {nombre} {fila.Anio_Mes}"
            ),
            Id_Movimiento_Anulado=mov.Id_Movimiento,
        )
        sesion.add(anulacion)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta + mov.Monto_Movimiento

        # La fila vuelve a "cargada pero sin pagar": el monto se conserva (es lo
        # que se va a corregir) y se sueltan las tres marcas del pago.
        fila.Fecha_Pago_Gasto_Extra_Mes = None
        fila.Id_Cuenta_Pago = None
        fila.Id_Movimiento = None

        sesion.commit()
        return anulacion
    except Exception as e:
        sesion.rollback()
        raise e


def estado_mes(sesion, anio_mes):
    """Los gastos registrados del mes con su estado de pago, y si están todos
    pagados (condición para poder prorratear)."""
    filas = sesion.query(Gasto_Extra_Mes).filter_by(Anio_Mes=anio_mes).all()
    detalle = []
    total = 0.0
    pagados = 0
    for f in filas:
        gasto = sesion.get(Gasto_Extra, f.Id_Gasto_Extra)
        cuenta = sesion.get(Cuenta, f.Id_Cuenta_Pago) if f.Id_Cuenta_Pago else None
        pagado = f.Fecha_Pago_Gasto_Extra_Mes is not None
        if pagado:
            pagados += 1
        total += float(f.Monto_Gasto_Extra_Mes)
        detalle.append({
            "id_gasto_extra_mes": f.Id_Gasto_Extra_Mes,
            "id_gasto_extra": f.Id_Gasto_Extra,
            "descripcion": gasto.Descripcion_Gasto_Extra if gasto else "?",
            "monto": float(f.Monto_Gasto_Extra_Mes),
            "pagado": pagado,
            "fecha_pago": str(f.Fecha_Pago_Gasto_Extra_Mes) if pagado else None,
            "cuenta_pago": cuenta.Nombre_Cuenta if cuenta else None,
        })
    return {
        "anio_mes": anio_mes,
        "total": round(total, 2),
        "cantidad": len(filas),
        "pagados": pagados,
        "todos_pagados": len(filas) > 0 and pagados == len(filas),
        "detalle": detalle,
    }
