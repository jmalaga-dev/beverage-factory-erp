"""
Rutas de absorcion de costos indirectos por botella (mejora 1.4):
registrar utensilios/equipos y feriados, y ver el saldo pendiente de cada
item. Las mermas crean sus items automaticamente (ver servicios/inventario).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import TASA_ABSORCION_DEFECTO
from app.dependencias import get_sesion
from app.models import Item_Absorcion
from app.servicios.absorcion import registrar_utensilio, registrar_feriado

router = APIRouter(tags=["absorcion"])


@router.get("/items-absorcion")
def listar_items_absorcion(sesion: Session = Depends(get_sesion)):
    """Items de absorcion con su saldo. tasa_defecto ayuda al frontend a
    sugerir las botellas estimadas al registrar uno nuevo."""
    items = sesion.query(Item_Absorcion).order_by(Item_Absorcion.Id_Item_Absorcion.desc()).all()
    return {
        "tasa_defecto": TASA_ABSORCION_DEFECTO,
        "items": [
            {
                "id_item_absorcion": it.Id_Item_Absorcion,
                "tipo": it.Tipo_Item_Absorcion,
                "descripcion": it.Descripcion_Item_Absorcion,
                "costo": float(it.Costo_Item_Absorcion),
                "botellas_estimadas": float(it.Botellas_Estimadas_Item_Absorcion),
                "botellas_restantes": float(it.Botellas_Restantes_Item_Absorcion),
                "costo_por_botella": round(
                    float(it.Costo_Item_Absorcion) / float(it.Botellas_Estimadas_Item_Absorcion), 4
                ) if it.Botellas_Estimadas_Item_Absorcion else 0,
                "saldado": it.Botellas_Restantes_Item_Absorcion <= 0,
                "fecha": it.Fecha_Item_Absorcion.isoformat() if it.Fecha_Item_Absorcion else None,
            }
            for it in items
        ],
    }


class AbsorbibleEntrada(BaseModel):
    descripcion: str
    costo: Decimal
    id_cuenta: int
    # Cuantas botellas se estima que lo cubriran. Si no se manda, el servicio
    # usa costo * TASA_ABSORCION_DEFECTO.
    botellas_estimadas: Decimal | None = None
    fecha: date | None = None


@router.post("/utensilios")
def crear_utensilio(datos: AbsorbibleEntrada, sesion: Session = Depends(get_sesion)):
    """Compra de un utensilio/equipo: sale dinero y su costo se absorbe."""
    try:
        item = registrar_utensilio(
            sesion,
            descripcion=datos.descripcion,
            costo=datos.costo,
            id_cuenta=datos.id_cuenta,
            botellas_estimadas=datos.botellas_estimadas,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Utensilio registrado", "id": item.Id_Item_Absorcion}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/feriados")
def crear_feriado(datos: AbsorbibleEntrada, sesion: Session = Depends(get_sesion)):
    """Horas pagadas por feriado (sin produccion): sale dinero y se absorbe."""
    try:
        item = registrar_feriado(
            sesion,
            descripcion=datos.descripcion,
            costo=datos.costo,
            id_cuenta=datos.id_cuenta,
            botellas_estimadas=datos.botellas_estimadas,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Feriado registrado", "id": item.Id_Item_Absorcion}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
