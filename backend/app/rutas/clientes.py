"""
Rutas de clientes y sectores (zonas de reparto).

Edicion / deshabilitar / borrar (mejora 6.1): mismo criterio que en
catalogos.py. Editar es siempre seguro (relaciones por Id); deshabilitar
saca de los desplegables sin borrar; borrar es real y solo si no hay
historial (un cliente sin ventas, un sector sin clientes).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Cliente, Sector, Venta
from app.servicios.clientes import crear_sector, registrar_cliente

router = APIRouter(tags=["clientes"])


# =========================================================
# CLIENTES
# =========================================================

@router.get("/clientes")
def listar_clientes(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de todos los clientes (con todos los campos editables)."""
    clientes = sesion.query(Cliente).all()
    con_ventas = {row[0] for row in sesion.query(Venta.Id_Cliente).distinct() if row[0] is not None}
    return [
        {
            "id_cliente": c.Id_Cliente,
            "nombre": c.Nombre_Cliente,
            "apellido": c.Apellido_Cliente,
            "celular": c.Celular_Cliente,
            "licoreria": c.Licoreria_Cliente,
            "latitud": float(c.Latitud_Cliente) if c.Latitud_Cliente is not None else None,
            "longitud": float(c.Longitud_Cliente) if c.Longitud_Cliente is not None else None,
            "id_sector": c.Id_Sector,
            "habilitado": c.Habilitado_Cliente,
            "en_uso": c.Id_Cliente in con_ventas,
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


class ClienteEdicion(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    celular: str | None = None
    licoreria: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    id_sector: int | None = None


@router.patch("/clientes/{id_cliente}")
def actualizar_cliente(id_cliente: int, datos: ClienteEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige los datos de un cliente. El sector, si se indica, debe existir.
    Para desvincular el sector, mandar id_sector = 0."""
    c = sesion.get(Cliente, id_cliente)
    if c is None:
        raise HTTPException(status_code=404, detail=f"No existe cliente con Id {id_cliente}")
    if datos.nombre is not None:
        if not datos.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
        c.Nombre_Cliente = datos.nombre.strip()
    if datos.apellido is not None:
        c.Apellido_Cliente = datos.apellido or None
    if datos.celular is not None:
        c.Celular_Cliente = datos.celular or None
    if datos.licoreria is not None:
        c.Licoreria_Cliente = datos.licoreria or None
    if datos.latitud is not None:
        c.Latitud_Cliente = datos.latitud
    if datos.longitud is not None:
        c.Longitud_Cliente = datos.longitud
    if datos.id_sector is not None:
        if datos.id_sector == 0:
            c.Id_Sector = None
        else:
            if sesion.get(Sector, datos.id_sector) is None:
                raise HTTPException(status_code=400, detail=f"No existe sector con Id {datos.id_sector}")
            c.Id_Sector = datos.id_sector
    sesion.commit()
    return {"mensaje": "Cliente actualizado", "id_cliente": c.Id_Cliente}


class HabilitadoEntrada(BaseModel):
    habilitado: bool


@router.patch("/clientes/{id_cliente}/habilitado")
def cambiar_habilitado_cliente(id_cliente: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    c = sesion.get(Cliente, id_cliente)
    if c is None:
        raise HTTPException(status_code=404, detail=f"No existe cliente con Id {id_cliente}")
    c.Habilitado_Cliente = datos.habilitado
    sesion.commit()
    return {"mensaje": "Cliente actualizado", "id_cliente": c.Id_Cliente, "habilitado": c.Habilitado_Cliente}


@router.delete("/clientes/{id_cliente}")
def borrar_cliente(id_cliente: int, sesion: Session = Depends(get_sesion)):
    c = sesion.get(Cliente, id_cliente)
    if c is None:
        raise HTTPException(status_code=404, detail=f"No existe cliente con Id {id_cliente}")
    tiene_ventas = sesion.query(Venta).filter(Venta.Id_Cliente == id_cliente).first() is not None
    if tiene_ventas:
        raise HTTPException(
            status_code=400,
            detail="No se puede borrar: el cliente tiene ventas registradas. Deshabilítalo en su lugar.",
        )
    sesion.delete(c)
    sesion.commit()
    return {"mensaje": "Cliente eliminado"}


# =========================================================
# SECTORES
# =========================================================

@router.get("/sectores")
def listar_sectores(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de sectores (para el desplegable)."""
    sectores = sesion.query(Sector).all()
    con_clientes = {row[0] for row in sesion.query(Cliente.Id_Sector).distinct() if row[0] is not None}
    return [
        {
            "id_sector": s.Id_Sector,
            "nombre": s.Nombre_Sector,
            "habilitado": s.Habilitado_Sector,
            "en_uso": s.Id_Sector in con_clientes,
        }
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


class SectorEdicion(BaseModel):
    nombre: str


@router.patch("/sectores/{id_sector}")
def actualizar_sector(id_sector: int, datos: SectorEdicion, sesion: Session = Depends(get_sesion)):
    s = sesion.get(Sector, id_sector)
    if s is None:
        raise HTTPException(status_code=404, detail=f"No existe sector con Id {id_sector}")
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
    existente = sesion.query(Sector).filter(
        Sector.Nombre_Sector.ilike(datos.nombre.strip()), Sector.Id_Sector != id_sector
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe otro sector con ese nombre")
    s.Nombre_Sector = datos.nombre.strip()
    sesion.commit()
    return {"mensaje": "Sector actualizado", "id_sector": s.Id_Sector}


@router.patch("/sectores/{id_sector}/habilitado")
def cambiar_habilitado_sector(id_sector: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    s = sesion.get(Sector, id_sector)
    if s is None:
        raise HTTPException(status_code=404, detail=f"No existe sector con Id {id_sector}")
    s.Habilitado_Sector = datos.habilitado
    sesion.commit()
    return {"mensaje": "Sector actualizado", "id_sector": s.Id_Sector, "habilitado": s.Habilitado_Sector}


@router.delete("/sectores/{id_sector}")
def borrar_sector(id_sector: int, sesion: Session = Depends(get_sesion)):
    s = sesion.get(Sector, id_sector)
    if s is None:
        raise HTTPException(status_code=404, detail=f"No existe sector con Id {id_sector}")
    tiene_clientes = sesion.query(Cliente).filter(Cliente.Id_Sector == id_sector).first() is not None
    if tiene_clientes:
        raise HTTPException(
            status_code=400,
            detail="No se puede borrar: el sector tiene clientes asignados. Deshabilítalo en su lugar.",
        )
    sesion.delete(s)
    sesion.commit()
    return {"mensaje": "Sector eliminado"}
