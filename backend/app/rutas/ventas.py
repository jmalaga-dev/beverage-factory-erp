"""
Rutas de ventas: registrar una venta (cabecera + lineas) y listarlas.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Cliente, Detalle_Venta, Produccion, Producto_Terminado, Venta
from app.servicios.ventas import registrar_venta

router = APIRouter(tags=["ventas"])


# Esquema de UNA linea de venta. id_cuenta solo se usa con reparto=False.
class LineaVentaEntrada(BaseModel):
    id_produccion: int
    cantidad: Decimal
    precio_real: Decimal
    id_cuenta: int | None = None


# Esquema de la venta completa: cabecera + lista de lineas
class VentaEntrada(BaseModel):
    id_cliente: int
    lineas: list[LineaVentaEntrada]
    fecha: date | None = None
    reparto: bool = True   # True = 70/30 automatico Fabrica/Casa (mejora 2.C)
    taxi: Decimal = 0      # taxi/delivery: baja el ingreso neto (item 8)


@router.post("/ventas")
def crear_venta(datos: VentaEntrada, sesion: Session = Depends(get_sesion)):
    try:
        lineas = [
            {
                "id_produccion": linea.id_produccion,
                "cantidad": linea.cantidad,
                "precio_real": linea.precio_real,
                "id_cuenta": linea.id_cuenta,
            }
            for linea in datos.lineas
        ]
        venta = registrar_venta(
            sesion,
            id_cliente=datos.id_cliente,
            lineas=lineas,
            fecha=datos.fecha or date.today(),
            reparto=datos.reparto,
            taxi=datos.taxi,
        )
        return {"mensaje": "Venta registrada", "id_venta": venta.Id_Venta, "lineas": len(lineas)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LineaPreviewReparto(BaseModel):
    id_produccion: int
    cantidad: Decimal
    precio_real: Decimal


class PreviewRepartoEntrada(BaseModel):
    lineas: list[LineaPreviewReparto]
    taxi: Decimal = 0


@router.post("/ventas/preview-reparto")
def preview_reparto_venta(datos: PreviewRepartoEntrada, sesion: Session = Depends(get_sesion)):
    """Muestra cómo se repartiría el ingreso NETO de una venta entre Fábrica y
    Casa (70/30 con recuperación de inversión), sin registrar nada. El taxi se
    prorratea uniforme por botella y baja el neto, igual que al registrar (item
    8). Acumula el saldo línea por línea."""
    from app.models import Produccion
    from app.servicios.saldo_producto import saldo_de_producto, dividir_ingreso

    lineas = datos.lineas
    total_botellas = sum(l.cantidad for l in lineas)
    taxi_por_botella = datos.taxi / total_botellas if total_botellas > 0 else 0

    saldo_por_producto = {}
    detalle = []
    total_fabrica = total_casa = 0.0
    for l in lineas:
        produccion = sesion.get(Produccion, l.id_produccion)
        if produccion is None:
            raise HTTPException(status_code=400, detail=f"No existe lote {l.id_produccion}")
        pid = produccion.Id_Producto_Terminado
        if pid not in saldo_por_producto:
            saldo_por_producto[pid] = saldo_de_producto(sesion, pid)
        ingreso = l.cantidad * (l.precio_real - taxi_por_botella)
        a_fab, a_casa = dividir_ingreso(saldo_por_producto[pid], ingreso)
        saldo_por_producto[pid] = saldo_por_producto[pid] + ingreso
        total_fabrica += float(a_fab)
        total_casa += float(a_casa)
        detalle.append({
            "id_produccion": l.id_produccion,
            "ingreso": round(float(ingreso), 2),
            "a_fabrica": round(float(a_fab), 2),
            "a_casa": round(float(a_casa), 2),
        })
    return {
        "detalle": detalle,
        "total_fabrica": round(total_fabrica, 2),
        "total_casa": round(total_casa, 2),
    }


@router.get("/ultimo-precio-cliente/{id_cliente}")
def ultimo_precio_cliente(id_cliente: int, sesion: Session = Depends(get_sesion)):
    """Último precio al que ese cliente compró cada producto terminado (mejora
    10.4). Devuelve un mapa {id_producto_terminado: precio}. El precio es por
    PRODUCTO (no por lote): la venta anterior pudo salir de otro lote. Sirve
    para predeterminar el precio de venta a ese cliente; si el producto no
    aparece, no hay historial y el frontend cae al precio sugerido."""
    filas = (
        sesion.query(
            Produccion.Id_Producto_Terminado,
            Detalle_Venta.Precio_Venta_Real,
        )
        .join(Venta, Detalle_Venta.Id_Venta == Venta.Id_Venta)
        .join(Produccion, Detalle_Venta.Id_Produccion == Produccion.Id_Produccion)
        .filter(Venta.Id_Cliente == id_cliente)
        .order_by(Venta.Fecha_Venta.asc(), Venta.Id_Venta.asc())
        .all()
    )
    # Recorriendo en orden ascendente, el último que pisa cada producto es el
    # más reciente.
    ultimo = {}
    for id_producto, precio in filas:
        ultimo[id_producto] = float(precio)
    return ultimo


@router.get("/ventas")
def listar_ventas(sesion: Session = Depends(get_sesion)):
    ventas = sesion.query(Venta).all()
    resultado = []
    for v in ventas:
        cliente = sesion.get(Cliente, v.Id_Cliente)
        detalles = sesion.query(Detalle_Venta).filter_by(Id_Venta=v.Id_Venta).all()
        # "total" es lo que REALMENTE entro (neto), no lo que pago el cliente:
        # asi el listado coincide con los movimientos de caja de esa venta, y el
        # bruto se obtiene sumando el taxi en vez de restandolo. El bruto va
        # igual, para la pantalla de devoluciones (que reembolsa lo pagado).
        bruto = sum(float(d.Cantidad_Venta) * float(d.Precio_Venta_Real) for d in detalles)
        taxi = float(v.Taxi_Venta or 0)
        resultado.append({
            "id_venta": v.Id_Venta,
            "cliente": cliente.Nombre_Cliente if cliente else "?",
            "fecha": str(v.Fecha_Venta),
            "lineas": len(detalles),
            "total": round(bruto - taxi, 2),
            "taxi": round(taxi, 2),
            "bruto": round(bruto, 2),
        })
    return resultado


@router.get("/ventas/{id_venta}")
def detalle_venta(id_venta: int, sesion: Session = Depends(get_sesion)):
    """Detalle de una venta: sus lineas con lote, producto, cantidad y precio.
    Lo usa la pantalla de Devoluciones para vincular la devolucion a la venta
    original (autocompletar el reembolso y validar la cantidad)."""
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise HTTPException(status_code=404, detail=f"No existe venta con Id {id_venta}")
    cliente = sesion.get(Cliente, venta.Id_Cliente)
    detalles = sesion.query(Detalle_Venta).filter_by(Id_Venta=id_venta).all()
    lineas = []
    for d in detalles:
        produccion = sesion.get(Produccion, d.Id_Produccion)
        producto = sesion.get(Producto_Terminado, produccion.Id_Producto_Terminado) if produccion else None
        lineas.append({
            "id_produccion": d.Id_Produccion,
            "nombre_producto": producto.Descripcion_Producto_Terminado if producto else "?",
            "cantidad": float(d.Cantidad_Venta),
            "precio_real": float(d.Precio_Venta_Real),
        })
    bruto = sum(float(d.Cantidad_Venta) * float(d.Precio_Venta_Real) for d in detalles)
    taxi = float(venta.Taxi_Venta or 0)
    return {
        "id_venta": venta.Id_Venta,
        "cliente": cliente.Nombre_Cliente if cliente else "?",
        "fecha": str(venta.Fecha_Venta),
        "lineas": lineas,
        # El precio por linea es el BRUTO (lo que pago el cliente): es lo que se
        # reembolsa en una devolucion. El taxi ya se pago al taxista, no vuelve.
        "bruto": round(bruto, 2),
        "taxi": round(taxi, 2),
        "total": round(bruto - taxi, 2),
    }
