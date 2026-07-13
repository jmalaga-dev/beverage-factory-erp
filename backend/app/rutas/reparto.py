"""
Rutas del reparto de gasto por prioridad de cuentas (mejora 2.B): propone de
qué cuentas sacar un gasto y lo registra como varios movimientos coordinados.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.reparto import proponer_reparto, registrar_gasto_repartido

router = APIRouter(tags=["reparto"])


@router.get("/reparto/preview")
def preview_reparto(
    monto: Decimal = Query(...),
    tipo: str = Query(...),   # FAMILIAR / FABRICA
    sesion: Session = Depends(get_sesion),
):
    """Propone de qué cuentas sacar un gasto por prioridad, sin tocar nada."""
    try:
        return proponer_reparto(sesion, monto, tipo.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class FuenteEntrada(BaseModel):
    id_cuenta: int
    monto: Decimal


class RepartoGastoEntrada(BaseModel):
    descripcion: str
    fuentes: list[FuenteEntrada]
    id_grupo: int | None = None
    fecha: date | None = None


@router.post("/reparto-gasto")
def crear_gasto_repartido(datos: RepartoGastoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra un gasto que sale de varias cuentas (una SALIDA por fuente)."""
    try:
        fuentes = [{"id_cuenta": f.id_cuenta, "monto": f.monto} for f in datos.fuentes]
        resultado = registrar_gasto_repartido(
            sesion,
            descripcion=datos.descripcion,
            fuentes=fuentes,
            id_grupo=datos.id_grupo,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Gasto repartido registrado", **resultado}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
