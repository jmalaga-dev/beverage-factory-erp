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
from app.servicios.balance import calcular_estado_actual, resumen_desde_ultima_foto, tomar_balance

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
    total_inmuebles = float(ultimo.Total_Inmuebles or 0)
    total_equipos = float(ultimo.Total_Equipos or 0)
    total_otros = float(ultimo.Total_Otros_Activos or 0)
    activos_fijos = total_inmuebles + total_equipos + total_otros
    return {
        "id_balance": ultimo.Id_Balance,
        "fecha": str(ultimo.Fecha_Balance),
        "efectivo": float(ultimo.Total_Efectivo or 0),
        "stock_materia_prima": float(ultimo.Valor_Stock_Materia_Prima or 0),
        "stock_producto_intermedio": float(ultimo.Valor_Stock_Intermedio or 0),
        "valor_horas_standby": float(ultimo.Valor_Horas_Standby or 0),
        "stock_producto_terminado": float(ultimo.Valor_Stock_Producto_Terminado or 0),
        "stock_producto_terminado_conservador": float(ultimo.Valor_Stock_Producto_Terminado_Conservador or 0),
        "deudas": float(ultimo.Total_Deudas or 0),
        "activos_fijos": round(activos_fijos, 2),
        "total_inmuebles": round(total_inmuebles, 2),
        "total_equipos": round(total_equipos, 2),
        "total_otros": round(total_otros, 2),
        "escenario_c": float(ultimo.Escenario_C or 0),
        "escenario_b": float(ultimo.Escenario_B or 0),
        "escenario_a": float(ultimo.Escenario_A or 0),
        "patrimonio": float(ultimo.Patrimonio or 0),
        "ventas": float(ultimo.Ventas_Semana or 0),
        "compras": float(ultimo.Compras_Semana or 0),
        "gastos": float(ultimo.Gastos_Semana or 0),
        # None (no 0): las fotos tomadas antes de esta columna no tienen este dato
        "pagos": float(ultimo.Pagos_Semana) if ultimo.Pagos_Semana is not None else None,
    }


@router.get("/balance-resumen-semana")
def balance_resumen_semana(sesion: Session = Depends(get_sesion)):
    """
    Resumen dia a dia desde la ultima foto guardada hasta hoy: ventas,
    compras, gastos y pagos, mas el detalle de que paso cada dia. No
    requiere tomar una foto nueva.
    """
    return resumen_desde_ultima_foto(sesion)
