"""
gastos_mensuales.py
Monto real de cada gasto extra en un mes concreto y su pago (mejora 1.1).

Gasto_Extra guarda el gasto recurrente (luz, agua...) y su monto tipico.
Gasto_Extra_Mes guarda el MONTO REAL de un mes y su pago (SALIDA de una cuenta).
El prorrateo del mes usa estos montos y exige que todos esten pagados.
"""

from app.models import Gasto_Extra, Gasto_Extra_Mes, Cuenta, Movimiento


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
