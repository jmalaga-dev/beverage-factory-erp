"""
main.py
Punto de entrada de la API de Fabrica V2 (FastAPI).
"""

from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.compras import registrar_compra

from decimal import Decimal

from app.models import Cliente, Cuenta, Materia_Prima, Compra, Producto_Terminado, Produccion, Venta

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Fabrica V2 API",
    description="API de gestion para la fabrica de bebidas",
    version="1.0.0",
)

# Permitir que el frontend (que corre en otro puerto) pueda pedir datos a esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],   # permite GET, POST, etc.
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def error_bd(request: Request, exc: SQLAlchemyError):
    # Muestra solo una linea corta en la terminal, no el traceback gigante
    print(f"ERROR BD en {request.url.path}: {str(exc)[:200]}")
    return JSONResponse(status_code=500, content={"detail": "Error de base de datos"})


@app.get("/")
def inicio():
    return {"mensaje": "API de Fabrica V2 funcionando"}


# ---------- ESQUEMA: el molde de datos que espera el endpoint de compra ----------

class CompraEntrada(BaseModel):
    id_materia_prima: int
    id_cuenta: int
    cantidad: float
    precio_total: float
    fecha: date | None = None


# ---------- ENDPOINT: registrar una compra ----------

from datetime import date   # asegúrate de tener este import arriba

@app.post("/compras")
def crear_compra(datos: CompraEntrada, sesion: Session = Depends(get_sesion)):
    """
    Registra una compra de materia prima.
    Recibe los datos validados por Pydantic, llama al servicio, y devuelve
    la compra creada o un error si algo falla.
    """
    try:
        compra = registrar_compra(
            sesion,
            id_materia_prima=datos.id_materia_prima,
            id_cuenta=datos.id_cuenta,
            cantidad=Decimal(str(datos.cantidad)),
            precio_total=Decimal(str(datos.precio_total)),
            fecha=datos.fecha or date.today(),   # si no vino fecha, usa hoy
        )
        return {
            "mensaje": "Compra registrada",
            "id_compra": compra.Id_Compra,
            "cantidad_restante": float(compra.Cantidad_Restante_Compra),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# ---------- ENDPOINTS GET: consultas de lectura ----------

@app.get("/clientes")
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


@app.get("/cuentas")
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


@app.get("/materias-primas")
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


@app.get("/lotes-producto-terminado")
def listar_lotes_pt(sesion: Session = Depends(get_sesion)):
    """Lotes de producto terminado con stock, nombre del producto, costo y precio recomendado."""
    lotes = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > 0
    ).all()
    resultado = []
    for p in lotes:
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        resultado.append({
            "id_produccion": p.Id_Produccion,
            "id_producto": p.Id_Producto_Terminado,
            "nombre_producto": producto.Descripcion_Producto_Terminado if producto else "?",
            "stock": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
            "precio_recomendado": float(producto.Precio_Venta_Recomendado_Producto_Terminado or 0) if producto else 0,
        })
    return resultado

from app.servicios.gastos import registrar_gasto


class GastoEntrada(BaseModel):
    id_cuenta: int
    monto: float
    descripcion: str
    id_grupo: int | None = None
    fecha: date | None = None


@app.post("/gastos")
def crear_gasto(datos: GastoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra un gasto que sale de una cuenta."""
    try:
        mov = registrar_gasto(
            sesion,
            id_cuenta=datos.id_cuenta,
            monto=Decimal(str(datos.monto)),
            descripcion=datos.descripcion,
            id_grupo=datos.id_grupo,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Gasto registrado",
            "id_movimiento": mov.Id_Movimiento,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

from app.servicios.pagos import calcular_pago_sugerido, registrar_pago_semanal


@app.get("/trabajadores/{id_trabajador}/pago-sugerido")
def ver_pago_sugerido(id_trabajador: int, sesion: Session = Depends(get_sesion)):
    """Calcula cuanto se le debe a un trabajador (horas pendientes x tarifa)."""
    try:
        sugerido, pendientes = calcular_pago_sugerido(sesion, id_trabajador)
        return {
            "id_trabajador": id_trabajador,
            "monto_sugerido": float(sugerido),
            "jornadas_pendientes": len(pendientes),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PagoEntrada(BaseModel):
    id_trabajador: int
    id_cuenta: int
    monto_real: float
    fecha: date | None = None


@app.post("/pagos")
def crear_pago(datos: PagoEntrada, sesion: Session = Depends(get_sesion)):
    """Registra el pago semanal a un trabajador."""
    try:
        pago = registrar_pago_semanal(
            sesion,
            id_trabajador=datos.id_trabajador,
            id_cuenta=datos.id_cuenta,
            monto_real=Decimal(str(datos.monto_real)),
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Pago registrado",
            "id_pago": pago.Id_Pago_Trabajador,
            "sugerido": float(pago.Monto_Sugerido_Pago),
            "real": float(pago.Monto_Real_Pago),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

from app.servicios.ventas import registrar_venta


# Esquema de UNA linea de venta
class LineaVentaEntrada(BaseModel):
    id_produccion: int
    cantidad: float
    precio_real: float
    id_cuenta: int


# Esquema de la venta completa: cabecera + lista de lineas
class VentaEntrada(BaseModel):
    id_cliente: int
    lineas: list[LineaVentaEntrada]
    fecha: date | None = None


# Asegúrate que el POST /ventas ponga fecha de hoy:
@app.post("/ventas")
def crear_venta(datos: VentaEntrada, sesion: Session = Depends(get_sesion)):
    try:
        lineas = [
            {
                "id_produccion": linea.id_produccion,
                "cantidad": Decimal(str(linea.cantidad)),
                "precio_real": Decimal(str(linea.precio_real)),
                "id_cuenta": linea.id_cuenta,
            }
            for linea in datos.lineas
        ]
        venta = registrar_venta(
            sesion,
            id_cliente=datos.id_cliente,
            lineas=lineas,
            fecha=datos.fecha or date.today(),   # hoy si no viene
        )
        return {"mensaje": "Venta registrada", "id_venta": venta.Id_Venta, "lineas": len(lineas)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# GET para listar ventas registradas
@app.get("/ventas")
def listar_ventas(sesion: Session = Depends(get_sesion)):
    from app.models import Detalle_Venta
    ventas = sesion.query(Venta).all()
    resultado = []
    for v in ventas:
        cliente = sesion.get(Cliente, v.Id_Cliente)
        detalles = sesion.query(Detalle_Venta).filter_by(Id_Venta=v.Id_Venta).all()
        total = sum(float(d.Cantidad_Venta) * float(d.Precio_Venta_Real) for d in detalles)
        resultado.append({
            "id_venta": v.Id_Venta,
            "cliente": cliente.Nombre_Cliente if cliente else "?",
            "fecha": str(v.Fecha_Venta),
            "lineas": len(detalles),
            "total": round(total, 2),
        })
    return resultado
    

from app.servicios.trabajadores import registrar_jornada
from app.servicios.clientes import crear_sector, registrar_cliente
from app.servicios.produccion_intermedia import producir_intermedio
from app.servicios.produccion_terminado import producir_terminado
from app.servicios.inventario import registrar_movimiento_inventario
from app.servicios.prorrateo import calcular_prorrateo_mensual
from app.servicios.balance import tomar_balance


class JornadaEntrada(BaseModel):
    id_trabajador: int
    horas: float
    fecha: date | None = None


@app.post("/jornadas")
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
    

class SectorEntrada(BaseModel):
    nombre: str


@app.post("/sectores")
def crear_sector_endpoint(datos: SectorEntrada, sesion: Session = Depends(get_sesion)):
    """Crea un sector (zona) validado."""
    try:
        sector = crear_sector(sesion, datos.nombre)
        return {"mensaje": "Sector listo", "id_sector": sector.Id_Sector, "nombre": sector.Nombre_Sector}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ClienteEntrada(BaseModel):
    nombre: str
    apellido: str | None = None
    celular: str | None = None
    licoreria: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    id_sector: int | None = None


@app.post("/clientes")
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
    

class ProduccionIntermediaEntrada(BaseModel):
    id_producto_intermedio: int
    cantidad_producida: float
    insumos_mp: list[tuple[int, float]] = []          # [(id_compra, cantidad), ...]
    insumos_trabajo: list[tuple[int, float]] = []     # [(id_registro, horas), ...]
    insumos_intermedio: list[tuple[int, float]] = []  # [(id_prod_int, cantidad), ...]
    fecha: date | None = None


@app.post("/producciones-intermedias")
def crear_produccion_intermedia(datos: ProduccionIntermediaEntrada, sesion: Session = Depends(get_sesion)):
    """Produce un producto intermedio consumiendo lotes de insumos."""
    try:
        # Convertir las cantidades a Decimal dentro de cada tupla
        mp = [(i, Decimal(str(c))) for i, c in datos.insumos_mp]
        trabajo = [(i, Decimal(str(h))) for i, h in datos.insumos_trabajo]
        intermedio = [(i, Decimal(str(c))) for i, c in datos.insumos_intermedio]

        prod = producir_intermedio(
            sesion,
            id_producto_intermedio=datos.id_producto_intermedio,
            cantidad_producida=Decimal(str(datos.cantidad_producida)),
            insumos_mp=mp,
            insumos_trabajo=trabajo,
            insumos_intermedio=intermedio,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Produccion intermedia creada",
            "id_produccion_intermedio": prod.Id_Produccion_Intermedio,
            "costo_unitario": float(prod.Costo_Unitario_Produccion_Intermedio),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

class ProduccionTerminadoEntrada(BaseModel):
    id_producto_terminado: int
    cantidad_producida: float
    insumos_intermedio: list[tuple[int, float]] = []
    insumos_mp: list[tuple[int, float]] = []
    insumos_trabajo: list[tuple[int, float]] = []
    fecha: date | None = None


@app.post("/producciones-terminadas")
def crear_produccion_terminada(datos: ProduccionTerminadoEntrada, sesion: Session = Depends(get_sesion)):
    """Produce un producto terminado consumiendo intermedios, MP y trabajo."""
    try:
        intermedio = [(i, Decimal(str(c))) for i, c in datos.insumos_intermedio]
        mp = [(i, Decimal(str(c))) for i, c in datos.insumos_mp]
        trabajo = [(i, Decimal(str(h))) for i, h in datos.insumos_trabajo]

        prod = producir_terminado(
            sesion,
            id_producto_terminado=datos.id_producto_terminado,
            cantidad_producida=Decimal(str(datos.cantidad_producida)),
            insumos_intermedio=intermedio,
            insumos_mp=mp,
            insumos_trabajo=trabajo,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Produccion terminada creada",
            "id_produccion": prod.Id_Produccion,
            "costo_unitario": float(prod.Precio_Unitario_Producto_Terminado),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

class MovimientoInventarioEntrada(BaseModel):
    tipo: str        # MERMA, AJUSTE, DEVOLUCION, REPROCESO
    sentido: str     # SALIDA, ENTRADA
    origen_lote: str # COMPRA, PRODUCCION, PRODUCCION_INTERMEDIO
    cantidad: float
    motivo: str | None = None
    id_compra: int | None = None
    id_produccion: int | None = None
    id_prod_intermedio: int | None = None
    fecha: date | None = None


@app.post("/movimientos-inventario")
def crear_movimiento_inventario(datos: MovimientoInventarioEntrada, sesion: Session = Depends(get_sesion)):
    """Registra una merma, ajuste, devolucion o reproceso sobre un lote."""
    try:
        mov = registrar_movimiento_inventario(
            sesion,
            tipo=datos.tipo,
            sentido=datos.sentido,
            origen_lote=datos.origen_lote,
            cantidad=Decimal(str(datos.cantidad)),
            motivo=datos.motivo,
            id_compra=datos.id_compra,
            id_produccion=datos.id_produccion,
            id_prod_intermedio=datos.id_prod_intermedio,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Movimiento de inventario registrado", "id": mov.Id_Movimiento_Inventario}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

class ProrrateoEntrada(BaseModel):
    anio_mes: str   # ej "2026-06"


@app.post("/prorrateos")
def crear_prorrateo(datos: ProrrateoEntrada, sesion: Session = Depends(get_sesion)):
    """Reparte los gastos extra del mes entre los productos segun horas."""
    try:
        creados = calcular_prorrateo_mensual(sesion, datos.anio_mes)
        return {"mensaje": "Prorrateo calculado", "asignaciones": len(creados)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class BalanceEntrada(BaseModel):
    fecha_balance: date | None = None
    dias_semana: int = 7


@app.post("/balances")
def crear_balance(datos: BalanceEntrada, sesion: Session = Depends(get_sesion)):
    """Toma una foto del balance actual de la fabrica."""
    try:
        balance = tomar_balance(sesion, fecha_balance=datos.fecha_balance, dias_semana=datos.dias_semana)
        return {
            "mensaje": "Balance tomado",
            "id_balance": balance.Id_Balance,
            "patrimonio": float(balance.Patrimonio),
            "escenario_c": float(balance.Escenario_C),
            "escenario_b": float(balance.Escenario_B),
            "escenario_a": float(balance.Escenario_A),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
from app.models import Sector

@app.get("/sectores")
def listar_sectores(sesion: Session = Depends(get_sesion)):
    """Devuelve la lista de sectores (para el desplegable)."""
    sectores = sesion.query(Sector).all()
    return [
        {"id_sector": s.Id_Sector, "nombre": s.Nombre_Sector}
        for s in sectores
    ]

from sqlalchemy import func

@app.get("/stock-materia-prima")
def stock_materia_prima(sesion: Session = Depends(get_sesion)):
    """Stock general de materia prima: suma el restante de todos los lotes por cada materia."""
    filas = (
        sesion.query(
            Materia_Prima.Id_Materia_Prima,
            Materia_Prima.Descripcion_Materia_Prima,
            Materia_Prima.Unidad_Materia_Prima,
            func.coalesce(func.sum(Compra.Cantidad_Restante_Compra), 0).label("total"),
        )
        .outerjoin(Compra, Compra.Id_Materia_Prima == Materia_Prima.Id_Materia_Prima)
        .group_by(
            Materia_Prima.Id_Materia_Prima,
            Materia_Prima.Descripcion_Materia_Prima,
            Materia_Prima.Unidad_Materia_Prima,
        )
        .all()
    )
    return [
        {
            "id_materia_prima": f.Id_Materia_Prima,
            "descripcion": f.Descripcion_Materia_Prima,
            "unidad": f.Unidad_Materia_Prima,
            "stock_total": float(f.total),
        }
        for f in filas
    ]

@app.get("/lotes-compra")
def listar_lotes_compra(sesion: Session = Depends(get_sesion)):
    """Lotes de compra con stock, incluyendo el nombre de la materia prima."""
    lotes = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > 0).all()
    resultado = []
    for c in lotes:
        mp = sesion.get(Materia_Prima, c.Id_Materia_Prima)
        resultado.append({
            "id_compra": c.Id_Compra,
            "id_materia_prima": c.Id_Materia_Prima,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "cantidad_restante": float(c.Cantidad_Restante_Compra),
            "precio_compra": float(c.Precio_Compra),
            "cantidad_compra": float(c.Cantidad_Compra),
        })
    return resultado

from app.models import Trabajador, Producto_Terminado, Producto_Intermedio, Grupo_Movimiento, Gasto_Extra

# ---------- MATERIA PRIMA ----------
@app.get("/materias-primas")  # (ya lo tienes, verifica que exista)
def listar_materias_primas(sesion: Session = Depends(get_sesion)):
    ms = sesion.query(Materia_Prima).all()
    return [{"id_materia_prima": m.Id_Materia_Prima, "descripcion": m.Descripcion_Materia_Prima, "unidad": m.Unidad_Materia_Prima} for m in ms]

class MateriaPrimaEntrada(BaseModel):
    descripcion: str
    unidad: str

@app.post("/materias-primas")
def crear_materia_prima(datos: MateriaPrimaEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    m = Materia_Prima(Descripcion_Materia_Prima=datos.descripcion, Unidad_Materia_Prima=datos.unidad)
    sesion.add(m); sesion.commit()
    return {"mensaje": "Materia prima creada", "id": m.Id_Materia_Prima}

# ---------- TRABAJADOR ----------
@app.get("/trabajadores")
def listar_trabajadores(sesion: Session = Depends(get_sesion)):
    ts = sesion.query(Trabajador).all()
    return [{"id_trabajador": t.Id_Trabajador, "nombre": t.Nombre_Trabajador, "pago": float(t.Pago_Trabajador or 0), "horas_base": float(t.Horas_Base_Trabajador or 0)} for t in ts]

class TrabajadorEntrada(BaseModel):
    nombre: str
    pago: float
    horas_base: float | None = None

@app.post("/trabajadores")
def crear_trabajador(datos: TrabajadorEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    t = Trabajador(Nombre_Trabajador=datos.nombre, Pago_Trabajador=Decimal(str(datos.pago)),
                   Horas_Base_Trabajador=Decimal(str(datos.horas_base)) if datos.horas_base else None)
    sesion.add(t); sesion.commit()
    return {"mensaje": "Trabajador creado", "id": t.Id_Trabajador}

# ---------- PRODUCTO TERMINADO ----------
@app.get("/productos-terminados")
def listar_productos_terminados(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Terminado).all()
    return [{"id_producto_terminado": p.Id_Producto_Terminado, "descripcion": p.Descripcion_Producto_Terminado, "precio_recomendado": float(p.Precio_Venta_Recomendado_Producto_Terminado or 0)} for p in ps]

class ProductoTerminadoEntrada(BaseModel):
    descripcion: str
    precio_recomendado: float | None = None

@app.post("/productos-terminados")
def crear_producto_terminado(datos: ProductoTerminadoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Terminado(Descripcion_Producto_Terminado=datos.descripcion,
                           Precio_Venta_Recomendado_Producto_Terminado=Decimal(str(datos.precio_recomendado)) if datos.precio_recomendado else None)
    sesion.add(p); sesion.commit()
    return {"mensaje": "Producto terminado creado", "id": p.Id_Producto_Terminado}

# ---------- PRODUCTO INTERMEDIO ----------
@app.get("/productos-intermedios")
def listar_productos_intermedios(sesion: Session = Depends(get_sesion)):
    ps = sesion.query(Producto_Intermedio).all()
    return [{"id_producto_intermedio": p.Id_Producto_Intermedio, "descripcion": p.Descripcion_Producto_Intermedio, "litros": float(p.Litros_Botella_Final or 0)} for p in ps]

class ProductoIntermedioEntrada(BaseModel):
    descripcion: str
    litros: float | None = None

@app.post("/productos-intermedios")
def crear_producto_intermedio(datos: ProductoIntermedioEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    p = Producto_Intermedio(Descripcion_Producto_Intermedio=datos.descripcion,
                            Litros_Botella_Final=Decimal(str(datos.litros)) if datos.litros else None)
    sesion.add(p); sesion.commit()
    return {"mensaje": "Producto intermedio creado", "id": p.Id_Producto_Intermedio}

# ---------- GRUPO DE MOVIMIENTO ----------
@app.get("/grupos")
def listar_grupos(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Grupo_Movimiento).all()
    return [{"id_grupo": g.Id_Grupo_Movimiento, "nombre": g.Nombre_Grupo_Movimiento} for g in gs]

class GrupoEntrada(BaseModel):
    nombre: str

@app.post("/grupos")
def crear_grupo(datos: GrupoEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    existente = sesion.query(Grupo_Movimiento).filter(Grupo_Movimiento.Nombre_Grupo_Movimiento.ilike(datos.nombre.strip())).first()
    if existente:
        return {"mensaje": "Ya existía", "id": existente.Id_Grupo_Movimiento}
    g = Grupo_Movimiento(Nombre_Grupo_Movimiento=datos.nombre.strip())
    sesion.add(g); sesion.commit()
    return {"mensaje": "Grupo creado", "id": g.Id_Grupo_Movimiento}

# ---------- GASTO EXTRA ----------
@app.get("/gastos-extra")
def listar_gastos_extra(sesion: Session = Depends(get_sesion)):
    gs = sesion.query(Gasto_Extra).all()
    return [{"id_gasto_extra": g.Id_Gasto_Extra, "descripcion": g.Descripcion_Gasto_Extra, "precio_mensual": float(g.Precio_Mensual_Gasto_Extra or 0)} for g in gs]

class GastoExtraEntrada(BaseModel):
    descripcion: str
    precio_mensual: float

@app.post("/gastos-extra")
def crear_gasto_extra(datos: GastoExtraEntrada, sesion: Session = Depends(get_sesion)):
    if not datos.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria")
    g = Gasto_Extra(Descripcion_Gasto_Extra=datos.descripcion, Precio_Mensual_Gasto_Extra=Decimal(str(datos.precio_mensual)))
    sesion.add(g); sesion.commit()
    return {"mensaje": "Gasto extra creado", "id": g.Id_Gasto_Extra}

from app.models import Registro_Trabajador

@app.get("/jornadas")
def listar_jornadas(sesion: Session = Depends(get_sesion)):
    jornadas = sesion.query(Registro_Trabajador).all()
    resultado = []
    for j in jornadas:
        trabajador = sesion.get(Trabajador, j.Id_Trabajador)
        resultado.append({
            "id_jornada": j.Id_Registro_Trabajador,
            "id_trabajador": j.Id_Trabajador,
            "nombre_trabajador": trabajador.Nombre_Trabajador if trabajador else "?",
            "fecha": str(j.Fecha_Registro_Trabajador),
            "horas": float(j.Horas_Registro_Trabajador),
            "horas_restantes": float(j.Horas_Restante_Registro_Trabajador or 0),  # NUEVO
            "pagada": j.Id_Pago_Trabajador is not None,
        })
    return resultado


from app.models import Produccion_Intermedio
from app.models import Producto_Intermedio 

@app.get("/producciones-intermedias")
def listar_producciones_intermedias(sesion: Session = Depends(get_sesion)):
    """Lotes de producción intermedia con su stock restante y costo."""
    prods = sesion.query(Produccion_Intermedio).filter(
        Produccion_Intermedio.Cantidad_Restante_Producida > 0
    ).all()
    resultado = []
    for p in prods:
        producto = sesion.get(Producto_Intermedio, p.Id_Producto_Intermedio)
        resultado.append({
            "id_produccion_intermedio": p.Id_Produccion_Intermedio,
            "descripcion": producto.Descripcion_Producto_Intermedio if producto else "?",
            "cantidad_restante": float(p.Cantidad_Restante_Producida),
            "costo_unitario": float(p.Costo_Unitario_Produccion_Intermedio or 0),
        })
    return resultado

@app.get("/stock-intermedio-general")
def stock_intermedio_general(sesion: Session = Depends(get_sesion)):
    """Stock consolidado de producto intermedio: suma todos los lotes por producto,
    con costo unitario promedio ponderado (prorrateado) de lo que queda."""
    prods = sesion.query(Produccion_Intermedio).filter(
        Produccion_Intermedio.Cantidad_Restante_Producida > 0
    ).all()

    # Agrupar por producto intermedio
    resumen = {}
    for p in prods:
        pid = p.Id_Producto_Intermedio
        if pid not in resumen:
            producto = sesion.get(Producto_Intermedio, pid)
            resumen[pid] = {
                "descripcion": producto.Descripcion_Producto_Intermedio if producto else "?",
                "stock_total": 0,
                "valor_total": 0,   # para el promedio ponderado
            }
        cant = float(p.Cantidad_Restante_Producida)
        costo = float(p.Costo_Unitario_Produccion_Intermedio or 0)
        resumen[pid]["stock_total"] += cant
        resumen[pid]["valor_total"] += cant * costo   # cantidad x su costo

    # Armar la respuesta con el costo promedio ponderado
    resultado = []
    for pid, datos in resumen.items():
        stock = datos["stock_total"]
        costo_prom = datos["valor_total"] / stock if stock > 0 else 0
        resultado.append({
            "id_producto_intermedio": pid,
            "descripcion": datos["descripcion"],
            "stock_total": stock,
            "costo_promedio": round(costo_prom, 4),
        })
    return resultado

# GET: lotes de produccion terminada con stock (por lote)
@app.get("/producciones-terminadas")
def listar_producciones_terminadas(sesion: Session = Depends(get_sesion)):
    """Lotes de producto terminado con stock, para la tabla por lote."""
    prods = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > 0
    ).all()
    resultado = []
    for p in prods:
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        resultado.append({
            "id_produccion": p.Id_Produccion,
            "descripcion": producto.Descripcion_Producto_Terminado if producto else "?",
            "cantidad_restante": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
        })
    return resultado


# GET: stock consolidado de producto terminado (general, con promedio ponderado)
@app.get("/stock-terminado-general")
def stock_terminado_general(sesion: Session = Depends(get_sesion)):
    """Stock consolidado de producto terminado: suma lotes por producto, costo promedio ponderado."""
    prods = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > 0
    ).all()
    resumen = {}
    for p in prods:
        pid = p.Id_Producto_Terminado
        if pid not in resumen:
            producto = sesion.get(Producto_Terminado, pid)
            resumen[pid] = {"descripcion": producto.Descripcion_Producto_Terminado if producto else "?",
                            "stock_total": 0, "valor_total": 0}
        cant = float(p.Cantidad_Restante_Produccion)
        costo = float(p.Precio_Unitario_Producto_Terminado or 0)
        resumen[pid]["stock_total"] += cant
        resumen[pid]["valor_total"] += cant * costo
    resultado = []
    for pid, d in resumen.items():
        stock = d["stock_total"]
        resultado.append({
            "id_producto_terminado": pid,
            "descripcion": d["descripcion"],
            "stock_total": stock,
            "costo_promedio": round(d["valor_total"] / stock, 4) if stock > 0 else 0,
        })
    return resultado

@app.post("/pagos")
def crear_pago(datos: PagoEntrada, sesion: Session = Depends(get_sesion)):
    try:
        pago = registrar_pago_semanal(
            sesion,
            id_trabajador=datos.id_trabajador,
            id_cuenta=datos.id_cuenta,
            monto_real=Decimal(str(datos.monto_real)),
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Pago registrado", "id_pago": pago.Id_Pago_Trabajador,
                "sugerido": float(pago.Monto_Sugerido_Pago), "real": float(pago.Monto_Real_Pago)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.post("/gastos")
def crear_gasto(datos: GastoEntrada, sesion: Session = Depends(get_sesion)):
    try:
        mov = registrar_gasto(
            sesion,
            id_cuenta=datos.id_cuenta,
            monto=Decimal(str(datos.monto)),
            descripcion=datos.descripcion,
            id_grupo=datos.id_grupo,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Gasto registrado", "id_movimiento": mov.Id_Movimiento}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.post("/movimientos-inventario")
def crear_movimiento_inventario(datos: MovimientoInventarioEntrada, sesion: Session = Depends(get_sesion)):
    try:
        mov = registrar_movimiento_inventario(
            sesion,
            tipo=datos.tipo, sentido=datos.sentido, origen_lote=datos.origen_lote,
            cantidad=Decimal(str(datos.cantidad)), motivo=datos.motivo,
            id_compra=datos.id_compra, id_produccion=datos.id_produccion,
            id_prod_intermedio=datos.id_prod_intermedio,
            fecha=datos.fecha or date.today(),
        )
        return {"mensaje": "Movimiento registrado", "id": mov.Id_Movimiento_Inventario}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
from app.models import Horas_Producto_Mes

@app.get("/horas-producto-mes/{anio_mes}")
def ver_horas_producto_mes(anio_mes: str, sesion: Session = Depends(get_sesion)):
    """Qué productos usaron la fábrica ese mes y cuántas horas cada uno."""
    filas = sesion.query(Horas_Producto_Mes).filter_by(Anio_Mes=anio_mes).all()
    resultado = []
    total = 0
    for f in filas:
        producto = sesion.get(Producto_Terminado, f.Id_Producto_Terminado)
        horas = float(f.Horas_Producto_Mes)
        total += horas
        resultado.append({
            "producto": producto.Descripcion_Producto_Terminado if producto else "?",
            "horas": horas,
        })
    return {"total_horas": total, "detalle": resultado}


@app.get("/gastos-extra-total")
def ver_gastos_extra_total(sesion: Session = Depends(get_sesion)):
    """Lista de gastos extra mensuales y su total."""
    gastos = sesion.query(Gasto_Extra).all()
    total = sum(float(g.Precio_Mensual_Gasto_Extra or 0) for g in gastos)
    detalle = [{"descripcion": g.Descripcion_Gasto_Extra, "precio": float(g.Precio_Mensual_Gasto_Extra or 0)} for g in gastos]
    return {"total": total, "detalle": detalle}

from app.models import Balance

# GET: estado ACTUAL sin guardar (vista previa con desglose)
@app.get("/balance-actual")
def balance_actual(sesion: Session = Depends(get_sesion)):
    """Calcula el estado actual con desglose completo, SIN guardar la foto."""
    from sqlalchemy import func
    from app.models import Deuda

    # Efectivo: suma de saldos de cuentas
    efectivo = sesion.query(func.coalesce(func.sum(Cuenta.Saldo_Actual_Cuenta), 0)).scalar()

    # Stock materia prima valorizado
    compras = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > 0).all()
    stock_mp = sum(float(c.Cantidad_Restante_Compra) * (float(c.Precio_Compra) / float(c.Cantidad_Compra)) for c in compras)

    # Stock de producto INTERMEDIO valorizado (a su costo unitario)
    from app.models import Produccion_Intermedio
    prods_int = sesion.query(Produccion_Intermedio).filter(Produccion_Intermedio.Cantidad_Restante_Producida > 0).all()
    stock_int = sum(float(p.Cantidad_Restante_Producida) * float(p.Costo_Unitario_Produccion_Intermedio or 0) for p in prods_int)

    # Horas de trabajo en stand-by (pagadas/registradas pero no consumidas)
    from app.models import Registro_Trabajador, Trabajador
    jornadas = sesion.query(Registro_Trabajador).filter(Registro_Trabajador.Horas_Restante_Registro_Trabajador > 0).all()
    valor_horas = 0
    for j in jornadas:
        trab = sesion.get(Trabajador, j.Id_Trabajador)
        valor_horas += float(j.Horas_Restante_Registro_Trabajador) * float(trab.Pago_Trabajador or 0) if trab else 0

    # Stock producto terminado valorizado (a precio recomendado)
    producciones = sesion.query(Produccion).filter(Produccion.Cantidad_Restante_Produccion > 0).all()
    stock_pt = 0
    for p in producciones:
        prod = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        precio = float(prod.Precio_Venta_Recomendado_Producto_Terminado or 0) if prod else 0
        stock_pt += float(p.Cantidad_Restante_Produccion) * precio

    # Deudas
    deudas = sesion.query(func.coalesce(func.sum(Deuda.Saldo_Actual_Deuda), 0)).scalar()

    efectivo = float(efectivo); deudas = float(deudas)
    escenario_c = efectivo - deudas
    escenario_b = efectivo + stock_mp + stock_int + stock_pt + valor_horas - deudas
    escenario_a = escenario_b  # sin activos fijos por ahora (se suman si los hay)

    return {
        "efectivo": round(efectivo, 2),
        "stock_materia_prima": round(stock_mp, 2),
        "stock_producto_terminado": round(stock_pt, 2),
        "deudas": round(deudas, 2),
        "escenario_c": round(escenario_c, 2),
        "escenario_b": round(escenario_b, 2),
        "escenario_a": round(escenario_a, 2),
        "patrimonio": round(escenario_a, 2),
        "stock_producto_intermedio": round(stock_int, 2),
        "valor_horas_standby": round(valor_horas, 2),
    }


# GET: última foto guardada
@app.get("/balance-ultimo")
def balance_ultimo(sesion: Session = Depends(get_sesion)):
    """Devuelve la última foto de balance guardada, con desglose."""
    ultimo = sesion.query(Balance).order_by(Balance.Id_Balance.desc()).first()
    if ultimo is None:
        return None
    return {
        "id_balance": ultimo.Id_Balance,
        "fecha": str(ultimo.Fecha_Balance),
        "efectivo": float(ultimo.Total_Efectivo or 0),
        "stock_materia_prima": float(ultimo.Valor_Stock_Materia_Prima or 0),
        "stock_producto_intermedio": float(ultimo.Valor_Stock_Intermedio or 0),
        "valor_horas_standby": float(ultimo.Valor_Horas_Standby or 0),
        "stock_producto_terminado": float(ultimo.Valor_Stock_Producto_Terminado or 0),
        "deudas": float(ultimo.Total_Deudas or 0),
        "escenario_c": float(ultimo.Escenario_C or 0),
        "escenario_b": float(ultimo.Escenario_B or 0),
        "escenario_a": float(ultimo.Escenario_A or 0),
        "patrimonio": float(ultimo.Patrimonio or 0),
    }