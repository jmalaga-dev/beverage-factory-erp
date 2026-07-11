"""
Rutas de proveedores (mejora 5.1 base).

Un proveedor se registra una vez (nombre, celular, ubicacion) y se asocia a
las materias primas que vende (tabla puente Proveedor_Materia_Prima). Al
comprar, el frontend consulta que proveedores venden esa materia prima:
si hay uno solo se autoselecciona, si hay varios se elige de una lista.

Se sigue el mismo juego de acciones que el resto de catalogos (6.1):
editar (seguro, relaciones por Id), habilitar/deshabilitar (dar de baja sin
perder historial) y borrar (solo si no tiene compras encima).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Proveedor, Proveedor_Materia_Prima, Materia_Prima, Compra

router = APIRouter(tags=["proveedores"])


def _materias_de(sesion: Session, id_proveedor: int):
    """Lista las materias primas asociadas a un proveedor, con el nombre y
    el estado (habilitado) del vinculo."""
    vinculos = (
        sesion.query(Proveedor_Materia_Prima)
        .filter(Proveedor_Materia_Prima.Id_Proveedor == id_proveedor)
        .all()
    )
    resultado = []
    for v in vinculos:
        mp = sesion.get(Materia_Prima, v.Id_Materia_Prima)
        resultado.append({
            "id_materia_prima": v.Id_Materia_Prima,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "habilitado": v.Habilitado_Proveedor_Materia_Prima,
        })
    return resultado


@router.get("/proveedores")
def listar_proveedores(sesion: Session = Depends(get_sesion)):
    proveedores = sesion.query(Proveedor).all()
    # Un proveedor "en uso" tiene compras vinculadas: no se puede borrar.
    con_compras = {
        p_id for (p_id,) in sesion.query(Compra.Id_Proveedor).filter(Compra.Id_Proveedor.isnot(None)).distinct()
    }
    return [
        {
            "id_proveedor": p.Id_Proveedor,
            "nombre": p.Nombre_Proveedor,
            "celular": p.Celular_Proveedor,
            "latitud": float(p.Latitud_Proveedor) if p.Latitud_Proveedor is not None else None,
            "longitud": float(p.Longitud_Proveedor) if p.Longitud_Proveedor is not None else None,
            "habilitado": p.Habilitado_Proveedor,
            "en_uso": p.Id_Proveedor in con_compras,
            "materias": _materias_de(sesion, p.Id_Proveedor),
        }
        for p in proveedores
    ]


@router.get("/proveedores-por-materia/{id_materia_prima}")
def proveedores_por_materia(id_materia_prima: int, sesion: Session = Depends(get_sesion)):
    """Proveedores ACTIVOS que venden una materia prima dada (proveedor
    habilitado y vinculo habilitado). Alimenta el desplegable de Compras:
    0 -> bloquear y pedir registrar proveedor; 1 -> autoseleccion; >1 -> elegir."""
    vinculos = (
        sesion.query(Proveedor_Materia_Prima)
        .filter(
            Proveedor_Materia_Prima.Id_Materia_Prima == id_materia_prima,
            Proveedor_Materia_Prima.Habilitado_Proveedor_Materia_Prima.is_(True),
        )
        .all()
    )
    resultado = []
    for v in vinculos:
        p = sesion.get(Proveedor, v.Id_Proveedor)
        if p is None or not p.Habilitado_Proveedor:
            continue
        resultado.append({"id_proveedor": p.Id_Proveedor, "nombre": p.Nombre_Proveedor})
    return resultado


class ProveedorEntrada(BaseModel):
    nombre: str
    celular: str | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None


@router.post("/proveedores")
def crear_proveedor(datos: ProveedorEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    p = Proveedor(
        Nombre_Proveedor=datos.nombre.strip(),
        Celular_Proveedor=datos.celular or None,
        Latitud_Proveedor=datos.latitud,
        Longitud_Proveedor=datos.longitud,
    )
    sesion.add(p)
    sesion.commit()
    return {"mensaje": "Proveedor creado", "id": p.Id_Proveedor}


class ProveedorEdicion(BaseModel):
    nombre: str | None = None
    celular: str | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None


@router.patch("/proveedores/{id_proveedor}")
def actualizar_proveedor(id_proveedor: int, datos: ProveedorEdicion, sesion: Session = Depends(get_sesion)):
    p = sesion.get(Proveedor, id_proveedor)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe proveedor con Id {id_proveedor}")
    if datos.nombre is not None:
        if not datos.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
        p.Nombre_Proveedor = datos.nombre.strip()
    if datos.celular is not None:
        p.Celular_Proveedor = datos.celular or None
    if datos.latitud is not None:
        p.Latitud_Proveedor = datos.latitud
    if datos.longitud is not None:
        p.Longitud_Proveedor = datos.longitud
    sesion.commit()
    return {"mensaje": "Proveedor actualizado", "id": p.Id_Proveedor}


class HabilitadoEntrada(BaseModel):
    habilitado: bool


@router.patch("/proveedores/{id_proveedor}/habilitado")
def cambiar_habilitado_proveedor(id_proveedor: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    p = sesion.get(Proveedor, id_proveedor)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe proveedor con Id {id_proveedor}")
    p.Habilitado_Proveedor = datos.habilitado
    sesion.commit()
    return {"mensaje": "Proveedor actualizado", "id": p.Id_Proveedor, "habilitado": p.Habilitado_Proveedor}


@router.delete("/proveedores/{id_proveedor}")
def borrar_proveedor(id_proveedor: int, sesion: Session = Depends(get_sesion)):
    p = sesion.get(Proveedor, id_proveedor)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe proveedor con Id {id_proveedor}")
    tiene_compras = sesion.query(Compra).filter(Compra.Id_Proveedor == id_proveedor).first() is not None
    if tiene_compras:
        raise HTTPException(
            status_code=400,
            detail="El proveedor tiene compras registradas: deshabilítalo en vez de borrarlo",
        )
    # Sin compras: borrar tambien sus vinculos a materias primas (no tienen
    # historial propio, solo declaran "vende esto").
    sesion.query(Proveedor_Materia_Prima).filter(
        Proveedor_Materia_Prima.Id_Proveedor == id_proveedor
    ).delete()
    sesion.delete(p)
    sesion.commit()
    return {"mensaje": "Proveedor eliminado"}


# ---------- MATERIAS QUE VENDE UN PROVEEDOR (tabla puente) ----------

class MateriaVinculo(BaseModel):
    id_materia_prima: int


@router.post("/proveedores/{id_proveedor}/materias")
def agregar_materia(id_proveedor: int, datos: MateriaVinculo, sesion: Session = Depends(get_sesion)):
    """Asocia una materia prima al proveedor. Si el vinculo ya existe pero
    estaba deshabilitado, lo reactiva (en vez de duplicar)."""
    if sesion.get(Proveedor, id_proveedor) is None:
        raise HTTPException(status_code=404, detail=f"No existe proveedor con Id {id_proveedor}")
    if sesion.get(Materia_Prima, datos.id_materia_prima) is None:
        raise HTTPException(status_code=400, detail=f"No existe materia prima con Id {datos.id_materia_prima}")
    vinculo = (
        sesion.query(Proveedor_Materia_Prima)
        .filter(
            Proveedor_Materia_Prima.Id_Proveedor == id_proveedor,
            Proveedor_Materia_Prima.Id_Materia_Prima == datos.id_materia_prima,
        )
        .first()
    )
    if vinculo is not None:
        vinculo.Habilitado_Proveedor_Materia_Prima = True
        sesion.commit()
        return {"mensaje": "Materia prima reactivada para el proveedor"}
    vinculo = Proveedor_Materia_Prima(
        Id_Proveedor=id_proveedor,
        Id_Materia_Prima=datos.id_materia_prima,
    )
    sesion.add(vinculo)
    sesion.commit()
    return {"mensaje": "Materia prima asociada al proveedor"}


@router.patch("/proveedores/{id_proveedor}/materias/{id_materia_prima}/habilitado")
def cambiar_habilitado_materia(id_proveedor: int, id_materia_prima: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    """Habilita/deshabilita el vinculo proveedor-materia (ej. Juan deja de
    vender azucar): no aparece en el desplegable de compra de esa materia,
    pero el historial de compras a Juan queda intacto."""
    vinculo = (
        sesion.query(Proveedor_Materia_Prima)
        .filter(
            Proveedor_Materia_Prima.Id_Proveedor == id_proveedor,
            Proveedor_Materia_Prima.Id_Materia_Prima == id_materia_prima,
        )
        .first()
    )
    if vinculo is None:
        raise HTTPException(status_code=404, detail="No existe ese vínculo proveedor-materia")
    vinculo.Habilitado_Proveedor_Materia_Prima = datos.habilitado
    sesion.commit()
    return {"mensaje": "Vínculo actualizado", "habilitado": vinculo.Habilitado_Proveedor_Materia_Prima}
