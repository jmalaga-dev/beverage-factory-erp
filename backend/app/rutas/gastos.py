"""
Rutas de gastos operativos (salidas de dinero de una cuenta).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.gastos import registrar_gasto, registrar_gasto_cubierto_externo
from app.servicios.gastos_lote import previsualizar_gastos_lote, registrar_gastos_lote

router = APIRouter(tags=["gastos"])


class GastoEntrada(BaseModel):
    id_cuenta: int
    monto: Decimal
    descripcion: str
    id_grupo: int | None = None
    fecha: date | None = None
    # Gasto cubierto por un aporte externo (item 10b): lo pagó alguien de fuera
    # (ej. la cónyuge). Se registra el gasto pero no reduce las cuentas.
    pagado_externo: bool = False
    quien_pago: str | None = None


@router.post("/gastos")
def crear_gasto(datos: GastoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra un gasto que sale de una cuenta (o cubierto por aporte externo)."""
    try:
        if datos.pagado_externo:
            mov = registrar_gasto_cubierto_externo(
                sesion,
                id_cuenta=datos.id_cuenta,
                monto=datos.monto,
                descripcion=datos.descripcion,
                quien_pago=datos.quien_pago,
                id_grupo=datos.id_grupo,
                fecha=datos.fecha or date.today(),
            )
        else:
            mov = registrar_gasto(
                sesion,
                id_cuenta=datos.id_cuenta,
                monto=datos.monto,
                descripcion=datos.descripcion,
                id_grupo=datos.id_grupo,
                fecha=datos.fecha or date.today(),
            )
        return {
            "mensaje": "Gasto registrado",
            "id_movimiento": mov.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LineaGastoLote(BaseModel):
    monto: Decimal
    descripcion: str
    id_grupo: int | None = None
    # Pagado por otra persona (bloque D): no sale de ninguna cuenta propia y
    # queda fuera del reparto por prioridad.
    pagado_externo: bool = False
    quien_pago: str | None = None


class GastosLoteEntrada(BaseModel):
    lineas: list[LineaGastoLote]
    tipo: str = "FAMILIAR"   # FAMILIAR = Casa->Fabrica, FABRICA = Fabrica->Casa
    fecha: date | None = None


def _lineas_lote_dict(datos: GastosLoteEntrada):
    return [
        {
            "monto": l.monto,
            "descripcion": l.descripcion,
            "id_grupo": l.id_grupo,
            "pagado_externo": l.pagado_externo,
            "quien_pago": l.quien_pago,
        }
        for l in datos.lineas
    ]


@router.post("/gastos-lote/preview")
def previsualizar_gastos_lote_ruta(datos: GastosLoteEntrada, sesion: Session = Depends(get_sesion)):
    """Calcula, sin registrar nada, de qué cuenta saldría cada línea (tabla
    de gastos con reparto por prioridad, Casa primero por defecto)."""
    try:
        return previsualizar_gastos_lote(sesion, _lineas_lote_dict(datos), tipo=datos.tipo.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gastos-lote")
def crear_gastos_lote(datos: GastosLoteEntrada, sesion: Session = Depends(get_sesion)):
    """Registra varios gastos a la vez, drenando primero la cuenta de mayor
    prioridad del tipo elegido. Una línea que se paga entre las dos cuentas
    genera un movimiento por tramo. Todo o nada."""
    try:
        resultado = registrar_gastos_lote(
            sesion,
            lineas=_lineas_lote_dict(datos),
            tipo=datos.tipo.upper(),
            fecha=datos.fecha or date.today(),
        )
        partidas = sum(1 for r in resultado["lineas"] if r["partida"])
        externas = sum(1 for r in resultado["lineas"] if r["externa"])
        detalles = []
        if partidas:
            detalles.append(f"{partidas} pagado(s) entre las dos cuentas")
        if externas:
            detalles.append(f"{externas} cubierto(s) por otra persona")
        mensaje = f"{len(resultado['lineas'])} gastos registrados"
        if detalles:
            mensaje += " (" + "; ".join(detalles) + ")"
        return {
            "mensaje": mensaje,
            "total_fabrica": float(resultado["total_fabrica"]),
            "total_casa": float(resultado["total_casa"]),
            "total_externo": float(resultado["total_externo"]),
            "lineas": [
                {
                    "partida": r["partida"],
                    "externa": r["externa"],
                    "tramos": [
                        {"id_movimiento": t["id_movimiento"], "cuenta": t["cuenta"],
                         "monto": float(t["monto"]), "quien": t["quien"]}
                        for t in r["tramos"]
                    ],
                }
                for r in resultado["lineas"]
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
