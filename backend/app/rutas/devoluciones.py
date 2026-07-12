"""
Rutas de devolucion y reproceso (mejora 3.3).

- POST /devoluciones: devolucion completa (reembolso + destino del producto).
- POST /reprocesos: reproceso directo de un lote (sin devolucion de por medio,
  ej. se rompio la tapa de unas botellas en el deposito).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencias import get_sesion
from app.servicios.devoluciones import registrar_devolucion
from app.servicios.reproceso import reprocesar

router = APIRouter(tags=["devoluciones"])


class ReprocesoDatos(BaseModel):
    cantidad_producida: Decimal
    insumos_mp: list[tuple[int, Decimal]] = []
    insumos_trabajo: list[tuple[int, Decimal]] = []


class DevolucionEntrada(BaseModel):
    id_produccion: int
    cantidad: Decimal
    id_cuenta: int
    monto_reembolso: Decimal
    destino: str  # STOCK / MERMA / REPROCESO
    id_venta: int | None = None
    motivo: str | None = None
    fecha: date | None = None
    # Solo si destino=MERMA (absorcion del costo, 1.4)
    absorber_costo: bool = True
    botellas_estimadas_absorcion: Decimal | None = None
    # Solo si destino=REPROCESO
    reproceso: ReprocesoDatos | None = None


@router.post("/devoluciones")
def crear_devolucion(datos: DevolucionEntrada, sesion: Session = Depends(get_sesion)):
    """Registra una devolucion completa (reembolso + destino del producto)."""
    try:
        reproceso = None
        if datos.reproceso is not None:
            reproceso = {
                "cantidad_producida": datos.reproceso.cantidad_producida,
                "insumos_mp": [tuple(x) for x in datos.reproceso.insumos_mp],
                "insumos_trabajo": [tuple(x) for x in datos.reproceso.insumos_trabajo],
            }
        resultado = registrar_devolucion(
            sesion,
            id_produccion=datos.id_produccion,
            cantidad=datos.cantidad,
            id_cuenta=datos.id_cuenta,
            monto_reembolso=datos.monto_reembolso,
            destino=datos.destino.upper(),
            id_venta=datos.id_venta,
            motivo=datos.motivo,
            fecha=datos.fecha or date.today(),
            absorber_costo=datos.absorber_costo,
            botellas_estimadas_absorcion=datos.botellas_estimadas_absorcion,
            reproceso=reproceso,
        )
        return {"mensaje": "Devolucion registrada", **resultado}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ReprocesoEntrada(BaseModel):
    id_produccion_origen: int
    cantidad: Decimal
    cantidad_producida: Decimal
    insumos_mp: list[tuple[int, Decimal]] = []
    insumos_trabajo: list[tuple[int, Decimal]] = []
    motivo: str | None = None
    fecha: date | None = None


@router.post("/reprocesos")
def crear_reproceso(datos: ReprocesoEntrada, sesion: Session = Depends(get_sesion)):
    """Reprocesa un lote de producto terminado en un lote nuevo (sin devolucion)."""
    try:
        nuevo = reprocesar(
            sesion,
            id_produccion_origen=datos.id_produccion_origen,
            cantidad=datos.cantidad,
            cantidad_producida=datos.cantidad_producida,
            insumos_mp=[tuple(x) for x in datos.insumos_mp],
            insumos_trabajo=[tuple(x) for x in datos.insumos_trabajo],
            motivo=datos.motivo,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Reproceso registrado",
            "id_produccion_nuevo": nuevo.Id_Produccion,
            "costo_unitario": float(nuevo.Precio_Unitario_Producto_Terminado),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
