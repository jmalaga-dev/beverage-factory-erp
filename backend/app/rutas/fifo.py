"""
Ruta de resolucion FIFO (mejora 3.1): dado un producto y una cantidad,
sugiere que lotes consumir del mas antiguo al mas nuevo.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.fifo import resolver_fifo

router = APIRouter(tags=["fifo"])


@router.get("/fifo/{origen}/{id_producto}")
def sugerir_fifo(origen: str, id_producto: int, cantidad: Decimal = Query(...), sesion: Session = Depends(get_sesion)):
    """Sugiere los lotes a consumir por FIFO. origen: MP / INTERMEDIO / TERMINADO."""
    try:
        return resolver_fifo(sesion, origen.upper(), id_producto, cantidad)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
