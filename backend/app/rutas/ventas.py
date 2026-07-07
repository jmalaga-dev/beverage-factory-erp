"""
Rutas de ventas: registrar una venta (cabecera + lineas) y listarlas.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.models import Cliente, Detalle_Venta, Venta
from app.servicios.ventas import registrar_venta

router = APIRouter(tags=["ventas"])


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


@router.post("/ventas")
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
