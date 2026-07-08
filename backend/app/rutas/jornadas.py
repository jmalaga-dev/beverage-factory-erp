"""
Rutas de jornadas de trabajo (registro de horas; no mueven dinero).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Registro_Trabajador, Trabajador
from app.servicios.trabajadores import editar_jornada, eliminar_jornada, registrar_jornada

router = APIRouter(tags=["jornadas"])


class JornadaEntrada(BaseModel):
    id_trabajador: int
    horas: float
    fecha: date | None = None


@router.post("/jornadas")
def crear_jornada(datos: JornadaEntrada, sesion: Session = Depends(get_sesion)):
    """Registra una jornada de trabajo (solo horas, no mueve dinero)."""
    try:
        jornada = registrar_jornada(
            sesion,
            id_trabajador=datos.id_trabajador,
            horas=Decimal(str(datos.horas)),
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Jornada registrada", "id_jornada": jornada.Id_Registro_Trabajador}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jornadas")
def listar_jornadas(sesion: Session = Depends(get_sesion)):
    jornadas = sesion.query(Registro_Trabajador).all()
    resultado = []
    for j in jornadas:
        trabajador = sesion.get(Trabajador, j.Id_Trabajador)
        pagada = j.Id_Pago_Trabajador is not None
        sin_usar = j.Horas_Restante_Registro_Trabajador == j.Horas_Registro_Trabajador
        resultado.append({
            "id_jornada": j.Id_Registro_Trabajador,
            "id_trabajador": j.Id_Trabajador,
            "nombre_trabajador": trabajador.Nombre_Trabajador if trabajador else "?",
            "fecha": str(j.Fecha_Registro_Trabajador),
            "horas": float(j.Horas_Registro_Trabajador),
            "horas_restantes": float(j.Horas_Restante_Registro_Trabajador or 0),
            "pagada": pagada,
            "intacta": pagada is False and sin_usar,  # se puede editar/eliminar
        })
    return resultado


class JornadaEdicion(BaseModel):
    id_trabajador: int | None = None
    horas: float | None = None
    fecha: date | None = None


@router.patch("/jornadas/{id_jornada}")
def actualizar_jornada(id_jornada: int, datos: JornadaEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige una jornada mal registrada. Solo si esta intacta (sin usar y sin pagar)."""
    try:
        jornada = editar_jornada(
            sesion,
            id_jornada=id_jornada,
            id_trabajador=datos.id_trabajador,
            horas=Decimal(str(datos.horas)) if datos.horas is not None else None,
            fecha=datos.fecha,
        )
        return {"mensaje": "Jornada actualizada", "id_jornada": jornada.Id_Registro_Trabajador}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jornadas/{id_jornada}")
def borrar_jornada(id_jornada: int, sesion: Session = Depends(get_sesion)):
    """Anula una jornada mal registrada. Solo si esta intacta (sin usar y sin pagar)."""
    try:
        eliminar_jornada(sesion, id_jornada=id_jornada)
        return {"mensaje": "Jornada eliminada"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
