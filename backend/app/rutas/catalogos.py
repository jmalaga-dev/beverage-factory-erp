"""
Rutas de catalogos: las tablas maestras que alimentan los desplegables
del frontend (materias primas, trabajadores, productos, grupos, gastos
extra y cuentas). Son CRUD simples sin logica de negocio, por eso operan
directo sobre los modelos en lugar de pasar por un servicio.

Edicion / deshabilitar / borrar (mejora 6.1):
  - Editar los campos descriptivos SIEMPRE es seguro: como las relaciones
    son por Id (no por texto), renombrar un catalogo no corrompe el
    historial que lo referencia. Por eso el PATCH de edicion no lleva
    guardrail.
  - Deshabilitar (PATCH .../habilitado) saca el item de los desplegables de
    operaciones nuevas sin borrarlo; su historial queda intacto. Es la via
    recomendada para "dar de baja" algo que ya se uso (ver DECISIONES_DISENO,
    "Deshabilitar en vez de borrar").
  - Borrar (DELETE) es un borrado real y SOLO se permite si el item no tiene
    historial encima (en_uso == False); si lo tiene, se bloquea y se sugiere
    deshabilitar. Asi se respeta la inmutabilidad del historico.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.config import ROLES_CUENTA
from app.dependencias import get_sesion
from app.servicios.trabajadores import tarifa_hora
from app.models import (
    Compra,
    Cuenta,
    Gasto_Extra,
    Grupo_Movimiento,
    Materia_Prima,
    Movimiento,
    Movimiento_Deuda,
    Pago_Trabajador,
    Produccion,
    Produccion_Intermedio,
    Producto_Intermedio,
    Producto_Terminado,
    Prorrateo_Mensual,
    Registro_Trabajador,
    Trabajador,
)

router = APIRouter(tags=["catalogos"])


# =========================================================
# HELPERS COMPARTIDOS
# =========================================================

class HabilitadoEntrada(BaseModel):
    habilitado: bool


def _ids_referenciados(sesion: Session, *columnas) -> set:
    """Union de los Ids que aparecen en una o mas columnas FK. De una sola
    pasada nos dice que items de un catalogo ya tienen historial encima (y
    por tanto no se pueden borrar, solo deshabilitar)."""
    usados = set()
    for col in columnas:
        for (valor,) in sesion.query(col).distinct():
            if valor is not None:
                usados.add(valor)
    return usados


def _toggle_habilitado(sesion, modelo, campo, id_valor, habilitado, etiqueta):
    """Activa/desactiva un item de catalogo. Deshabilitado deja de aparecer
    en los desplegables de operaciones nuevas (el frontend filtra), pero
    sigue existiendo y su historial queda intacto."""
    obj = sesion.get(modelo, id_valor)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"No existe {etiqueta} con Id {id_valor}")
    setattr(obj, campo, habilitado)
    sesion.commit()
    return {"mensaje": f"{etiqueta} actualizado", "habilitado": habilitado}


def _borrar(sesion, modelo, id_valor, etiqueta, en_uso, detalle_uso):
    """Borrado real, solo si el item no tiene historial (en_uso False).
    Si lo tiene, se bloquea y se sugiere deshabilitar."""
    obj = sesion.get(modelo, id_valor)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"No existe {etiqueta} con Id {id_valor}")
    if en_uso:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede borrar: {detalle_uso}. Deshabilítalo en su lugar para sacarlo de los desplegables sin perder el historial.",
        )
    sesion.delete(obj)
    sesion.commit()
    return {"mensaje": f"{etiqueta} eliminado"}


# =========================================================
# CUENTAS
# =========================================================

def _cuentas_en_uso(sesion: Session) -> set:
    """Una cuenta esta 'en uso' si algun movimiento (de caja o de deuda) la
    referencia. El saldo != 0 se evalua aparte, por cuenta, en cada uso."""
    return _ids_referenciados(
        sesion,
        Movimiento.Id_Cuenta_Origen,
        Movimiento.Id_Cuenta_Destino,
        Movimiento_Deuda.Id_Cuenta_Pago,
    )


@router.get("/cuentas")
def listar_cuentas(sesion: Session = Depends(get_sesion)):
    """Devuelve las cuentas con su saldo actual."""
    cuentas = sesion.query(Cuenta).all()
    usados = _cuentas_en_uso(sesion)
    return [
        {
            "id_cuenta": c.Id_Cuenta,
            "nombre": c.Nombre_Cuenta,
            "saldo": float(c.Saldo_Actual_Cuenta),
            "rol": c.Rol_Cuenta,
            "habilitado": c.Habilitado_Cuenta,
            # No se puede borrar si tiene movimientos o si le queda saldo.
            "en_uso": (c.Id_Cuenta in usados) or (c.Saldo_Actual_Cuenta != 0),
        }
        for c in cuentas
    ]


class CuentaEntrada(BaseModel):
    nombre: str
    rol: str


@router.post("/cuentas")
def crear_cuenta(datos: CuentaEntrada, sesion: Session = Depends(get_sesion)):
    """Crea una cuenta nueva, con saldo en 0 (mejora 10.10: antes no habia
    forma de crear una cuenta desde la app -- si se vaciaba la base, quedaba
    sin cuentas y sin poder recuperarlas). Para cargarle saldo inicial, se usa
    Transferencias > Ingreso externo (asi el saldo sigue derivandose SIEMPRE
    de movimientos, ninguna excepcion)."""
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if datos.rol not in ROLES_CUENTA:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {datos.rol}")
    existente = sesion.query(Cuenta).filter(Cuenta.Nombre_Cuenta.ilike(datos.nombre.strip())).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese nombre")
    # FABRICA y CASA son roles unicos: el reparto 70/30 y el reparto por
    # prioridad exigen exactamente una cuenta habilitada de cada uno.
    if datos.rol in ("FABRICA", "CASA"):
        ya_hay = sesion.query(Cuenta).filter(
            Cuenta.Rol_Cuenta == datos.rol, Cuenta.Habilitado_Cuenta.is_(True)
        ).first()
        if ya_hay:
            raise HTTPException(
                status_code=400,
                detail=f"Ya hay una cuenta habilitada con rol {datos.rol} ({ya_hay.Nombre_Cuenta}). "
                       f"Debe haber exactamente una: deshabilítala o cámbiale el rol antes de crear otra.",
            )
    c = Cuenta(Nombre_Cuenta=datos.nombre.strip(), Rol_Cuenta=datos.rol, Saldo_Actual_Cuenta=0)
    sesion.add(c)
    sesion.commit()
    return {"mensaje": "Cuenta creada", "id": c.Id_Cuenta}


class CuentaEdicion(BaseModel):
    nombre: str
    rol: str | None = None


@router.patch("/cuentas/{id_cuenta}")
def actualizar_cuenta(id_cuenta: int, datos: CuentaEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige el nombre y/o el rol de una cuenta. El saldo NO se edita a mano:
    se deriva de los movimientos (principio del libro de movimientos unico)."""
    c = sesion.get(Cuenta, id_cuenta)
    if c is None:
        raise HTTPException(status_code=404, detail=f"No existe cuenta con Id {id_cuenta}")
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
    existente = sesion.query(Cuenta).filter(
        Cuenta.Nombre_Cuenta.ilike(datos.nombre.strip()), Cuenta.Id_Cuenta != id_cuenta
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe otra cuenta con ese nombre")
    if datos.rol is not None:
        if datos.rol not in ROLES_CUENTA:
            raise HTTPException(status_code=400, detail=f"Rol inválido: {datos.rol}")
        c.Rol_Cuenta = datos.rol
    c.Nombre_Cuenta = datos.nombre.strip()
    sesion.commit()
    return {"mensaje": "Cuenta actualizada", "id": c.Id_Cuenta}


@router.patch("/cuentas/{id_cuenta}/habilitado")
def cambiar_habilitado_cuenta(id_cuenta: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Cuenta, "Habilitado_Cuenta", id_cuenta, datos.habilitado, "cuenta")


@router.delete("/cuentas/{id_cuenta}")
def borrar_cuenta(id_cuenta: int, sesion: Session = Depends(get_sesion)):
    c = sesion.get(Cuenta, id_cuenta)
    if c is None:
        raise HTTPException(status_code=404, detail=f"No existe cuenta con Id {id_cuenta}")
    tiene_mov = c.Id_Cuenta in _cuentas_en_uso(sesion)
    tiene_saldo = c.Saldo_Actual_Cuenta != 0
    en_uso = tiene_mov or tiene_saldo
    motivo = "tiene movimientos registrados" if tiene_mov else "tiene saldo distinto de cero"
    return _borrar(sesion, Cuenta, id_cuenta, "cuenta", en_uso, motivo)


# ---------- MATERIA PRIMA ----------

@router.get("/materias-primas")
def listar_materias_primas(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de materias primas (el catalogo)."""
    materias = sesion.query(Materia_Prima).all()
    usados = _ids_referenciados(sesion, Compra.Id_Materia_Prima)
    return [
        {
            "id_materia_prima": m.Id_Materia_Prima,
            "descripcion": m.Descripcion_Materia_Prima,
            "unidad": m.Unidad_Materia_Prima,
            "habilitado": m.Habilitado_Materia_Prima,
            "en_uso": m.Id_Materia_Prima in usados,
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


class MateriaPrimaEdicion(BaseModel):
    descripcion: str | None = None
    unidad: str | None = None


@router.patch("/materias-primas/{id_materia_prima}")
def actualizar_materia_prima(id_materia_prima: int, datos: MateriaPrimaEdicion, sesion: Session = Depends(get_sesion)):
    m = sesion.get(Materia_Prima, id_materia_prima)
    if m is None:
        raise HTTPException(status_code=404, detail=f"No existe materia prima con Id {id_materia_prima}")
    if datos.descripcion is not None:
        if not datos.descripcion.strip():
            raise HTTPException(status_code=400, detail="La descripción no puede quedar vacía")
        m.Descripcion_Materia_Prima = datos.descripcion.strip()
    if datos.unidad is not None:
        if not datos.unidad.strip():
            raise HTTPException(status_code=400, detail="La unidad no puede quedar vacía")
        m.Unidad_Materia_Prima = datos.unidad.strip()
    sesion.commit()
    return {"mensaje": "Materia prima actualizada", "id": m.Id_Materia_Prima}


@router.patch("/materias-primas/{id_materia_prima}/habilitado")
def cambiar_habilitado_materia_prima(id_materia_prima: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Materia_Prima, "Habilitado_Materia_Prima", id_materia_prima, datos.habilitado, "materia prima")


@router.delete("/materias-primas/{id_materia_prima}")
def borrar_materia_prima(id_materia_prima: int, sesion: Session = Depends(get_sesion)):
    en_uso = sesion.query(Compra).filter(Compra.Id_Materia_Prima == id_materia_prima).first() is not None
    return _borrar(sesion, Materia_Prima, id_materia_prima, "materia prima", en_uso, "tiene compras registradas")


# ---------- TRABAJADOR ----------

@router.get("/trabajadores")
def listar_trabajadores(sesion: Session = Depends(get_sesion)):
    ts = sesion.query(Trabajador).all()
    usados = _ids_referenciados(
        sesion, Registro_Trabajador.Id_Trabajador, Pago_Trabajador.Id_Trabajador
    )
    return [
        {
            "id_trabajador": t.Id_Trabajador,
            "nombre": t.Nombre_Trabajador,
            "pago": float(t.Pago_Trabajador or 0),
            "horas_base": float(t.Horas_Base_Trabajador or 0),
            "tarifa": round(float(tarifa_hora(t)), 4),
            "habilitado": t.Habilitado_Trabajador,
            "en_uso": t.Id_Trabajador in usados,
        }
        for t in ts
    ]


class TrabajadorEntrada(BaseModel):
    nombre: str
    pago: Decimal
    horas_base: Decimal | None = None
    habilitado: bool = True


@router.post("/trabajadores")
def crear_trabajador(datos: TrabajadorEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    t = Trabajador(Nombre_Trabajador=datos.nombre, Pago_Trabajador=datos.pago,
                   Horas_Base_Trabajador=datos.horas_base or None,
                   Habilitado_Trabajador=datos.habilitado)
    sesion.add(t)
    sesion.commit()
    return {"mensaje": "Trabajador creado", "id": t.Id_Trabajador}


class TrabajadorEdicion(BaseModel):
    nombre: str | None = None
    pago: Decimal | None = None
    horas_base: Decimal | None = None


@router.patch("/trabajadores/{id_trabajador}")
def actualizar_trabajador(id_trabajador: int, datos: TrabajadorEdicion, sesion: Session = Depends(get_sesion)):
    """Corrige nombre/tarifa/horas base. Cambiar la tarifa solo afecta las
    producciones FUTURAS: el costo de las ya hechas quedo congelado con la
    tarifa pactada de ese momento (Camino 1, ver DECISIONES_DISENO)."""
    t = sesion.get(Trabajador, id_trabajador)
    if t is None:
        raise HTTPException(status_code=404, detail=f"No existe trabajador con Id {id_trabajador}")
    if datos.nombre is not None:
        if not datos.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
        t.Nombre_Trabajador = datos.nombre.strip()
    if datos.pago is not None:
        t.Pago_Trabajador = datos.pago
    if datos.horas_base is not None:
        t.Horas_Base_Trabajador = datos.horas_base
    sesion.commit()
    return {"mensaje": "Trabajador actualizado", "id": t.Id_Trabajador}


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


@router.delete("/trabajadores/{id_trabajador}")
def borrar_trabajador(id_trabajador: int, sesion: Session = Depends(get_sesion)):
    en_uso = (
        sesion.query(Registro_Trabajador).filter(Registro_Trabajador.Id_Trabajador == id_trabajador).first() is not None
        or sesion.query(Pago_Trabajador).filter(Pago_Trabajador.Id_Trabajador == id_trabajador).first() is not None
    )
    return _borrar(sesion, Trabajador, id_trabajador, "trabajador", en_uso, "tiene jornadas o pagos registrados")


# ---------- PRODUCTO TERMINADO ----------

@router.get("/productos-terminados")
def listar_productos_terminados(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Terminado).all()
    usados = _ids_referenciados(sesion, Produccion.Id_Producto_Terminado)
    return [
        {
            "id_producto_terminado": p.Id_Producto_Terminado,
            "descripcion": p.Descripcion_Producto_Terminado,
            "precio_recomendado": float(p.Precio_Venta_Recomendado_Producto_Terminado or 0),
            "botellas_por_paquete": p.Botellas_Por_Paquete,
            "habilitado": p.Habilitado_Producto_Terminado,
            "en_uso": p.Id_Producto_Terminado in usados,
        }
        for p in ps
    ]


class ProductoTerminadoEntrada(BaseModel):
    descripcion: str
    precio_recomendado: Decimal | None = None
    botellas_por_paquete: int | None = None

    @field_validator("botellas_por_paquete")
    @classmethod
    def _validar_botellas_por_paquete(cls, v):
        if v is not None and v < 1:
            raise ValueError("Botellas por paquete debe ser al menos 1")
        return v


@router.post("/productos-terminados")
def crear_producto_terminado(datos: ProductoTerminadoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Terminado(Descripcion_Producto_Terminado=datos.descripcion,
                           Precio_Venta_Recomendado_Producto_Terminado=datos.precio_recomendado or None,
                           Botellas_Por_Paquete=datos.botellas_por_paquete or 1)
    sesion.add(p)
    sesion.commit()
    return {"mensaje": "Producto terminado creado", "id": p.Id_Producto_Terminado}


class ProductoTerminadoEdicion(BaseModel):
    descripcion: str | None = None
    precio_recomendado: Decimal | None = None
    botellas_por_paquete: int | None = None

    @field_validator("botellas_por_paquete")
    @classmethod
    def _validar_botellas_por_paquete(cls, v):
        if v is not None and v < 1:
            raise ValueError("Botellas por paquete debe ser al menos 1")
        return v


@router.patch("/productos-terminados/{id_producto}")
def actualizar_producto_terminado(id_producto: int, datos: ProductoTerminadoEdicion, sesion: Session = Depends(get_sesion)):
    p = sesion.get(Producto_Terminado, id_producto)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe producto terminado con Id {id_producto}")
    if datos.descripcion is not None:
        if not datos.descripcion.strip():
            raise HTTPException(status_code=400, detail="La descripción no puede quedar vacía")
        p.Descripcion_Producto_Terminado = datos.descripcion.strip()
    if datos.precio_recomendado is not None:
        p.Precio_Venta_Recomendado_Producto_Terminado = datos.precio_recomendado
    if datos.botellas_por_paquete is not None:
        p.Botellas_Por_Paquete = datos.botellas_por_paquete
    sesion.commit()
    return {"mensaje": "Producto terminado actualizado", "id": p.Id_Producto_Terminado}


@router.patch("/productos-terminados/{id_producto}/habilitado")
def cambiar_habilitado_producto_terminado(id_producto: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Producto_Terminado, "Habilitado_Producto_Terminado", id_producto, datos.habilitado, "producto terminado")


@router.delete("/productos-terminados/{id_producto}")
def borrar_producto_terminado(id_producto: int, sesion: Session = Depends(get_sesion)):
    en_uso = sesion.query(Produccion).filter(Produccion.Id_Producto_Terminado == id_producto).first() is not None
    return _borrar(sesion, Producto_Terminado, id_producto, "producto terminado", en_uso, "tiene producciones registradas")


# ---------- PRODUCTO INTERMEDIO ----------

@router.get("/productos-intermedios")
def listar_productos_intermedios(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Intermedio).all()
    usados = _ids_referenciados(sesion, Produccion_Intermedio.Id_Producto_Intermedio)
    return [
        {
            "id_producto_intermedio": p.Id_Producto_Intermedio,
            "descripcion": p.Descripcion_Producto_Intermedio,
            "litros": float(p.Litros_Botella_Final or 0),
            "habilitado": p.Habilitado_Producto_Intermedio,
            "en_uso": p.Id_Producto_Intermedio in usados,
        }
        for p in ps
    ]


class ProductoIntermedioEntrada(BaseModel):
    descripcion: str
    litros: Decimal | None = None


@router.post("/productos-intermedios")
def crear_producto_intermedio(datos: ProductoIntermedioEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Intermedio(Descripcion_Producto_Intermedio=datos.descripcion,
                            Litros_Botella_Final=datos.litros or None)
    sesion.add(p)
    sesion.commit()
    return {"mensaje": "Producto intermedio creado", "id": p.Id_Producto_Intermedio}


class ProductoIntermedioEdicion(BaseModel):
    descripcion: str | None = None
    litros: Decimal | None = None


@router.patch("/productos-intermedios/{id_producto}")
def actualizar_producto_intermedio(id_producto: int, datos: ProductoIntermedioEdicion, sesion: Session = Depends(get_sesion)):
    p = sesion.get(Producto_Intermedio, id_producto)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe producto intermedio con Id {id_producto}")
    if datos.descripcion is not None:
        if not datos.descripcion.strip():
            raise HTTPException(status_code=400, detail="La descripción no puede quedar vacía")
        p.Descripcion_Producto_Intermedio = datos.descripcion.strip()
    if datos.litros is not None:
        p.Litros_Botella_Final = datos.litros
    sesion.commit()
    return {"mensaje": "Producto intermedio actualizado", "id": p.Id_Producto_Intermedio}


@router.patch("/productos-intermedios/{id_producto}/habilitado")
def cambiar_habilitado_producto_intermedio(id_producto: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Producto_Intermedio, "Habilitado_Producto_Intermedio", id_producto, datos.habilitado, "producto intermedio")


@router.delete("/productos-intermedios/{id_producto}")
def borrar_producto_intermedio(id_producto: int, sesion: Session = Depends(get_sesion)):
    en_uso = sesion.query(Produccion_Intermedio).filter(Produccion_Intermedio.Id_Producto_Intermedio == id_producto).first() is not None
    return _borrar(sesion, Producto_Intermedio, id_producto, "producto intermedio", en_uso, "tiene producciones registradas")


# ---------- GRUPO DE MOVIMIENTO ----------

@router.get("/grupos")
def listar_grupos(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Grupo_Movimiento).all()
    usados = _ids_referenciados(sesion, Movimiento.Id_Grupo_Movimiento)
    return [
        {
            "id_grupo": g.Id_Grupo_Movimiento,
            "nombre": g.Nombre_Grupo_Movimiento,
            "habilitado": g.Habilitado_Grupo_Movimiento,
            "en_uso": g.Id_Grupo_Movimiento in usados,
        }
        for g in gs
    ]


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


class GrupoEdicion(BaseModel):
    nombre: str


@router.patch("/grupos/{id_grupo}")
def actualizar_grupo(id_grupo: int, datos: GrupoEdicion, sesion: Session = Depends(get_sesion)):
    g = sesion.get(Grupo_Movimiento, id_grupo)
    if g is None:
        raise HTTPException(status_code=404, detail=f"No existe grupo con Id {id_grupo}")
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
    existente = sesion.query(Grupo_Movimiento).filter(
        Grupo_Movimiento.Nombre_Grupo_Movimiento.ilike(datos.nombre.strip()),
        Grupo_Movimiento.Id_Grupo_Movimiento != id_grupo,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe otro grupo con ese nombre")
    g.Nombre_Grupo_Movimiento = datos.nombre.strip()
    sesion.commit()
    return {"mensaje": "Grupo actualizado", "id": g.Id_Grupo_Movimiento}


@router.patch("/grupos/{id_grupo}/habilitado")
def cambiar_habilitado_grupo(id_grupo: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Grupo_Movimiento, "Habilitado_Grupo_Movimiento", id_grupo, datos.habilitado, "grupo")


@router.delete("/grupos/{id_grupo}")
def borrar_grupo(id_grupo: int, sesion: Session = Depends(get_sesion)):
    en_uso = sesion.query(Movimiento).filter(Movimiento.Id_Grupo_Movimiento == id_grupo).first() is not None
    return _borrar(sesion, Grupo_Movimiento, id_grupo, "grupo", en_uso, "tiene movimientos asociados")


# ---------- GASTO EXTRA ----------

@router.get("/gastos-extra")
def listar_gastos_extra(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Gasto_Extra).all()
    usados = _ids_referenciados(sesion, Prorrateo_Mensual.Id_Gasto_Extra)
    return [
        {
            "id_gasto_extra": g.Id_Gasto_Extra,
            "descripcion": g.Descripcion_Gasto_Extra,
            "precio_mensual": float(g.Precio_Mensual_Gasto_Extra or 0),
            "habilitado": g.Habilitado_Gasto_Extra,
            "en_uso": g.Id_Gasto_Extra in usados,
        }
        for g in gs
    ]


class GastoExtraEntrada(BaseModel):
    descripcion: str
    precio_mensual: Decimal


@router.post("/gastos-extra")
def crear_gasto_extra(datos: GastoExtraEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    g = Gasto_Extra(Descripcion_Gasto_Extra=datos.descripcion, Precio_Mensual_Gasto_Extra=datos.precio_mensual)
    sesion.add(g)
    sesion.commit()
    return {"mensaje": "Gasto extra creado", "id": g.Id_Gasto_Extra}


class GastoExtraEdicion(BaseModel):
    descripcion: str | None = None
    precio_mensual: Decimal | None = None


@router.patch("/gastos-extra/{id_gasto}")
def actualizar_gasto_extra(id_gasto: int, datos: GastoExtraEdicion, sesion: Session = Depends(get_sesion)):
    g = sesion.get(Gasto_Extra, id_gasto)
    if g is None:
        raise HTTPException(status_code=404, detail=f"No existe gasto extra con Id {id_gasto}")
    if datos.descripcion is not None:
        if not datos.descripcion.strip():
            raise HTTPException(status_code=400, detail="La descripción no puede quedar vacía")
        g.Descripcion_Gasto_Extra = datos.descripcion.strip()
    if datos.precio_mensual is not None:
        g.Precio_Mensual_Gasto_Extra = datos.precio_mensual
    sesion.commit()
    return {"mensaje": "Gasto extra actualizado", "id": g.Id_Gasto_Extra}


@router.patch("/gastos-extra/{id_gasto}/habilitado")
def cambiar_habilitado_gasto_extra(id_gasto: int, datos: HabilitadoEntrada, sesion: Session = Depends(get_sesion)):
    return _toggle_habilitado(sesion, Gasto_Extra, "Habilitado_Gasto_Extra", id_gasto, datos.habilitado, "gasto extra")


@router.delete("/gastos-extra/{id_gasto}")
def borrar_gasto_extra(id_gasto: int, sesion: Session = Depends(get_sesion)):
    en_uso = sesion.query(Prorrateo_Mensual).filter(Prorrateo_Mensual.Id_Gasto_Extra == id_gasto).first() is not None
    return _borrar(sesion, Gasto_Extra, id_gasto, "gasto extra", en_uso, "ya se uso en un prorrateo")
