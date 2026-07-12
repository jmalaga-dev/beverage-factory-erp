"""
compras.py
Logica de negocio para registrar una compra de materia prima.
Una compra implica: validar saldo, descontar dinero, crear el movimiento
y crear la compra. Todo de forma ATOMICA (o pasa todo, o no pasa nada).
"""

from datetime import date
from app.models import Compra, Cuenta, Movimiento, Materia_Prima, Proveedor, Proveedor_Materia_Prima
from app.servicios.deudas import aumentar_deuda_proveedor


def _proveedores_activos_de(sesion, id_materia_prima):
    """Ids de proveedores activos (proveedor habilitado + vinculo habilitado)
    que venden una materia prima."""
    vinculos = (
        sesion.query(Proveedor_Materia_Prima)
        .filter(
            Proveedor_Materia_Prima.Id_Materia_Prima == id_materia_prima,
            Proveedor_Materia_Prima.Habilitado_Proveedor_Materia_Prima.is_(True),
        )
        .all()
    )
    activos = set()
    for v in vinculos:
        p = sesion.get(Proveedor, v.Id_Proveedor)
        if p is not None and p.Habilitado_Proveedor:
            activos.add(p.Id_Proveedor)
    return activos


def _aplicar_compra(sesion, id_materia_prima, id_cuenta, cantidad, precio_total,
                    fecha=None, id_proveedor=None, monto_pagado=None, recibida=True):
    """
    Aplica una compra de materia prima SIN hacer commit: valida, mueve dinero,
    crea deuda si corresponde y crea el lote. Se deja sin commit para poder
    COMPONER varias compras en una sola transaccion (una compra dividida por
    area = N compras que se registran todas o ninguna; ver compra_dividida.py).

    Parametros:
        sesion: la sesion de SQLAlchemy (la "conversacion" con la base)
        id_materia_prima: que materia prima se compro
        id_cuenta: de que cuenta se paga la parte pagada
        cantidad: cuanto se compro
        precio_total: cuanto costo en total (SIEMPRE el precio completo; es el
            que define el costo del lote, aunque se pague en partes)
        fecha: fecha de la compra (si no se da, no se asume hoy todavia)
        id_proveedor: de quien se compro. Obligatorio cuando la materia
            prima ya tiene proveedores activos (para llenar el catalogo de
            proveedores); si la materia no tiene ninguno, se bloquea pidiendo
            registrar uno primero (mejora 5.1).
        monto_pagado: cuanto se paga ahora desde la cuenta. None = pago total
            (precio_total), comportamiento clasico. Si es menor al precio, el
            faltante se vuelve una deuda al proveedor (compra a credito, 5.1).
        recibida: True = la mercaderia llego y entra al stock ya. False =
            pedido pendiente: se registra el lote con restante 0 (invisible
            como stock) hasta llamar a recibir_compra (5.1).

    Devuelve: el objeto Compra creado (sin commit).
    Lanza ValueError si algo no es valido (ej: saldo insuficiente).
    """

    # ----- 1. VALIDACIONES (antes de tocar nada) -----

    # Verificar que la materia prima existe
    materia = sesion.get(Materia_Prima, id_materia_prima)
    if materia is None:
        raise ValueError(f"No existe materia prima con Id {id_materia_prima}")

    # Verificar que la cuenta existe
    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")

    # Verificar que el precio y cantidad son positivos
    if precio_total <= 0:
        raise ValueError("El precio total debe ser mayor a cero")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero")

    # Cuanto se paga ahora: None = todo. Debe estar entre 0 y el precio total.
    if monto_pagado is None:
        monto_pagado = precio_total
    if monto_pagado < 0:
        raise ValueError("El monto pagado no puede ser negativo")
    if monto_pagado > precio_total:
        raise ValueError("El monto pagado no puede superar el precio total")
    faltante = precio_total - monto_pagado

    # Proveedor (mejora 5.1): toda compra debe quedar atada a un proveedor.
    activos = _proveedores_activos_de(sesion, id_materia_prima)
    if not activos:
        raise ValueError(
            f"'{materia.Descripcion_Materia_Prima}' no tiene ningún proveedor. "
            "Registra un proveedor para esta materia prima antes de comprarla."
        )
    if id_proveedor is None:
        raise ValueError("Debes indicar de qué proveedor se compró")
    if id_proveedor not in activos:
        raise ValueError(
            f"El proveedor indicado no vende '{materia.Descripcion_Materia_Prima}' "
            "(o está deshabilitado para esa materia)"
        )

    # La validacion de saldo es sobre lo que se paga AHORA, no el precio total
    # (lo demas va a deuda).
    if cuenta.Saldo_Actual_Cuenta < monto_pagado:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y el pago es de {monto_pagado} Bs"
        )

    # ----- 2. EJECUTAR (sin commit) -----

    id_movimiento = None
    # 2a. Movimiento de dinero solo por lo que se paga ahora (si se paga algo)
    if monto_pagado > 0:
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,        # sale del sistema (pago a proveedor)
            Monto_Movimiento=monto_pagado,
            Descripcion_Movimiento=f"Compra de {materia.Descripcion_Materia_Prima}",
        )
        sesion.add(movimiento)
        sesion.flush()   # asigna el Id_Movimiento sin confirmar aun
        id_movimiento = movimiento.Id_Movimiento
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - monto_pagado

    # 2b. El faltante se vuelve deuda al proveedor (compra a credito)
    if faltante > 0:
        aumentar_deuda_proveedor(sesion, id_proveedor, faltante, fecha)

    # 2c. Crear la compra. El precio guardado es el COMPLETO (costo real).
    #     Si es un pedido pendiente, no hay stock disponible aun (restante 0).
    compra = Compra(
        Id_Materia_Prima=id_materia_prima,
        Fecha_Compra=fecha,
        Cantidad_Compra=cantidad,
        Precio_Compra=precio_total,
        Cantidad_Restante_Compra=(cantidad if recibida else 0),
        Id_Movimiento=id_movimiento,
        Id_Proveedor=id_proveedor,
        Recibida_Compra=recibida,
    )
    sesion.add(compra)

    return compra


def registrar_compra(sesion, id_materia_prima, id_cuenta, cantidad, precio_total,
                     fecha=None, id_proveedor=None, monto_pagado=None, recibida=True):
    """Registra una compra suelta y hace commit. Envuelve a _aplicar_compra."""
    try:
        compra = _aplicar_compra(
            sesion, id_materia_prima, id_cuenta, cantidad, precio_total,
            fecha=fecha, id_proveedor=id_proveedor, monto_pagado=monto_pagado,
            recibida=recibida,
        )
        sesion.commit()
        return compra
    except Exception as e:
        sesion.rollback()
        raise e


def recibir_compra(sesion, id_compra):
    """Marca un pedido pendiente como recibido: el stock aparece (restante =
    cantidad). No mueve dinero ni deuda (eso ya paso al registrar el pedido)."""
    compra = sesion.get(Compra, id_compra)
    if compra is None:
        raise ValueError(f"No existe compra con Id {id_compra}")
    if compra.Recibida_Compra:
        raise ValueError("Esta compra ya estaba recibida")
    try:
        compra.Cantidad_Restante_Compra = compra.Cantidad_Compra
        compra.Recibida_Compra = True
        sesion.commit()
        return compra
    except Exception as e:
        sesion.rollback()
        raise e