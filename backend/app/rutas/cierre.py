"""
Rutas del cierre semanal de produccion (mejora 3.7): vista previa del reparto
de horas standby entre los terminados de un rango, y su ejecucion.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.cierre_semanal import calcular_cierre, ejecutar_cierre

router = APIRouter(tags=["cierre"])


def _serializar_plan(plan):
    """Convierte el plan (con Decimales) al dict que consume el frontend."""
    return {
        "sin_datos": plan["sin_datos"],
        "base": plan.get("base"),
        "base_alt": plan.get("base_alt"),
        "desde": plan["desde"],
        "hasta": plan["hasta"],
        "total_botellas": float(plan["total_botellas"]),
        "total_paquetes": float(plan.get("total_paquetes", 0)),
        "total_horas": float(plan["total_horas"]),
        "total_valor_trabajo": float(plan["total_valor_trabajo"]),
        "jornadas": [
            {
                "id_jornada": j["id_jornada"],
                "nombre_trabajador": j["nombre_trabajador"],
                "fecha": j["fecha"],
                "horas": float(j["horas"]),
                "tarifa": float(j["tarifa"]),
                "valor": float(j["valor"]),
            }
            for j in plan["jornadas"]
        ],
        "productos": [
            {
                "id_produccion": p["id_produccion"],
                "nombre": p["nombre"],
                "botellas": float(p["botellas"]),
                "paquetes": round(float(p["paquetes"]), 4),
                "proporcion": round(float(p["proporcion"]) * 100, 2),
                "costo_unit_actual": round(float(p["costo_unit_actual"]), 4),
                "horas_total": round(float(p["horas_total"]), 4),
                "costo_trabajo": round(float(p["costo_trabajo"]), 2),
                "costo_unit_nuevo": round(float(p["costo_unit_nuevo"]), 4),
                # Numeros de la otra base, para ver cuanto varia el reparto:
                "proporcion_alt": round(float(p["proporcion_alt"]) * 100, 2),
                "horas_total_alt": round(float(p["horas_total_alt"]), 4),
                "costo_trabajo_alt": round(float(p["costo_trabajo_alt"]), 2),
                "costo_unit_nuevo_alt": round(float(p["costo_unit_nuevo_alt"]), 4),
                "asignaciones": [
                    {
                        "id_jornada": a["id_jornada"],
                        "nombre_trabajador": a["nombre_trabajador"],
                        "horas": round(float(a["horas"]), 4),
                    }
                    for a in p["asignaciones"]
                ],
            }
            for p in plan["productos"]
        ],
    }


@router.get("/cierre-semanal/preview")
def preview_cierre(
    desde: date = Query(...),
    hasta: date = Query(...),
    base: str = Query("botellas"),
    sesion: Session = Depends(get_sesion),
):
    """Vista previa del reparto de horas standby, sin tocar nada."""
    try:
        plan = calcular_cierre(sesion, desde, hasta, base)
        return _serializar_plan(plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CierreEntrada(BaseModel):
    desde: date
    hasta: date
    base: str = "botellas"


@router.post("/cierre-semanal")
def hacer_cierre(datos: CierreEntrada, sesion: Session = Depends(get_sesion)):
    """Ejecuta el cierre: reparte las horas y actualiza los costos. Atomico."""
    try:
        resultado = ejecutar_cierre(sesion, datos.desde, datos.hasta, datos.base)
        return {"mensaje": "Cierre registrado", **resultado}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
