"""
Rutas de produccion: intermedia y terminada, con sus consultas de stock
por lote y consolidado (promedio ponderado).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import UMBRAL_STOCK_MINIMO
from app.dependencias import get_sesion
from app.models import (
    Produccion,
    Produccion_Intermedio,
    Producto_Intermedio,
    Producto_Terminado,
)
from app.servicios.produccion_intermedia import producir_intermedio
from app.servicios.produccion_terminado import producir_terminado

router = APIRouter(tags=["produccion"])


# ---------- PRODUCCION INTERMEDIA ----------

class ProduccionIntermediaEntrada(BaseModel):
    id_producto_intermedio: int
    cantidad_producida: Decimal
    insumos_mp: list[tuple[int, Decimal]] = []          # [(id_compra, cantidad), ...]
    insumos_trabajo: list[tuple[int, Decimal]] = []     # [(id_registro, horas), ...]
    insumos_intermedio: list[tuple[int, Decimal]] = []  # [(id_prod_int, cantidad), ...]
    fecha: date | None = None


@router.post("/producciones-intermedias")
def crear_produccion_intermedia(datos: ProduccionIntermediaEntrada, sesion: Session = Depends(get_sesion)):
    """Produce un producto intermedio consumiendo lotes de insumos."""
    try:
        prod = producir_intermedio(
            sesion,
            id_producto_intermedio=datos.id_producto_intermedio,
            cantidad_producida=datos.cantidad_producida,
            insumos_mp=datos.insumos_mp,
            insumos_trabajo=datos.insumos_trabajo,
            insumos_intermedio=datos.insumos_intermedio,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Produccion intermedia creada",
            "id_produccion_intermedio": prod.Id_Produccion_Intermedio,
            "costo_unitario": float(prod.Costo_Unitario_Produccion_Intermedio),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/producciones-intermedias")
def listar_producciones_intermedias(sesion: Session = Depends(get_sesion)):
    """Lotes de producción intermedia con su stock restante y costo."""
    prods = sesion.query(Produccion_Intermedio).filter(
        Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO
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


@router.get("/stock-intermedio-general")
def stock_intermedio_general(sesion: Session = Depends(get_sesion)):
    """Stock consolidado de producto intermedio: suma todos los lotes por producto,
    con costo unitario promedio ponderado (prorrateado) de lo que queda."""
    prods = sesion.query(Produccion_Intermedio).filter(
        Produccion_Intermedio.Cantidad_Restante_Producida > UMBRAL_STOCK_MINIMO
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


# ---------- PRODUCCION TERMINADA ----------

class ProduccionTerminadoEntrada(BaseModel):
    id_producto_terminado: int
    cantidad_producida: Decimal
    insumos_intermedio: list[tuple[int, Decimal]] = []
    insumos_mp: list[tuple[int, Decimal]] = []
    insumos_trabajo: list[tuple[int, Decimal]] = []
    fecha: date | None = None


@router.post("/producciones-terminadas")
def crear_produccion_terminada(datos: ProduccionTerminadoEntrada, sesion: Session = Depends(get_sesion)):
    """Produce un producto terminado consumiendo intermedios, MP y trabajo."""
    try:
        prod = producir_terminado(
            sesion,
            id_producto_terminado=datos.id_producto_terminado,
            cantidad_producida=datos.cantidad_producida,
            insumos_intermedio=datos.insumos_intermedio,
            insumos_mp=datos.insumos_mp,
            insumos_trabajo=datos.insumos_trabajo,
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": "Produccion terminada creada",
            "id_produccion": prod.Id_Produccion,
            "costo_unitario": float(prod.Precio_Unitario_Producto_Terminado),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/producciones-terminadas")
def listar_producciones_terminadas(sesion: Session = Depends(get_sesion)):
    """Lotes de producto terminado con stock, para la tabla por lote."""
    prods = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO
    ).all()
    resultado = []
    for p in prods:
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        resultado.append({
            "id_produccion": p.Id_Produccion,
            "descripcion": producto.Descripcion_Producto_Terminado if producto else "?",
            "cantidad_restante": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
            "horas_acumuladas": float(p.Horas_Acumuladas or 0),
        })
    return resultado


@router.get("/lotes-producto-terminado")
def listar_lotes_pt(sesion: Session = Depends(get_sesion)):
    """Lotes de producto terminado con stock, nombre del producto, costo y precio recomendado."""
    lotes = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO
    ).all()
    resultado = []
    for p in lotes:
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        # El precio sugerido (recomendado vs costo/(1-margen)) se calcula en el
        # frontend, porque el margen es una caja editable por venta (mejora
        # 6.12): aca solo damos costo y recomendado.
        resultado.append({
            "id_produccion": p.Id_Produccion,
            "id_producto": p.Id_Producto_Terminado,
            "nombre_producto": producto.Descripcion_Producto_Terminado if producto else "?",
            "stock": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
            "precio_recomendado": float(producto.Precio_Venta_Recomendado_Producto_Terminado or 0) if producto else 0,
        })
    return resultado


@router.get("/stock-terminado-general")
def stock_terminado_general(sesion: Session = Depends(get_sesion)):
    """Stock consolidado de producto terminado: suma lotes por producto, costo promedio ponderado."""
    prods = sesion.query(Produccion).filter(
        Produccion.Cantidad_Restante_Produccion > UMBRAL_STOCK_MINIMO
    ).all()
    resumen = {}
    for p in prods:
        pid = p.Id_Producto_Terminado
        if pid not in resumen:
            producto = sesion.get(Producto_Terminado, pid)
            resumen[pid] = {
                "descripcion": producto.Descripcion_Producto_Terminado if producto else "?",
                "botellas_por_paquete": producto.Botellas_Por_Paquete if producto else 1,
                "stock_total": 0, "valor_total": 0,
            }
        cant = float(p.Cantidad_Restante_Produccion)
        costo = float(p.Precio_Unitario_Producto_Terminado or 0)
        resumen[pid]["stock_total"] += cant
        resumen[pid]["valor_total"] += cant * costo
    resultado = []
    for pid, d in resumen.items():
        stock = d["stock_total"]
        botellas_paquete = d["botellas_por_paquete"] or 1
        resultado.append({
            "id_producto_terminado": pid,
            "descripcion": d["descripcion"],
            "stock_total": stock,
            "costo_promedio": round(d["valor_total"] / stock, 4) if stock > 0 else 0,
            "botellas_por_paquete": botellas_paquete,
            "paquetes_equivalentes": round(stock / botellas_paquete, 2),
        })
    return resultado
