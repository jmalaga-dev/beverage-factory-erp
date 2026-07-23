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
    Detalle_PI_Intermedio,
    Detalle_Prod_Intermedio,
    Detalle_Venta,
    Movimiento_Inventario,
)
from app.servicios.produccion_intermedia import producir_intermedio
from app.servicios.produccion_terminado import producir_terminado
from app.servicios.eliminar_produccion import (
    eliminar_produccion_intermedia, eliminar_produccion_terminada,
)

router = APIRouter(tags=["produccion"])


def _ids_no_nulos(sesion, *columnas):
    """Union de los valores no nulos de una o mas columnas (para saber que
    lotes ya estan referenciados aguas abajo y por tanto no son eliminables)."""
    usados = set()
    for col in columnas:
        for (v,) in sesion.query(col).distinct():
            if v is not None:
                usados.add(v)
    return usados


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
    # Lotes intermedios ya referenciados aguas abajo (consumidos por otra
    # produccion o mermados): no son eliminables (item 6a).
    usados = _ids_no_nulos(
        sesion,
        Detalle_PI_Intermedio.Id_Produccion_Intermedio_Origen,
        Detalle_Prod_Intermedio.Id_Produccion_Intermedio,
        Movimiento_Inventario.Id_Produccion_Intermedio,
    )
    resultado = []
    for p in prods:
        producto = sesion.get(Producto_Intermedio, p.Id_Producto_Intermedio)
        intacta = (
            p.Cantidad_Restante_Producida == p.Cantidad_Producida
            and p.Id_Produccion_Intermedio not in usados
        )
        resultado.append({
            "id_produccion_intermedio": p.Id_Produccion_Intermedio,
            "descripcion": producto.Descripcion_Producto_Intermedio if producto else "?",
            "unidad": producto.Unidad_Producto_Intermedio if producto else None,
            "cantidad_restante": float(p.Cantidad_Restante_Producida),
            "costo_unitario": float(p.Costo_Unitario_Produccion_Intermedio or 0),
            "eliminable": intacta,
        })
    return resultado


@router.delete("/producciones-intermedias/{id_produccion_intermedio}")
def borrar_produccion_intermedia(id_produccion_intermedio: int, sesion: Session = Depends(get_sesion)):
    """Elimina una produccion intermedia intacta, devolviendo sus insumos (item 6a)."""
    try:
        return eliminar_produccion_intermedia(sesion, id_produccion_intermedio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
                "unidad": producto.Unidad_Producto_Intermedio if producto else None,
                "destacado": producto.Destacado_Producto_Intermedio if producto else False,
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
            "unidad": datos["unidad"],
            "destacado": datos["destacado"],
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
    # Lotes terminados ya referenciados aguas abajo (vendidos, mermados,
    # devueltos o reprocesados): no son eliminables (item 6a).
    usados = _ids_no_nulos(
        sesion,
        Detalle_Venta.Id_Produccion,
        Movimiento_Inventario.Id_Produccion,
        Movimiento_Inventario.Ref_Reproceso,
    )
    resultado = []
    for p in prods:
        producto = sesion.get(Producto_Terminado, p.Id_Producto_Terminado)
        intacta = (
            p.Cantidad_Restante_Produccion == p.Cantidad_Producida_Produccion
            and p.Id_Produccion not in usados
        )
        resultado.append({
            "id_produccion": p.Id_Produccion,
            "descripcion": producto.Descripcion_Producto_Terminado if producto else "?",
            "cantidad_restante": float(p.Cantidad_Restante_Produccion),
            "costo_unitario": float(p.Precio_Unitario_Producto_Terminado or 0),
            "horas_acumuladas": float(p.Horas_Acumuladas or 0),
            "eliminable": intacta,
        })
    return resultado


@router.delete("/producciones-terminadas/{id_produccion}")
def borrar_produccion_terminada(id_produccion: int, sesion: Session = Depends(get_sesion)):
    """Elimina una produccion terminada intacta, devolviendo insumos y absorcion (item 6a)."""
    try:
        return eliminar_produccion_terminada(sesion, id_produccion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            # Para cargar la cantidad en paquetes + botellas sueltas (6.13).
            "botellas_por_paquete": producto.Botellas_Por_Paquete if producto else 1,
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
                "destacado": producto.Destacado_Producto_Terminado if producto else False,
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
            "destacado": d["destacado"],
            "stock_total": stock,
            "costo_promedio": round(d["valor_total"] / stock, 4) if stock > 0 else 0,
            "botellas_por_paquete": botellas_paquete,
            "paquetes_equivalentes": round(stock / botellas_paquete, 2),
        })
    return resultado
