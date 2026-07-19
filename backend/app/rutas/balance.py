"""
Rutas de balance: vista previa del estado actual, tomar la foto
(inmutable) y consultar la ultima foto guardada.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Balance, Balance_Detalle
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


@router.get("/balances/{id_balance}/detalle")
def detalle_balance(id_balance: int, sesion: Session = Depends(get_sesion)):
    """
    Detalle por item de una foto guardada (mejora 4.6), agrupado por bloque:
    materia prima, intermedio, terminado y activos.

    Lee lo que quedo CONGELADO en la foto (incluida la descripcion de cada
    item tal como se llamaba ese dia), no el catalogo de hoy: por eso responde
    "como estaba" y no "como esta".

    Las fotos anteriores a la migracion 024 solo tienen bloque TERMINADO; sus
    otros bloques vienen vacios porque ese dato nunca se guardo, no porque
    valieran cero. El frontend lo aclara.
    """
    if sesion.get(Balance, id_balance) is None:
        raise HTTPException(status_code=404, detail=f"No existe balance con Id {id_balance}")

    filas = (
        sesion.query(Balance_Detalle)
        .filter(Balance_Detalle.Id_Balance == id_balance)
        .order_by(Balance_Detalle.Tipo_Detalle, Balance_Detalle.Descripcion_Balance_Detalle)
        .all()
    )
    bloques = {"MP": [], "INTERMEDIO": [], "TERMINADO": [], "ACTIVO": []}
    for f in filas:
        bloques.setdefault(f.Tipo_Detalle, []).append({
            "id_item": f.Id_Item_Balance_Detalle,
            "descripcion": f.Descripcion_Balance_Detalle,
            "cantidad": float(f.Cantidad_Balance_Detalle or 0),
            "valor": float(f.Valor_Balance_Detalle or 0),
        })
    return {
        "id_balance": id_balance,
        "bloques": bloques,
        "totales": {k: sum(x["valor"] for x in v) for k, v in bloques.items()},
    }
