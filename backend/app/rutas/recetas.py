"""
Rutas de pre-recetas de produccion intermedia (mejora 3.6): CRUD de recetas
y "aplicar" (escala + resuelve por FIFO para pre-llenar la produccion).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Receta, Receta_Detalle, Producto_Intermedio, Producto_Terminado, Materia_Prima
from app.servicios.recetas import aplicar_receta

router = APIRouter(tags=["recetas"])


def _serializar(sesion, r):
    detalles = []
    for d in sesion.query(Receta_Detalle).filter(Receta_Detalle.Id_Receta == r.Id_Receta).all():
        if d.Tipo_Insumo_Receta == "MP":
            mp = sesion.get(Materia_Prima, d.Id_Materia_Prima)
            nombre = mp.Descripcion_Materia_Prima if mp else "?"
            id_insumo = d.Id_Materia_Prima
        else:
            pi = sesion.get(Producto_Intermedio, d.Id_Producto_Intermedio)
            nombre = pi.Descripcion_Producto_Intermedio if pi else "?"
            id_insumo = d.Id_Producto_Intermedio
        detalles.append({
            "tipo": d.Tipo_Insumo_Receta,
            "id_insumo": id_insumo,
            "nombre": nombre,
            "cantidad": float(d.Cantidad_Receta),
        })
    # Solo el terminado tiene paquete: su rendimiento esta en botellas, y con
    # Botellas_Por_Paquete del catalogo el frontend muestra el equivalente en
    # paquetes ("rinde 56 botellas ~ 7 paquetes"). El intermedio no se empaqueta.
    botellas_por_paquete = None
    if r.Tipo_Receta == "TERMINADO":
        pt = sesion.get(Producto_Terminado, r.Id_Producto_Terminado)
        nombre_prod = pt.Descripcion_Producto_Terminado if pt else "?"
        id_producto = r.Id_Producto_Terminado
        botellas_por_paquete = pt.Botellas_Por_Paquete if pt else None
    else:
        pi = sesion.get(Producto_Intermedio, r.Id_Producto_Intermedio)
        nombre_prod = pi.Descripcion_Producto_Intermedio if pi else "?"
        id_producto = r.Id_Producto_Intermedio
    return {
        "id_receta": r.Id_Receta,
        "tipo": r.Tipo_Receta,
        "id_producto": id_producto,
        "producto": nombre_prod,
        "nombre": r.Nombre_Receta,
        "rendimiento": float(r.Rendimiento_Receta),
        "botellas_por_paquete": botellas_por_paquete,
        "habilitado": r.Habilitado_Receta,
        "detalles": detalles,
    }


@router.get("/recetas")
def listar_recetas(sesion: Session = Depends(get_sesion)):
    return [_serializar(sesion, r) for r in sesion.query(Receta).all()]


class DetalleEntrada(BaseModel):
    tipo: str          # MP / INTERMEDIO
    id_insumo: int
    cantidad: Decimal


class RecetaEntrada(BaseModel):
    tipo: str = "INTERMEDIO"   # INTERMEDIO / TERMINADO
    id_producto: int           # id del intermedio o terminado, segun tipo
    nombre: str | None = None
    rendimiento: Decimal
    detalles: list[DetalleEntrada]


def _validar_receta(sesion, datos: "RecetaEntrada"):
    if datos.tipo not in ("INTERMEDIO", "TERMINADO"):
        raise HTTPException(status_code=400, detail=f"Tipo de receta inválido: {datos.tipo}")
    if datos.tipo == "TERMINADO":
        if sesion.get(Producto_Terminado, datos.id_producto) is None:
            raise HTTPException(status_code=400, detail=f"No existe producto terminado con Id {datos.id_producto}")
    else:
        if sesion.get(Producto_Intermedio, datos.id_producto) is None:
            raise HTTPException(status_code=400, detail=f"No existe producto intermedio con Id {datos.id_producto}")
    if datos.rendimiento <= 0:
        raise HTTPException(status_code=400, detail="El rendimiento debe ser mayor a cero")
    if not datos.detalles:
        raise HTTPException(status_code=400, detail="La receta debe tener al menos un insumo")
    for d in datos.detalles:
        if d.tipo not in ("MP", "INTERMEDIO"):
            raise HTTPException(status_code=400, detail=f"Tipo de insumo inválido: {d.tipo}")
        if d.cantidad <= 0:
            raise HTTPException(status_code=400, detail="Cada insumo debe tener cantidad mayor a cero")
        if d.tipo == "MP" and sesion.get(Materia_Prima, d.id_insumo) is None:
            raise HTTPException(status_code=400, detail=f"No existe materia prima con Id {d.id_insumo}")
        if d.tipo == "INTERMEDIO" and sesion.get(Producto_Intermedio, d.id_insumo) is None:
            raise HTTPException(status_code=400, detail=f"No existe producto intermedio con Id {d.id_insumo}")


def _guardar_detalles(sesion, id_receta, detalles):
    # Fusionar insumos repetidos (mismo tipo + id) sumando su cantidad, para
    # no guardar la misma materia/intermedio en varias filas.
    fusionado = {}   # (tipo, id) -> cantidad
    orden = []
    for d in detalles:
        clave = (d.tipo, d.id_insumo)
        if clave not in fusionado:
            fusionado[clave] = 0
            orden.append(clave)
        fusionado[clave] += d.cantidad
    for (tipo, id_insumo) in orden:
        sesion.add(Receta_Detalle(
            Id_Receta=id_receta,
            Tipo_Insumo_Receta=tipo,
            Id_Materia_Prima=id_insumo if tipo == "MP" else None,
            Id_Producto_Intermedio=id_insumo if tipo == "INTERMEDIO" else None,
            Cantidad_Receta=fusionado[(tipo, id_insumo)],
        ))


def _aplicar_producto(r, datos):
    """Setea el producto de salida (intermedio o terminado) segun el tipo."""
    r.Tipo_Receta = datos.tipo
    if datos.tipo == "TERMINADO":
        r.Id_Producto_Terminado = datos.id_producto
        r.Id_Producto_Intermedio = None
    else:
        r.Id_Producto_Intermedio = datos.id_producto
        r.Id_Producto_Terminado = None


@router.post("/recetas")
def crear_receta(datos: RecetaEntrada, sesion: Session = Depends(get_sesion)):
    _validar_receta(sesion, datos)
    r = Receta(Nombre_Receta=(datos.nombre or None), Rendimiento_Receta=datos.rendimiento)
    _aplicar_producto(r, datos)
    sesion.add(r)
    sesion.flush()
    _guardar_detalles(sesion, r.Id_Receta, datos.detalles)
    sesion.commit()
    return {"mensaje": "Receta creada", "id": r.Id_Receta}


@router.patch("/recetas/{id_receta}")
def actualizar_receta(id_receta: int, datos: RecetaEntrada, sesion: Session = Depends(get_sesion)):
    """Reemplaza la receta completa (cabecera + detalles). Editar una receta
    no afecta producciones ya hechas (guardaron sus insumos reales)."""
    r = sesion.get(Receta, id_receta)
    if r is None:
        raise HTTPException(status_code=404, detail=f"No existe receta con Id {id_receta}")
    _validar_receta(sesion, datos)
    _aplicar_producto(r, datos)
    r.Nombre_Receta = datos.nombre or None
    r.Rendimiento_Receta = datos.rendimiento
    sesion.query(Receta_Detalle).filter(Receta_Detalle.Id_Receta == id_receta).delete()
    _guardar_detalles(sesion, id_receta, datos.detalles)
    sesion.commit()
    return {"mensaje": "Receta actualizada", "id": id_receta}


class HabilitadoEntrada(BaseModel):
    habilitado: bool


@router.patch("/recetas/{id_receta}/habilitado")
def cambiar_habilitado_receta(id_receta: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    r = sesion.get(Receta, id_receta)
    if r is None:
        raise HTTPException(status_code=404, detail=f"No existe receta con Id {id_receta}")
    r.Habilitado_Receta = datos.habilitado
    sesion.commit()
    return {"mensaje": "Receta actualizada", "habilitado": r.Habilitado_Receta}


@router.delete("/recetas/{id_receta}")
def borrar_receta(id_receta: int, sesion: Session = Depends(get_sesion)):
    """Borra la receta y sus detalles. Es seguro: una receta es solo una
    plantilla, no tiene historial que dependa de ella (las producciones
    guardan sus insumos reales, no una referencia a la receta)."""
    r = sesion.get(Receta, id_receta)
    if r is None:
        raise HTTPException(status_code=404, detail=f"No existe receta con Id {id_receta}")
    sesion.query(Receta_Detalle).filter(Receta_Detalle.Id_Receta == id_receta).delete()
    sesion.delete(r)
    sesion.commit()
    return {"mensaje": "Receta eliminada"}


@router.get("/recetas/{id_receta}/aplicar")
def aplicar(id_receta: int, cantidad: Decimal = Query(...), sesion: Session = Depends(get_sesion)):
    """Escala la receta a 'cantidad' y resuelve los lotes por FIFO."""
    try:
        return aplicar_receta(sesion, id_receta, cantidad)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
