"""
Rutas de compras de materia prima y consultas de su stock.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Compra, Materia_Prima
from app.servicios.compras import registrar_compra

router = APIRouter(tags=["compras"])


class CompraEntrada(BaseModel):
    id_materia_prima: int
    id_cuenta: int
    cantidad: float
    precio_total: float
    fecha: date | None = None


@router.post("/compras")
def crear_compra(datos: CompraEntrada, sesion: Session = Depends(get_sesion)):
    """
    Registra una compra de materia prima.
    Recibe los datos validados por Pydantic, llama al servicio, y devuelve
    la compra creada o un error si algo falla.
    """
    try:
        compra = registrar_compra(
            sesion,
            id_materia_prima=datos.id_materia_prima,
            id_cuenta=datos.id_cuenta,
            cantidad=Decimal(str(datos.cantidad)),
            precio_total=Decimal(str(datos.precio_total)),
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Compra registrada",
            "id_compra": compra.Id_Compra,
            "cantidad_restante": float(compra.Cantidad_Restante_Compra),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lotes-compra")
def listar_lotes_compra(sesion: Session = Depends(get_sesion)):
    """Lotes de compra con stock, incluyendo el nombre de la materia prima."""
    lotes = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > 0).all()
    resultado = []
    for c in lotes:
        mp = sesion.get(Materia_Prima, c.Id_Materia_Prima)
        resultado.append({
            "id_compra": c.Id_Compra,
            "id_materia_prima": c.Id_Materia_Prima,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "cantidad_restante": float(c.Cantidad_Restante_Compra),
            "precio_compra": float(c.Precio_Compra),
            "cantidad_compra": float(c.Cantidad_Compra),
        })
    return resultado


@router.get("/stock-materia-prima")
def stock_materia_prima(sesion: Session = Depends(get_sesion)):
    """Stock general de materia prima: suma el restante de todos los lotes por cada materia."""
    filas = (
        sesion.query(
            Materia_Prima.Id_Materia_Prima,
            Materia_Prima.Descripcion_Materia_Prima,
            Materia_Prima.Unidad_Materia_Prima,
            func.coalesce(func.sum(Compra.Cantidad_Restante_Compra), 0).label("total"),
        )
        .outerjoin(Compra, Compra.Id_Materia_Prima == Materia_Prima.Id_Materia_Prima)
        .group_by(
            Materia_Prima.Id_Materia_Prima,
            Materia_Prima.Descripcion_Materia_Prima,
            Materia_Prima.Unidad_Materia_Prima,
        )
        .all()
    )
    return [
        {
            "id_materia_prima": f.Id_Materia_Prima,
            "descripcion": f.Descripcion_Materia_Prima,
            "unidad": f.Unidad_Materia_Prima,
            "stock_total": float(f.total),
        }
        for f in filas
    ]
