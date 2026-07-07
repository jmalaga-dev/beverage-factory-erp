"""
Rutas de gastos operativos (salidas de dinero de una cuenta).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.gastos import registrar_gasto

router = APIRouter(tags=["gastos"])


class GastoEntrada(BaseModel):
    id_cuenta: int
    monto: float
    descripcion: str
    id_grupo: int | None = None
    fecha: date | None = None


@router.post("/gastos")
def crear_gasto(datos: GastoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra un gasto que sale de una cuenta."""
    try:
        mov = registrar_gasto(
            sesion,
            id_cuenta=datos.id_cuenta,
            monto=Decimal(str(datos.monto)),
            descripcion=datos.descripcion,
            id_grupo=datos.id_grupo,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Gasto registrado",
            "id_movimiento": mov.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
