"""
absorcion.py
Absorcion de costos indirectos por botella producida (mejora 1.4).

Algunos costos no son insumos directos pero deben repartirse entre las
botellas que se produzcan despues, para que "alguien los pague" (replica el
Excel): utensilios/equipos comprados, horas de feriado, y el costo de las
mermas. Cada Item_Absorcion tiene un costo y una cantidad de botellas
estimadas que lo cubriran; costo/botellas = Bs por botella. Cada produccion
descuenta botellas de los items con saldo y suma ese monto a su costo.

Decision de negocio (jul 2026): un utensilio va SOLO a absorcion, nunca a
Activo fijo (un solo camino por compra), para no contar su costo dos veces.

Nota contable: al sumar la absorcion al costo del producto, ese costo se
capitaliza en el valor del stock terminado. Es el comportamiento buscado
(que el precio de venta cubra estos gastos), y es coherente con el Excel.
"""

from app.models import (
    Item_Absorcion, Absorcion_Produccion, Cuenta, Movimiento,
    Compra, Produccion, Produccion_Intermedio,
)
from app.config import TASA_ABSORCION_DEFECTO


def _costo_por_botella(item):
    if not item.Botellas_Estimadas_Item_Absorcion:
        return 0
    return item.Costo_Item_Absorcion / item.Botellas_Estimadas_Item_Absorcion


def absorber_en_produccion(sesion, id_produccion, botellas):
    """Reparte los items de absorcion con saldo entre las botellas de esta
    produccion. Cada item aporta min(botellas, su restante) * costo_por_botella,
    baja su restante y deja un registro Absorcion_Produccion. Devuelve el monto
    total absorbido. NO hace commit: corre dentro de la transaccion de la
    produccion.
    """
    total = 0
    items = (
        sesion.query(Item_Absorcion)
        .filter(Item_Absorcion.Botellas_Restantes_Item_Absorcion > 0)
        .order_by(Item_Absorcion.Id_Item_Absorcion)
        .all()
    )
    for item in items:
        # Cada item aporta hasta agotar su saldo (regla de 3 si le queda menos
        # que las botellas producidas).
        botellas_item = min(botellas, item.Botellas_Restantes_Item_Absorcion)
        if botellas_item <= 0:
            continue
        monto = botellas_item * _costo_por_botella(item)
        item.Botellas_Restantes_Item_Absorcion = (
            item.Botellas_Restantes_Item_Absorcion - botellas_item
        )
        sesion.add(Absorcion_Produccion(
            Id_Item_Absorcion=item.Id_Item_Absorcion,
            Id_Produccion=id_produccion,
            Botellas_Absorbidas=botellas_item,
            Monto_Absorbido=monto,
        ))
        total += monto
    return total


def _crear_item(sesion, tipo, descripcion, costo, botellas_estimadas, fecha):
    """Crea un Item_Absorcion (restante = estimadas al inicio). NO commit."""
    if costo <= 0:
        raise ValueError("El costo debe ser mayor a cero")
    if botellas_estimadas is None or botellas_estimadas <= 0:
        raise ValueError("Las botellas estimadas deben ser mayores a cero")
    item = Item_Absorcion(
        Tipo_Item_Absorcion=tipo,
        Descripcion_Item_Absorcion=descripcion.strip(),
        Costo_Item_Absorcion=costo,
        Botellas_Estimadas_Item_Absorcion=botellas_estimadas,
        Botellas_Restantes_Item_Absorcion=botellas_estimadas,
        Fecha_Item_Absorcion=fecha,
    )
    sesion.add(item)
    return item


def _registrar_gasto_absorbible(sesion, tipo, descripcion, costo, id_cuenta, botellas_estimadas, fecha):
    """Registra un utensilio o feriado: sale dinero de una cuenta (SALIDA, es
    un gasto real) y se crea el item que las botellas iran absorbiendo."""
    if not descripcion or not descripcion.strip():
        raise ValueError("La descripción es obligatoria")
    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")
    if costo <= 0:
        raise ValueError("El costo debe ser mayor a cero")
    if cuenta.Saldo_Actual_Cuenta < costo:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el costo es de {costo} Bs"
        )
    etiqueta = "Utensilio/equipo" if tipo == "UTENSILIO" else "Feriado"
    try:
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,
            Monto_Movimiento=costo,
            Descripcion_Movimiento=f"{etiqueta}: {descripcion.strip()}",
        )
        sesion.add(movimiento)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - costo
        item = _crear_item(sesion, tipo, descripcion, costo, botellas_estimadas, fecha)
        sesion.commit()
        return item
    except Exception as e:
        sesion.rollback()
        raise e


def registrar_utensilio(sesion, descripcion, costo, id_cuenta, botellas_estimadas=None, fecha=None):
    """Compra de un utensilio/equipo menor: sale dinero y su costo se absorbe."""
    if botellas_estimadas is None:
        botellas_estimadas = costo * TASA_ABSORCION_DEFECTO
    return _registrar_gasto_absorbible(sesion, "UTENSILIO", descripcion, costo, id_cuenta, botellas_estimadas, fecha)


def registrar_feriado(sesion, descripcion, costo, id_cuenta, botellas_estimadas=None, fecha=None):
    """Horas pagadas por feriado (sin produccion): sale dinero y se absorbe."""
    if botellas_estimadas is None:
        botellas_estimadas = costo * TASA_ABSORCION_DEFECTO
    return _registrar_gasto_absorbible(sesion, "FERIADO", descripcion, costo, id_cuenta, botellas_estimadas, fecha)


def crear_item_merma(sesion, costo, descripcion, fecha, botellas_estimadas=None):
    """(Interno) crea un item de absorcion tipo MERMA a partir del costo del
    stock perdido. Si no se indican botellas estimadas, la tasa por defecto
    define cuantas lo absorberan. NO commit: corre dentro de la transaccion
    de la merma."""
    if botellas_estimadas is None:
        botellas_estimadas = costo * TASA_ABSORCION_DEFECTO
    return _crear_item(sesion, "MERMA", descripcion, costo, botellas_estimadas, fecha)
