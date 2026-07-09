"""
Rutas de balance: vista previa del estado actual, tomar la foto
(inmutable) y consultar la ultima foto guardada.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Balance
from app.servicios.balance import (
    calcular_estado_actual,
    resumen_desde_ultima_foto,
    serializar_balance,
    tomar_balance,
)

router = APIRouter(tags=["balance"])


class BalanceEntrada(BaseModel):
    fecha_balance: date | None = None
    dias_semana: int = 7


@router.post("/balances")
def crear_balance(datos: BalanceEntrada, sesion: Session = Depends(get_sesion)):
    """Toma una foto del balance actual de la fabrica."""
    try:
        balance = tomar_balance(sesion, fecha_balance=datos.fecha_balance, dias_semana=datos.dias_semana)
        return {
            "mensaje": "Balance tomado",
            "id_balance": balance.Id_Balance,
            "patrimonio": float(balance.Patrimonio),
            "escenario_c": float(balance.Escenario_C),
            "escenario_b": float(balance.Escenario_B),
            "escenario_a": float(balance.Escenario_A),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balance-actual")
def balance_actual(sesion: Session = Depends(get_sesion)):
    """Calcula el estado actual con desglose completo, SIN guardar la foto."""
    return calcular_estado_actual(sesion)


@router.get("/balance-ultimo")
def balance_ultimo(sesion: Session = Depends(get_sesion)):
    """Devuelve la última foto de balance guardada, con desglose."""
    ultimo = sesion.query(Balance).order_by(Balance.Id_Balance.desc()).first()
    if ultimo is None:
        return None
    return serializar_balance(ultimo)


@router.get("/balances")
def listar_balances(sesion: Session = Depends(get_sesion)):
    """
    Lista todas las fotos de balance guardadas, cada una con su desglose
    completo, ordenadas de la más reciente a la más antigua. El frontend
    (comparativa 4.4) elige dos y calcula la diferencia en el cliente, sin
    pedir cada foto por separado.
    """
    balances = sesion.query(Balance).order_by(Balance.Id_Balance.desc()).all()
    return [serializar_balance(b) for b in balances]


@router.get("/balance-resumen-semana")
def balance_resumen_semana(sesion: Session = Depends(get_sesion)):
    """
    Resumen dia a dia desde la ultima foto guardada hasta hoy: ventas,
    compras, gastos y pagos, mas el detalle de que paso cada dia. No
    requiere tomar una foto nueva.
    """
    return resumen_desde_ultima_foto(sesion)
