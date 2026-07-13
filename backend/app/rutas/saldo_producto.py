"""
Ruta de solo lectura del acumulador de inversion/ingresos por producto
(mejora 2.C, Tajada 1). Base del reparto 70/30 de la venta (Tajada 2).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.saldo_producto import calcular_saldos


router = APIRouter(tags=["saldo-producto"])


@router.get("/saldo-productos")
def ver_saldo_productos(
    dias_comparacion: int = Query(30, ge=1),
    sesion: Session = Depends(get_sesion),
):
    """Saldo acumulado (ingresos - inversion) de cada producto terminado, con
    su valor de hace N dias para ver la tendencia reciente."""
    filas = calcular_saldos(sesion, dias_comparacion=dias_comparacion)
    return [
        {
            "id_producto": f["id_producto"],
            "nombre": f["nombre"],
            "inversion_acumulada": round(float(f["inversion_acumulada"]), 2),
            "ingresos_acumulados": round(float(f["ingresos_acumulados"]), 2),
            "saldo": round(float(f["saldo"]), 2),
            "recupero_inversion": f["recupero_inversion"],
            "saldo_hace_dias": round(float(f["saldo_hace_dias"]), 2),
            "dias_comparacion": f["dias_comparacion"],
        }
        for f in filas
    ]
