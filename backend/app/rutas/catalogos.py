"""
Rutas de catalogos: las tablas maestras que alimentan los desplegables
del frontend (materias primas, trabajadores, productos, grupos, gastos
extra y cuentas). Son CRUD simples sin logica de negocio, por eso operan
directo sobre los modelos en lugar de pasar por un servicio.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import (
    Cuenta,
    Gasto_Extra,
    Grupo_Movimiento,
    Materia_Prima,
    Producto_Intermedio,
    Producto_Terminado,
    Trabajador,
)

router = APIRouter(tags=["catalogos"])


# ---------- CUENTAS ----------

@router.get("/cuentas")
def listar_cuentas(sesion: Session = Depends(get_sesion)):
    """Devuelve las cuentas con su saldo actual."""
    cuentas = sesion.query(Cuenta).all()
    return [
        {
            "id_cuenta": c.Id_Cuenta,
            "nombre": c.Nombre_Cuenta,
            "saldo": float(c.Saldo_Actual_Cuenta),
        }
        for c in cuentas
    ]


# ---------- MATERIA PRIMA ----------

@router.get("/materias-primas")
def listar_materias_primas(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de materias primas (el catalogo)."""
    materias = sesion.query(Materia_Prima).all()
    return [
        {
            "id_materia_prima": m.Id_Materia_Prima,
            "descripcion": m.Descripcion_Materia_Prima,
            "unidad": m.Unidad_Materia_Prima,
        }
        for m in materias
    ]


class MateriaPrimaEntrada(BaseModel):
    descripcion: str
    unidad: str


@router.post("/materias-primas")
def crear_materia_prima(datos: MateriaPrimaEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    m = Materia_Prima(Descripcion_Materia_Prima=datos.descripcion, Unidad_Materia_Prima=datos.unidad)
    sesion.add(m)
    sesion.commit()
    return {"mensaje": "Materia prima creada", "id": m.Id_Materia_Prima}


# ---------- TRABAJADOR ----------

@router.get("/trabajadores")
def listar_trabajadores(sesion: Session = Depends(get_sesion)):
    ts = sesion.query(Trabajador).all()
    return [
        {
            "id_trabajador": t.Id_Trabajador,
            "nombre": t.Nombre_Trabajador,
            "pago": float(t.Pago_Trabajador or 0),
            "horas_base": float(t.Horas_Base_Trabajador or 0),
            "habilitado": t.Habilitado_Trabajador,
        }
        for t in ts
    ]


class TrabajadorEntrada(BaseModel):
    nombre: str
    pago: float
    horas_base: float | None = None
    habilitado: bool = True


@router.post("/trabajadores")
def crear_trabajador(datos: TrabajadorEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    t = Trabajador(Nombre_Trabajador=datos.nombre, Pago_Trabajador=Decimal(str(datos.pago)),
                   Horas_Base_Trabajador=Decimal(str(datos.horas_base)) if datos.horas_base else None,
                   Habilitado_Trabajador=datos.habilitado)
    sesion.add(t)
    sesion.commit()
    return {"mensaje": "Trabajador creado", "id": t.Id_Trabajador}


class TrabajadorHabilitadoEntrada(BaseModel):
    habilitado: bool


@router.patch("/trabajadores/{id_trabajador}/habilitado")
def cambiar_habilitado_trabajador(id_trabajador: int, datos: TrabajadorHabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    """Activa/desactiva un trabajador (no aparece en desplegables si esta deshabilitado)."""
    t = sesion.get(Trabajador, id_trabajador)
    if t is None:
        raise HTTPException(status_code=404, detail=f"No existe trabajador con Id {id_trabajador}")
    t.Habilitado_Trabajador = datos.habilitado
    sesion.commit()
    return {"mensaje": "Trabajador actualizado", "id": t.Id_Trabajador, "habilitado": t.Habilitado_Trabajador}


# ---------- PRODUCTO TERMINADO ----------

@router.get("/productos-terminados")
def listar_productos_terminados(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Terminado).all()
    return [
        {
            "id_producto_terminado": p.Id_Producto_Terminado,
            "descripcion": p.Descripcion_Producto_Terminado,
            "precio_recomendado": float(p.Precio_Venta_Recomendado_Producto_Terminado or 0),
        }
        for p in ps
    ]


class ProductoTerminadoEntrada(BaseModel):
    descripcion: str
    precio_recomendado: float | None = None


@router.post("/productos-terminados")
def crear_producto_terminado(datos: ProductoTerminadoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Terminado(Descripcion_Producto_Terminado=datos.descripcion,
                           Precio_Venta_Recomendado_Producto_Terminado=Decimal(str(datos.precio_recomendado)) if datos.precio_recomendado else None)
    sesion.add(p)
    sesion.commit()
    return {"mensaje": "Producto terminado creado", "id": p.Id_Producto_Terminado}


# ---------- PRODUCTO INTERMEDIO ----------

@router.get("/productos-intermedios")
def listar_productos_intermedios(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Intermedio).all()
    return [
        {
            "id_producto_intermedio": p.Id_Producto_Intermedio,
            "descripcion": p.Descripcion_Producto_Intermedio,
            "litros": float(p.Litros_Botella_Final or 0),
        }
        for p in ps
    ]


class ProductoIntermedioEntrada(BaseModel):
    descripcion: str
    litros: float | None = None


@router.post("/productos-intermedios")
def crear_producto_intermedio(datos: ProductoIntermedioEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Intermedio(Descripcion_Producto_Intermedio=datos.descripcion,
                            Litros_Botella_Final=Decimal(str(datos.litros)) if datos.litros else None)
    sesion.add(p)
    sesion.commit()
    return {"mensaje": "Producto intermedio creado", "id": p.Id_Producto_Intermedio}


# ---------- GRUPO DE MOVIMIENTO ----------

@router.get("/grupos")
def listar_grupos(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Grupo_Movimiento).all()
    return [{"id_grupo": g.Id_Grupo_Movimiento, "nombre": g.Nombre_Grupo_Movimiento} for g in gs]


class GrupoEntrada(BaseModel):
    nombre: str


@router.post("/grupos")
def crear_grupo(datos: GrupoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    existente = sesion.query(Grupo_Movimiento).filter(Grupo_Movimiento.Nombre_Grupo_Movimiento.ilike(datos.nombre.strip())).first()
    if existente:
        return {"mensaje": "Ya existía", "id": existente.Id_Grupo_Movimiento}
    g = Grupo_Movimiento(Nombre_Grupo_Movimiento=datos.nombre.strip())
    sesion.add(g)
    sesion.commit()
    return {"mensaje": "Grupo creado", "id": g.Id_Grupo_Movimiento}


# ---------- GASTO EXTRA ----------

@router.get("/gastos-extra")
def listar_gastos_extra(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Gasto_Extra).all()
    return [
        {
            "id_gasto_extra": g.Id_Gasto_Extra,
            "descripcion": g.Descripcion_Gasto_Extra,
            "precio_mensual": float(g.Precio_Mensual_Gasto_Extra or 0),
        }
        for g in gs
    ]


class GastoExtraEntrada(BaseModel):
    descripcion: str
    precio_mensual: float


@router.post("/gastos-extra")
def crear_gasto_extra(datos: GastoExtraEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    g = Gasto_Extra(Descripcion_Gasto_Extra=datos.descripcion, Precio_Mensual_Gasto_Extra=Decimal(str(datos.precio_mensual)))
    sesion.add(g)
    sesion.commit()
    return {"mensaje": "Gasto extra creado", "id": g.Id_Gasto_Extra}
