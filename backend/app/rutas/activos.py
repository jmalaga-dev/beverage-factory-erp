"""
Rutas de activos fijos y sus tipos de bien.
Los activos (casa, vehiculo, equipos) suman al patrimonio y a los
escenarios de liquidez en el balance. Tipo_Bien es un catalogo simple
para clasificarlos.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import CATEGORIAS_TIPO_BIEN
from app.dependencias import get_sesion
from app.models import Activo, Tipo_Bien

router = APIRouter(tags=["activos"])


# ---------- TIPO DE BIEN (catalogo) ----------

@router.get("/tipos-bien")
def listar_tipos_bien(sesion: Session = Depends(get_sesion)):
    tipos = sesion.query(Tipo_Bien).all()
    return [
        {"id_tipo_bien": t.Id_Tipo_Bien, "nombre": t.Nombre_Tipo_Bien, "categoria": t.Categoria_Tipo_Bien}
        for t in tipos
    ]


class TipoBienEntrada(BaseModel):
    nombre: str
    categoria: str


@router.post("/tipos-bien")
def crear_tipo_bien(datos: TipoBienEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if datos.categoria not in CATEGORIAS_TIPO_BIEN:
        raise HTTPException(status_code=400, detail=f"Categoría inválida, debe ser una de: {CATEGORIAS_TIPO_BIEN}")
    # Normalizar para no duplicar por mayusculas/espacios (mismo criterio que grupos)
    existente = sesion.query(Tipo_Bien).filter(
        Tipo_Bien.Nombre_Tipo_Bien.ilike(datos.nombre.strip())
    ).first()
    if existente:
        return {"mensaje": "Ya existía", "id": existente.Id_Tipo_Bien}
    t = Tipo_Bien(Nombre_Tipo_Bien=datos.nombre.strip(), Categoria_Tipo_Bien=datos.categoria)
    sesion.add(t)
    sesion.commit()
    return {"mensaje": "Tipo de bien creado", "id": t.Id_Tipo_Bien}


class TipoBienEdicion(BaseModel):
    categoria: str


@router.patch("/tipos-bien/{id_tipo_bien}")
def actualizar_categoria_tipo_bien(id_tipo_bien: int, datos: TipoBienEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige la categoria de un tipo de bien (ej. los que quedaron en
    OTRO por defecto al migrar, o si se cambia de idea despues)."""
    t = sesion.get(Tipo_Bien, id_tipo_bien)
    if t is None:
        raise HTTPException(status_code=404, detail=f"No existe tipo de bien con Id {id_tipo_bien}")
    if datos.categoria not in CATEGORIAS_TIPO_BIEN:
        raise HTTPException(status_code=400, detail=f"Categoría inválida, debe ser una de: {CATEGORIAS_TIPO_BIEN}")
    t.Categoria_Tipo_Bien = datos.categoria
    sesion.commit()
    return {"mensaje": "Categoría actualizada", "id": t.Id_Tipo_Bien}


# ---------- ACTIVO ----------

@router.get("/activos")
def listar_activos(sesion: Session = Depends(get_sesion)):
    activos = sesion.query(Activo).all()
    resultado = []
    for a in activos:
        tipo = sesion.get(Tipo_Bien, a.Id_Tipo_Bien)
        resultado.append({
            "id_activo": a.Id_Activo,
            "descripcion": a.Descripcion_Activo,
            "valor": float(a.Valor_Activo),
            "id_tipo_bien": a.Id_Tipo_Bien,
            "tipo_bien": tipo.Nombre_Tipo_Bien if tipo else "?",
        })
    return resultado


class ActivoEntrada(BaseModel):
    descripcion: str
    valor: float
    id_tipo_bien: int


@router.post("/activos")
def crear_activo(datos: ActivoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    if datos.valor <= 0:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor a cero")
    if sesion.get(Tipo_Bien, datos.id_tipo_bien) is None:
        raise HTTPException(status_code=400, detail=f"No existe tipo de bien con Id {datos.id_tipo_bien}")
    a = Activo(
        Descripcion_Activo=datos.descripcion.strip(),
        Valor_Activo=Decimal(str(datos.valor)),
        Id_Tipo_Bien=datos.id_tipo_bien,
    )
    sesion.add(a)
    sesion.commit()
    return {"mensaje": "Activo creado", "id": a.Id_Activo}


class ActivoEdicion(BaseModel):
    descripcion: str | None = None
    valor: float | None = None
    id_tipo_bien: int | None = None


@router.patch("/activos/{id_activo}")
def actualizar_activo(id_activo: int, datos: ActivoEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige un activo (su valor cambia con el tiempo)."""
    a = sesion.get(Activo, id_activo)
    if a is None:
        raise HTTPException(status_code=404, detail=f"No existe activo con Id {id_activo}")
    if datos.descripcion is not None:
        if not datos.descripcion.strip():
            raise HTTPException(status_code=400, detail="La descripción no puede quedar vacía")
        a.Descripcion_Activo = datos.descripcion.strip()
    if datos.valor is not None:
        if datos.valor <= 0:
            raise HTTPException(status_code=400, detail="El valor debe ser mayor a cero")
        a.Valor_Activo = Decimal(str(datos.valor))
    if datos.id_tipo_bien is not None:
        if sesion.get(Tipo_Bien, datos.id_tipo_bien) is None:
            raise HTTPException(status_code=400, detail=f"No existe tipo de bien con Id {datos.id_tipo_bien}")
        a.Id_Tipo_Bien = datos.id_tipo_bien
    sesion.commit()
    return {"mensaje": "Activo actualizado", "id": a.Id_Activo}


@router.delete("/activos/{id_activo}")
def borrar_activo(id_activo: int, sesion: Session = Depends(get_sesion)):
    """Da de baja un activo (ej. se vendió). Es un borrado real: un activo
    no tiene historial que dependa de él (no genera movimientos)."""
    a = sesion.get(Activo, id_activo)
    if a is None:
        raise HTTPException(status_code=404, detail=f"No existe activo con Id {id_activo}")
    sesion.delete(a)
    sesion.commit()
    return {"mensaje": "Activo eliminado"}
