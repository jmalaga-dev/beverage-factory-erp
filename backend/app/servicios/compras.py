"""
compras.py
Logica de negocio para registrar una compra de materia prima.
Una compra implica: validar saldo, descontar dinero, crear el movimiento
y crear la compra. Todo de forma ATOMICA (o pasa todo, o no pasa nada).
"""

from datetime import date
from app.models import Compra, Cuenta, Movimiento, Materia_Prima, Proveedor, Proveedor_Materia_Prima


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


def registrar_compra(sesion, id_materia_prima, id_cuenta, cantidad, precio_total, fecha=None, id_proveedor=None):
    """
    Registra una compra de materia prima pagada desde una cuenta.

    Parametros:
        sesion: la sesion de SQLAlchemy (la "conversacion" con la base)
        id_materia_prima: que materia prima se compro
        id_cuenta: de que cuenta se paga
        cantidad: cuanto se compro
        precio_total: cuanto costo en total
        fecha: fecha de la compra (si no se da, no se asume hoy todavia)
        id_proveedor: de quien se compro. Obligatorio cuando la materia
            prima ya tiene proveedores activos (para llenar el catalogo de
            proveedores); si la materia no tiene ninguno, se bloquea pidiendo
            registrar uno primero (mejora 5.1).

    Devuelve: el objeto Compra creado.
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

    # LA validacion clave: hay saldo suficiente?
    if cuenta.Saldo_Actual_Cuenta < precio_total:
        raise ValueError(
            f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
            f"{cuenta.Saldo_Actual_Cuenta} Bs y la compra cuesta {precio_total} Bs"
        )

    # ----- 2. EJECUTAR LA OPERACION (todo o nada) -----

    try:
        # 2a. Crear el movimiento de dinero (SALIDA de la cuenta)
        movimiento = Movimiento(
            Fecha_Movimiento=fecha,
            Tipo_Movimiento="SALIDA",
            Id_Cuenta_Origen=id_cuenta,
            Id_Cuenta_Destino=None,            # sale del sistema (pago a proveedor)
            Monto_Movimiento=precio_total,
            Descripcion_Movimiento=f"Compra de {materia.Descripcion_Materia_Prima}",
        )
        sesion.add(movimiento)
        sesion.flush()   # fuerza a la base a asignar el Id_Movimiento sin confirmar aun

        # 2b. Descontar el dinero de la cuenta (mantener el saldo)
        cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - precio_total

        # 2c. Crear la compra, vinculada al movimiento y al proveedor
        compra = Compra(
            Id_Materia_Prima=id_materia_prima,
            Fecha_Compra=fecha,
            Cantidad_Compra=cantidad,
            Precio_Compra=precio_total,
            Cantidad_Restante_Compra=cantidad,   # al comprar, queda todo disponible
            Id_Movimiento=movimiento.Id_Movimiento,
            Id_Proveedor=id_proveedor,
        )
        sesion.add(compra)

        # 2d. Confirmar TODO junto: aqui se guarda de verdad
        sesion.commit()

        return compra

    except Exception as e:
        # Si algo fallo a mitad, deshacer TODO (ni movimiento, ni descuento, ni compra)
        sesion.rollback()
        raise e