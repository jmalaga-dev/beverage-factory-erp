"""
Rutas de deudas y su amortizacion (mejoras 7.0 y 7.3).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Deuda, Movimiento_Deuda, Cuenta
from app.servicios.deudas import (
    registrar_deuda_simple,
    registrar_prestamo_con_ingreso,
    pagar_deuda,
)

router = APIRouter(tags=["deudas"])


@router.get("/deudas")
def listar_deudas(sesion: Session = Depends(get_sesion)):
    """Deudas con su saldo actual. Las de saldo 0 ya estan saldadas."""
    deudas = sesion.query(Deuda).all()
    return [
        {
            "id_deuda": d.Id_Deuda,
            "descripcion": d.Descripcion_Deuda,
            "saldo": float(d.Saldo_Actual_Deuda),
        }
        for d in deudas
    ]


@router.get("/deudas/{id_deuda}/movimientos")
def listar_movimientos_deuda(id_deuda: int, sesion: Session = Depends(get_sesion)):
    """Historial de aumentos y pagos de una deuda."""
    if sesion.get(Deuda, id_deuda) is None:
        raise HTTPException(status_code=404, detail=f"No existe deuda con Id {id_deuda}")
    movs = (
        sesion.query(Movimiento_Deuda)
        .filter(Movimiento_Deuda.Id_Deuda == id_deuda)
        .order_by(Movimiento_Deuda.Fecha_Movimiento_Deuda, Movimiento_Deuda.Id_Movimiento_Deuda)
        .all()
    )
    resultado = []
    for m in movs:
        cuenta = sesion.get(Cuenta, m.Id_Cuenta_Pago) if m.Id_Cuenta_Pago else None
        resultado.append({
            "id_movimiento_deuda": m.Id_Movimiento_Deuda,
            "fecha": m.Fecha_Movimiento_Deuda.isoformat() if m.Fecha_Movimiento_Deuda else None,
            "tipo": m.Tipo_Movimiento_Deuda,
            "monto": float(m.Monto_Movimiento_Deuda),
            "cuenta": cuenta.Nombre_Cuenta if cuenta else None,
        })
    return resultado


class DeudaSimpleEntrada(BaseModel):
    descripcion: str | None = None
    id_deuda: int | None = None
    monto: Decimal
    fecha: date | None = None


@router.post("/deudas/simple")
def crear_deuda_simple(datos: DeudaSimpleEntrada, sesion: Session = Depends(get_sesion)):
    """Aumenta una deuda sin mover caja (interés, gasto pagado por un tercero).
    Si se pasa id_deuda, suma a esa; si no, crea/reutiliza por descripción."""
    try:
        deuda = registrar_deuda_simple(
            sesion,
            monto=datos.monto,
            descripcion=datos.descripcion,
            id_deuda=datos.id_deuda,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Deuda registrada", "id_deuda": deuda.Id_Deuda, "saldo": float(deuda.Saldo_Actual_Deuda)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PrestamoEntrada(BaseModel):
    descripcion: str | None = None
    id_deuda: int | None = None
    monto: Decimal
    id_cuenta_destino: int
    fecha: date | None = None


@router.post("/deudas/prestamo")
def crear_prestamo(datos: PrestamoEntrada, sesion: Session = Depends(get_sesion)):
    """Toma un préstamo: aumenta la deuda y entra el dinero a una cuenta."""
    try:
        deuda = registrar_prestamo_con_ingreso(
            sesion,
            monto=datos.monto,
            id_cuenta_destino=datos.id_cuenta_destino,
            descripcion=datos.descripcion,
            id_deuda=datos.id_deuda,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Préstamo registrado", "id_deuda": deuda.Id_Deuda, "saldo": float(deuda.Saldo_Actual_Deuda)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PagoDeudaEntrada(BaseModel):
    id_deuda: int
    monto: Decimal
    id_cuenta: int
    fecha: date | None = None


@router.post("/deudas/pago")
def pagar(datos: PagoDeudaEntrada, sesion: Session = Depends(get_sesion)):
    """Amortiza una deuda descontando de una cuenta elegida."""
    try:
        deuda = pagar_deuda(
            sesion,
            id_deuda=datos.id_deuda,
            monto=datos.monto,
            id_cuenta=datos.id_cuenta,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Pago registrado", "id_deuda": deuda.Id_Deuda, "saldo": float(deuda.Saldo_Actual_Deuda)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
