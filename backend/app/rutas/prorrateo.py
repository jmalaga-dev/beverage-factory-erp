"""
Rutas del cierre de mes (mejora 1.1): montos de gastos extra por mes y su pago,
y el prorrateo de esos gastos entre los productos según sus horas-hombre.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.gastos_mensuales import (
    registrar_monto_mes, pagar_monto_mes, anular_pago_mes, estado_mes,
)
from app.servicios.prorrateo import preview_prorrateo, ejecutar_prorrateo

router = APIRouter(tags=["prorrateo"])


# ---------- Gastos extra por mes ----------

class MontoMesEntrada(BaseModel):
    id_gasto_extra: int
    anio_mes: str          # 'YYYY-MM'
    monto: Decimal


@router.post("/gastos-mes")
def registrar_gasto_mes(datos: MontoMesEntrada, sesion: Session = Depends(get_sesion)):
    """Fija el monto real de un gasto recurrente en un mes concreto."""
    try:
        fila = registrar_monto_mes(sesion, datos.id_gasto_extra, datos.anio_mes, datos.monto)
        return {"mensaje": "Monto del mes guardado", "id_gasto_extra_mes": fila.Id_Gasto_Extra_Mes}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PagoMesEntrada(BaseModel):
    id_cuenta: int
    fecha: date | None = None


@router.post("/gastos-mes/{id_gasto_extra_mes}/pagar")
def pagar_gasto_mes(id_gasto_extra_mes: int, datos: PagoMesEntrada, sesion: Session = Depends(get_sesion)):
    """Paga el gasto del mes (SALIDA de una cuenta) y lo marca pagado."""
    try:
        fila = pagar_monto_mes(sesion, id_gasto_extra_mes, datos.id_cuenta, datos.fecha or date.today())
        return {"mensaje": "Gasto del mes pagado", "id_gasto_extra_mes": fila.Id_Gasto_Extra_Mes}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class AnulacionPagoEntrada(BaseModel):
    fecha: date | None = None


@router.post("/gastos-mes/{id_gasto_extra_mes}/anular-pago")
def anular_pago_gasto_mes(id_gasto_extra_mes: int, datos: AnulacionPagoEntrada,
                          sesion: Session = Depends(get_sesion)):
    """Anula el pago de un gasto del mes con un movimiento inverso: la plata
    vuelve a la cuenta y la fila queda sin pagar, para corregir el monto y
    volver a pagarla. No borra el pago original (bloque B)."""
    try:
        anulacion = anular_pago_mes(sesion, id_gasto_extra_mes, datos.fecha or date.today())
        return {
            "mensaje": "Pago anulado: la plata volvió a la cuenta y el gasto quedó sin pagar",
            "id_movimiento_anulacion": anulacion.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gastos-mes/{anio_mes}")
def ver_gastos_mes(anio_mes: str, sesion: Session = Depends(get_sesion)):
    """Los gastos del mes con su estado de pago, y si están todos pagados."""
    return estado_mes(sesion, anio_mes)


# ---------- Prorrateo ----------

@router.get("/prorrateo/preview/{anio_mes}")
def ver_preview_prorrateo(anio_mes: str, sesion: Session = Depends(get_sesion)):
    """Vista previa del reparto del mes (horas por producto + gastos), sin tocar nada."""
    return preview_prorrateo(sesion, anio_mes)


class ProrrateoEntrada(BaseModel):
    anio_mes: str


@router.post("/prorrateos")
def crear_prorrateo(datos: ProrrateoEntrada, sesion: Session = Depends(get_sesion)):
    """Ejecuta el prorrateo del mes: reparte los gastos entre los productos según horas."""
    try:
        resultado = ejecutar_prorrateo(sesion, datos.anio_mes)
        return {"mensaje": "Prorrateo calculado", **resultado}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
