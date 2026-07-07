"""
Rutas de prorrateo mensual: reparto de gastos extra entre productos
segun las horas de fabrica que uso cada uno.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Gasto_Extra, Horas_Producto_Mes, Producto_Terminado
from app.servicios.prorrateo import calcular_prorrateo_mensual

router = APIRouter(tags=["prorrateo"])


class ProrrateoEntrada(BaseModel):
    anio_mes: str   # ej "2026-06"


@router.post("/prorrateos")
def crear_prorrateo(datos: ProrrateoEntrada, sesion: Session = Depends(get_sesion)):
    """Reparte los gastos extra del mes entre los productos segun horas."""
    try:
        creados = calcular_prorrateo_mensual(sesion, datos.anio_mes)
        return {"mensaje": "Prorrateo calculado", "asignaciones": len(creados)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/horas-producto-mes/{anio_mes}")
def ver_horas_producto_mes(anio_mes: str, sesion: Session = Depends(get_sesion)):
    """Qué productos usaron la fábrica ese mes y cuántas horas cada uno."""
    filas = sesion.query(Horas_Producto_Mes).filter_by(Anio_Mes=anio_mes).all()
    resultado = []
    total = 0
    for f in filas:
        producto = sesion.get(Producto_Terminado, f.Id_Producto_Terminado)
        horas = float(f.Horas_Producto_Mes)
        total += horas
        resultado.append({
            "producto": producto.Descripcion_Producto_Terminado if producto else "?",
            "horas": horas,
        })
    return {"total_horas": total, "detalle": resultado}


@router.get("/gastos-extra-total")
def ver_gastos_extra_total(sesion: Session = Depends(get_sesion)):
    """Lista de gastos extra mensuales y su total."""
    gastos = sesion.query(Gasto_Extra).all()
    total = sum(float(g.Precio_Mensual_Gasto_Extra or 0) for g in gastos)
    detalle = [{"descripcion": g.Descripcion_Gasto_Extra, "precio": float(g.Precio_Mensual_Gasto_Extra or 0)} for g in gastos]
    return {"total": total, "detalle": detalle}
