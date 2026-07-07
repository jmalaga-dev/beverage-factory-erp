"""
Rutas de clientes y sectores (zonas de reparto).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Cliente, Sector
from app.servicios.clientes import crear_sector, registrar_cliente

router = APIRouter(tags=["clientes"])


@router.get("/clientes")
def listar_clientes(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de todos los clientes."""
    clientes = sesion.query(Cliente).all()
    return [
        {
            "id_cliente": c.Id_Cliente,
            "nombre": c.Nombre_Cliente,
            "celular": c.Celular_Cliente,
            "id_sector": c.Id_Sector,
        }
        for c in clientes
    ]


class ClienteEntrada(BaseModel):
    nombre: str
    apellido: str | None = None
    celular: str | None = None
    licoreria: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    id_sector: int | None = None


@router.post("/clientes")
def crear_cliente_endpoint(datos: ClienteEntrada, sesion: Session = Depends(get_sesion)):
    """Registra un cliente."""
    try:
        cliente = registrar_cliente(
            sesion,
            nombre=datos.nombre,
            apellido=datos.apellido,
            celular=datos.celular,
            licoreria=datos.licoreria,
            latitud=datos.latitud,
            longitud=datos.longitud,
            id_sector=datos.id_sector,
        )
        return {"mensaje": "Cliente registrado", "id_cliente": cliente.Id_Cliente}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sectores")
def listar_sectores(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de sectores (para el desplegable)."""
    sectores = sesion.query(Sector).all()
    return [
        {"id_sector": s.Id_Sector, "nombre": s.Nombre_Sector}
        for s in sectores
    ]


class SectorEntrada(BaseModel):
    nombre: str


@router.post("/sectores")
def crear_sector_endpoint(datos: SectorEntrada, sesion: Session = Depends(get_sesion)):
    """Crea un sector (zona) validado."""
    try:
        sector = crear_sector(sesion, datos.nombre)
        return {"mensaje": "Sector listo", "id_sector": sector.Id_Sector, "nombre": sector.Nombre_Sector}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
