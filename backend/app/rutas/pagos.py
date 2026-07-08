"""
Rutas de pagos a trabajadores: pago sugerido y registro del pago semanal.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.pagos import calcular_pago_sugerido, registrar_pago_semanal

router = APIRouter(tags=["pagos"])


@router.get("/trabajadores/{id_trabajador}/pago-sugerido")
def ver_pago_sugerido(id_trabajador: int, sesion: Session = Depends(get_sesion)):
    """Calcula cuanto se le debe a un trabajador (horas pendientes x tarifa)."""
    try:
        sugerido, pendientes = calcular_pago_sugerido(sesion, id_trabajador)
        return {
            "id_trabajador": id_trabajador,
            "monto_sugerido": float(sugerido),
            "jornadas_pendientes": len(pendientes),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PagoEntrada(BaseModel):
    id_trabajador: int
    id_cuenta: int
    monto_real: Decimal
    fecha: date | None = None


@router.post("/pagos")
def crear_pago(datos: PagoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra el pago semanal a un trabajador."""
    try:
        pago = registrar_pago_semanal(
            sesion,
            id_trabajador=datos.id_trabajador,
            id_cuenta=datos.id_cuenta,
            monto_real=datos.monto_real,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Pago registrado",
            "id_pago": pago.Id_Pago_Trabajador,
            "sugerido": float(pago.Monto_Sugerido_Pago),
            "real": float(pago.Monto_Real_Pago),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
