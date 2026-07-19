"""
Rutas de movimientos de inventario: mermas, ajustes, devoluciones y
reprocesos sobre lotes de compra o produccion.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import UMBRAL_STOCK_MINIMO
from app.dependencias import get_sesion
from app.servicios.inventario import registrar_movimiento_inventario
from app.servicios.residuos import limpiar_residuos, listar_residuos

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
    # Solo aplica a MERMA (mejora 1.4): si su costo se reparte entre las
    # botellas futuras, y con cuantas botellas estimadas (None = tasa por
    # defecto). El control vive en la pantalla de Mermas.
    absorber_costo: bool = True
    botellas_estimadas_absorcion: Decimal | None = None


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
            absorber_costo=datos.absorber_costo,
            botellas_estimadas_absorcion=datos.botellas_estimadas_absorcion,
        )
        return {"mensaje": "Movimiento de inventario registrado", "id": mov.Id_Movimiento_Inventario}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- LIMPIEZA DE RESIDUOS BAJO EL UMBRAL (mejora 3.5) ----------

class ResiduoSeleccionado(BaseModel):
    origen: str      # MP / INTERMEDIO / TERMINADO
    id_lote: int


class LimpiezaResiduosEntrada(BaseModel):
    seleccion: list[ResiduoSeleccionado]
    fecha: date | None = None


@router.get("/residuos")
def listar_residuos_ruta(sesion: Session = Depends(get_sesion)):
    """
    Vista previa: lotes con resto positivo bajo el umbral. No toca nada.

    Devuelve tambien el umbral para que la pantalla lo muestre sin duplicar la
    constante en el frontend (si algun dia cambia en config.py, el texto de la
    pantalla la sigue sola).
    """
    return {
        "umbral": float(UMBRAL_STOCK_MINIMO),
        "residuos": listar_residuos(sesion),
    }


@router.post("/residuos/limpiar")
def limpiar_residuos_ruta(datos: LimpiezaResiduosEntrada, sesion: Session = Depends(get_sesion)):
    """Cierra en cero los lotes confirmados, con una MERMA por su resto exacto."""
    if not datos.seleccion:
        raise HTTPException(status_code=400, detail="No se seleccionó ningún residuo")
    try:
        return limpiar_residuos(
            sesion,
            seleccion=[s.model_dump() for s in datos.seleccion],
            fecha=datos.fecha or date.today(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
