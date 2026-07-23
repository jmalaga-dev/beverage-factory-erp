"""
Rutas de transferencias entre cuentas propias e ingresos externos (mejora 7.5).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.transferencias import (
    registrar_transferencia, registrar_ingreso_externo,
    listar_ingresos_externos, anular_ingreso_externo,
)

router = APIRouter(tags=["transferencias"])


class TransferenciaEntrada(BaseModel):
    id_cuenta_origen: int
    id_cuenta_destino: int
    monto: Decimal
    descripcion: str
    fecha: date | None = None


@router.post("/transferencias")
def crear_transferencia(datos: TransferenciaEntrada, sesion: Session = Depends(get_sesion)):
    """Mueve dinero de una cuenta propia a otra."""
    try:
        mov = registrar_transferencia(
            sesion,
            id_cuenta_origen=datos.id_cuenta_origen,
            id_cuenta_destino=datos.id_cuenta_destino,
            monto=datos.monto,
            descripcion=datos.descripcion,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Transferencia registrada",
            "id_movimiento": mov.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class IngresoExternoEntrada(BaseModel):
    id_cuenta_destino: int
    monto: Decimal
    descripcion: str
    fecha: date | None = None


@router.post("/ingresos-externos")
def crear_ingreso_externo(datos: IngresoExternoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra dinero que entra a una cuenta desde fuera de la fabrica."""
    try:
        mov = registrar_ingreso_externo(
            sesion,
            id_cuenta_destino=datos.id_cuenta_destino,
            monto=datos.monto,
            descripcion=datos.descripcion,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Ingreso externo registrado",
            "id_movimiento": mov.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ingresos-externos")
def ver_ingresos_externos(sesion: Session = Depends(get_sesion)):
    """Lista los ingresos externos con su estado (anulado o no), para el
    historial y poder anular uno mal cargado (item 10a)."""
    return listar_ingresos_externos(sesion)


@router.post("/ingresos-externos/{id_movimiento}/anular")
def anular_ingreso(id_movimiento: int, sesion: Session = Depends(get_sesion)):
    """Anula un ingreso externo mal cargado con un movimiento inverso (item 10a)."""
    try:
        anulacion = anular_ingreso_externo(sesion, id_movimiento, fecha=date.today())
        return {"mensaje": "Ingreso externo anulado", "id_movimiento": anulacion.Id_Movimiento}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
