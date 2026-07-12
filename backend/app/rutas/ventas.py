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


# Esquema de UNA linea de venta
class LineaVentaEntrada(BaseModel):
    id_produccion: int
    cantidad: Decimal
    precio_real: Decimal
    id_cuenta: int


# Esquema de la venta completa: cabecera + lista de lineas
class VentaEntrada(BaseModel):
    id_cliente: int
    lineas: list[LineaVentaEntrada]
    fecha: date | None = None


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
        )
        return {"mensaje": "Venta registrada", "id_venta": venta.Id_Venta, "lineas": len(lineas)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ventas")
def listar_ventas(sesion: Session = Depends(get_sesion)):
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
    return {
        "id_venta": venta.Id_Venta,
        "cliente": cliente.Nombre_Cliente if cliente else "?",
        "fecha": str(venta.Fecha_Venta),
        "lineas": lineas,
    }
