"""
deudas.py
Logica de negocio para deudas (mejoras 7.0 y 7.3).

Tres operaciones, todas atomicas. El saldo de la Deuda se mantiene igual que
el de una Cuenta (campo cacheado que refleja la suma de sus movimientos):
cada operacion registra un Movimiento_Deuda (AUMENTO o PAGO) y ajusta
Saldo_Actual_Deuda.

  1. registrar_deuda_simple: sube el pasivo sin mover caja. Ej: el interes
     que cobra el banco, o un gasto que alguien pago por nosotros.
  2. registrar_prestamo_con_ingreso: sube el pasivo Y entra dinero a una
     cuenta (un solo acto). Ej: el banco presta 100 a Billetera Fabrica. El
     lado de caja usa un Movimiento INGRESO_EXTERNO (excluido de ventas).
  3. pagar_deuda: baja el pasivo y descuenta una cuenta. El lado de caja usa
     un Movimiento PAGO_DEUDA (excluido de los gastos de la semana). Version
     base: se paga desde UNA cuenta elegida; el reparto por prioridad de
     cuentas (seccion 2) queda para mas adelante.

El balance ya resta la suma de Saldo_Actual_Deuda (Total_Deudas), asi que
estas operaciones se reflejan solas en patrimonio y escenarios.
"""

from app.models import Deuda, Cuenta, Movimiento, Movimiento_Deuda


def _crear_o_ubicar_deuda(sesion, id_deuda, descripcion):
    """Devuelve la deuda por id, o crea una nueva con la descripcion dada.
    La descripcion es UNIQUE, asi que si se repite se reutiliza la existente."""
    if id_deuda is not None:
        deuda = sesion.get(Deuda, id_deuda)
        if deuda is None:
            raise ValueError(f"No existe deuda con Id {id_deuda}")
        return deuda
    if not descripcion or not descripcion.strip():
        raise ValueError("La descripción de la deuda es obligatoria")
    existente = sesion.query(Deuda).filter(
        Deuda.Descripcion_Deuda.ilike(descripcion.strip())
    ).first()
    if existente:
        return existente
    deuda = Deuda(Descripcion_Deuda=descripcion.strip(), Saldo_Actual_Deuda=0)
    sesion.add(deuda)
    sesion.flush()
    return deuda


def registrar_deuda_simple(sesion, monto, descripcion=None, id_deuda=None, fecha=None):
    """Sube el pasivo sin mover caja (interes, gasto pagado por un tercero)."""
    if monto <= 0:
        raise ValueError("El monto de la deuda debe ser mayor a cero")

    try:
        deuda = _crear_o_ubicar_deuda(sesion, id_deuda, descripcion)
        mov = Movimiento_Deuda(
            Id_Deuda=deuda.Id_Deuda,
            Fecha_Movimiento_Deuda=fecha,
            Tipo_Movimiento_Deuda="AUMENTO",
            Monto_Movimiento_Deuda=monto,
            Id_Cuenta_Pago=None,
        )
        sesion.add(mov)
        deuda.Saldo_Actual_Deuda = deuda.Saldo_Actual_Deuda + monto
        sesion.commit()
        return deuda
    except Exception as e:
        sesion.rollback()
        raise e


def registrar_prestamo_con_ingreso(sesion, monto, id_cuenta_destino, descripcion=None, id_deuda=None, fecha=None):
    """Sube el pasivo y entra dinero a una cuenta (prestamo desembolsado)."""
    if monto <= 0:
        raise ValueError("El monto del préstamo debe ser mayor a cero")

    cuenta = sesion.get(Cuenta, id_cuenta_destino)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta_destino}")

    try:
        deuda = _crear_o_ubicar_deuda(sesion, id_deuda, descripcion)

        # Lado del pasivo: aumenta la deuda
        mov_deuda = Movimiento_Deuda(
            Id_Deuda=deuda.Id_Deuda,
            Fecha_Movimiento_Deuda=fecha,
            Tipo_Movimiento_Deuda="AUMENTO",
            Monto_Movimiento_Deuda=monto,
            Id_Cuenta_Pago=id_cuenta_destino,
        )
        sesion.add(mov_deuda)
        deuda.Saldo_Actual_Deuda = deuda.Saldo_Actual_Deuda + monto

        # Lado de caja: entra el dinero a la cuenta (no es una venta)
        mov_caja = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="INGRESO_EXTERNO",
            Id_Cuenta_Origen=None,
            Id_Cuenta_Destino=id_cuenta_destino,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=f"Préstamo: {deuda.Descripcion_Deuda}",
        )
        sesion.add(mov_caja)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta + monto

        sesion.commit()
        return deuda
    except Exception as e:
        sesion.rollback()
        raise e


def pagar_deuda(sesion, id_deuda, monto, id_cuenta, fecha=None):
    """Amortiza una deuda: baja el pasivo y descuenta una cuenta."""
    deuda = sesion.get(Deuda, id_deuda)
    if deuda is None:
        raise ValueError(f"No existe deuda con Id {id_deuda}")

    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")

    if monto <= 0:
        raise ValueError("El monto del pago debe ser mayor a cero")

    if monto > deuda.Saldo_Actual_Deuda:
        raise ValueError(
            f"El pago ({monto} Bs) supera el saldo de la deuda "
            f"'{deuda.Descripcion_Deuda}' ({deuda.Saldo_Actual_Deuda} Bs)"
        )

    if cuenta.Saldo_Actual_Cuenta < monto:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el pago es de {monto} Bs"
        )

    try:
        # Lado de caja: sale el dinero (no es un gasto de la semana)
        mov_caja = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="PAGO_DEUDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,
            Monto_Movimiento=monto,
            Descripcion_Movimiento=f"Pago de deuda: {deuda.Descripcion_Deuda}",
        )
        sesion.add(mov_caja)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto

        # Lado del pasivo: baja la deuda
        mov_deuda = Movimiento_Deuda(
            Id_Deuda=id_deuda,
            Fecha_Movimiento_Deuda=fecha,
            Tipo_Movimiento_Deuda="PAGO",
            Monto_Movimiento_Deuda=monto,
            Id_Cuenta_Pago=id_cuenta,
        )
        sesion.add(mov_deuda)
        deuda.Saldo_Actual_Deuda = deuda.Saldo_Actual_Deuda - monto

        sesion.commit()
        return deuda
    except Exception as e:
        sesion.rollback()
        raise e
