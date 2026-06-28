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

from app.models import Cliente, Cuenta, Materia_Prima, Compra, Producto_Terminado, Produccion

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
            fecha=datos.fecha,
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
    """Devuelve los lotes de producto terminado con stock disponible (para vender)."""
    lotes = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > 0
    ).all()
    return [
        {
            "id_produccion": p.Id_Produccion,
            "id_producto": p.Id_Producto_Terminado,
            "stock": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
        }
        for p in lotes
    ]

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
            fecha=datos.fecha,
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
            fecha=datos.fecha,
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


@app.post("/ventas")
def crear_venta(datos: VentaEntrada, sesion: Session = Depends(get_sesion)):
    """Registra una venta con varias lineas de producto."""
    try:
        # Convertir cada linea a los tipos que espera el servicio (Decimal)
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
            fecha=datos.fecha,
        )
        return {
            "mensaje": "Venta registrada",
            "id_venta": venta.Id_Venta,
            "lineas": len(lineas),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

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
            fecha=datos.fecha,
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
            fecha=datos.fecha,
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
            fecha=datos.fecha,
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
            fecha=datos.fecha,
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