"""
Rutas de movimientos de inventario: mermas, ajustes, devoluciones y
reprocesos sobre lotes de compra o produccion.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.inventario import registrar_movimiento_inventario

router = APIRouter(tags=["inventario"])


class MovimientoInventarioEntrada(BaseModel):
    tipo: str        # MERMA, AJUSTE, DEVOLUCION, REPROCESO
    sentido: str     # SALIDA, ENTRADA
    origen_lote: str # COMPRA, PRODUCCION, PRODUCCION_INTERMEDIO
    cantidad: Decimal
    motivo: str | None = None
    id_compra: int | None = None
    id_produccion: int | None = None
    id_prod_intermedio: int | None = None
    fecha: date | None = None


@router.post("/movimientos-inventario")
def crear_movimiento_inventario(datos: MovimientoInventarioEntrada, sesion: Session = Depends(get_sesion)):
    """Registra una merma, ajuste, devolucion o reproceso sobre un lote."""
    try:
        mov = registrar_movimiento_inventario(
            sesion,
            tipo=datos.tipo,
            sentido=datos.sentido,
            origen_lote=datos.origen_lote,
            cantidad=datos.cantidad,
            motivo=datos.motivo,
            id_compra=datos.id_compra,
            id_produccion=datos.id_produccion,
            id_prod_intermedio=datos.id_prod_intermedio,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Movimiento de inventario registrado", "id": mov.Id_Movimiento_Inventario}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
