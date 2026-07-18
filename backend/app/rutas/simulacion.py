"""
rutas/simulacion.py
Endpoints de la simulacion de producto nuevo (mejora 1.5).

Son de SOLO LECTURA: no crean ni modifican nada. Se usa POST (no GET) porque
la receta hipotetica es una lista de insumos que no entra comoda en la query
string; mismo criterio que /ventas/preview-reparto.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.simulacion import indicadores_referencia, simular

router = APIRouter()


class InsumoSimulado(BaseModel):
    tipo: str            # MP / INTERMEDIO
    id_insumo: int
    cantidad: Decimal


class SimulacionEntrada(BaseModel):
    insumos: list[InsumoSimulado]
    rendimiento: Decimal                       # cuanto sale la receta (ej. 30 litros)
    litros_por_botella: Decimal | None = None  # capacidad de la botella (ej. 0.75)
    botellas_por_paquete: int = 1
    meses: int = 12                            # ventana; 0 = todo el historico


@router.post("/simulacion")
def simular_producto(datos: SimulacionEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.insumos:
        raise HTTPException(status_code=400, detail="Agrega al menos un insumo a la receta")
    for i in datos.insumos:
        if i.tipo not in ("MP", "INTERMEDIO"):
            raise HTTPException(status_code=400, detail=f"Tipo de insumo inválido: {i.tipo}")
    try:
        return simular(
            sesion,
            insumos=[i.model_dump() for i in datos.insumos],
            rendimiento=datos.rendimiento,
            litros_por_botella=datos.litros_por_botella,
            botellas_por_paquete=datos.botellas_por_paquete,
            meses=datos.meses,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/simulacion/referencia")
def referencia(meses: int = 12, sesion: Session = Depends(get_sesion)):
    """Carga fija promedio por botella (mano de obra, absorcion, gastos extra)."""
    return indicadores_referencia(sesion, meses)
