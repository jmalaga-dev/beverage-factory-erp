"""
reparto.py
Reparto de un gasto por prioridad de cuentas (mejora 2.B).

Un gasto puede cubrirse con varias cuentas: se PROPONE drenar las cuentas por
orden de prioridad según el tipo de gasto (familiar: Casa→Fábrica; de fábrica:
Fábrica→Casa), respetando saldos y partiendo entre cuentas cuando la primera no
alcanza. Es una sugerencia: el usuario puede ajustar cuánto sale de cada una.
Al confirmar, cada fuente genera un movimiento SALIDA; todo atómico.
"""

from app.models import Cuenta, Movimiento, Grupo_Movimiento
from app.config import PRIORIDAD_CUENTAS


def asignar_por_prioridad(cuentas, monto_total, orden_roles):
    """Núcleo puro (sin BD): ordena las cuentas por prioridad de rol (y a igual
    rol, más saldo primero) y reparte greedily hasta cubrir el monto. Devuelve
    (fuentes, pendiente). `cuentas` es una lista de dicts con id_cuenta, nombre,
    rol, disponible."""
    def clave(c):
        rol = c["rol"] if c["rol"] in orden_roles else "OTRA"
        idx = orden_roles.index(rol) if rol in orden_roles else len(orden_roles)
        return (idx, -c["disponible"])
    ordenadas = sorted(cuentas, key=clave)

    pendiente = monto_total
    fuentes = []
    for c in ordenadas:
        usar = min(pendiente, c["disponible"]) if pendiente > 0 else 0
        fuentes.append({**c, "utilizado": usar})
        pendiente -= usar
    return fuentes, pendiente


def proponer_reparto(sesion, monto_total, tipo):
    """Propone de qué cuentas sacar el gasto, por prioridad. No toca la BD."""
    if tipo not in PRIORIDAD_CUENTAS:
        raise ValueError(f"Tipo de gasto inválido: {tipo}")
    if monto_total <= 0:
        raise ValueError("El monto debe ser mayor a cero")

    monto_total = float(monto_total)
    cuentas = [
        {"id_cuenta": c.Id_Cuenta, "nombre": c.Nombre_Cuenta, "rol": c.Rol_Cuenta,
         "disponible": float(c.Saldo_Actual_Cuenta)}
        for c in sesion.query(Cuenta).filter(Cuenta.Habilitado_Cuenta.is_(True)).all()
    ]
    fuentes, pendiente = asignar_por_prioridad(cuentas, monto_total, PRIORIDAD_CUENTAS[tipo])

    return {
        "monto_total": monto_total,
        "cubierto": pendiente <= 0,
        "faltante": max(pendiente, 0),
        "fuentes": fuentes,
    }


def registrar_gasto_repartido(sesion, descripcion, fuentes, id_grupo=None, fecha=None):
    """
    Registra un gasto que sale de varias cuentas (una SALIDA por fuente).

    fuentes: lista de dicts {"id_cuenta": int, "monto": Decimal}.
    Valida TODO antes de tocar nada (saldos de cada cuenta) y ejecuta atómico.
    """
    if not descripcion or not descripcion.strip():
        raise ValueError("La descripción es obligatoria")

    fuentes = [f for f in fuentes if f.get("monto") and f["monto"] > 0]
    if not fuentes:
        raise ValueError("Debe indicar al menos una fuente con monto")

    if id_grupo is not None and sesion.get(Grupo_Movimiento, id_grupo) is None:
        raise ValueError(f"No existe grupo de movimiento con Id {id_grupo}")

    # Validar todas las cuentas y saldos antes de ejecutar (atómico)
    for f in fuentes:
        cuenta = sesion.get(Cuenta, f["id_cuenta"])
        if cuenta is None:
            raise ValueError(f"No existe cuenta con Id {f['id_cuenta']}")
        if f["monto"] <= 0:
            raise ValueError("Cada monto debe ser mayor a cero")
        if cuenta.Saldo_Actual_Cuenta < f["monto"]:
            raise ValueError(
                f"Saldo insuficiente. La cuenta '{cuenta.Nombre_Cuenta}' tiene "
                f"{cuenta.Saldo_Actual_Cuenta} Bs y se pide {f['monto']} Bs"
            )

    try:
        total = 0
        for f in fuentes:
            cuenta = sesion.get(Cuenta, f["id_cuenta"])
            movimiento = Movimiento(
                Fecha_Movimiento=fecha,
                Tipo_Movimiento="SALIDA",
                Id_Cuenta_Origen=f["id_cuenta"],
                Id_Cuenta_Destino=None,
                Monto_Movimiento=f["monto"],
                Descripcion_Movimiento=descripcion.strip(),
                Id_Grupo_Movimiento=id_grupo,
            )
            sesion.add(movimiento)
            cuenta.Saldo_Actual_Cuenta = cuenta.Saldo_Actual_Cuenta - f["monto"]
            total += f["monto"]

        sesion.commit()
        return {"movimientos": len(fuentes), "total": float(total)}

    except Exception as e:
        sesion.rollback()
        raise e
