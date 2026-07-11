"""
Rutas de compras de materia prima y consultas de su stock.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import UMBRAL_STOCK_MINIMO
from app.dependencias import get_sesion
from app.models import Compra, Materia_Prima, Proveedor
from app.servicios.compras import registrar_compra

router = APIRouter(tags=["compras"])


class CompraEntrada(BaseModel):
    id_materia_prima: int
    id_cuenta: int
    cantidad: Decimal
    precio_total: Decimal
    fecha: date | None = None
    id_proveedor: int | None = None


@router.post("/compras")
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
            cantidad=datos.cantidad,
            precio_total=datos.precio_total,
            fecha=datos.fecha or date.today(),
            id_proveedor=datos.id_proveedor,
        )
        return {
            "mensaje": "Compra registrada",
            "id_compra": compra.Id_Compra,
            "cantidad_restante": float(compra.Cantidad_Restante_Compra),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lotes-compra")
def listar_lotes_compra(sesion: Session = Depends(get_sesion)):
    """Lotes de compra con stock, incluyendo el nombre de la materia prima."""
    lotes = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()
    resultado = []
    for c in lotes:
        mp = sesion.get(Materia_Prima, c.Id_Materia_Prima)
        prov = sesion.get(Proveedor, c.Id_Proveedor) if c.Id_Proveedor else None
        resultado.append({
            "id_compra": c.Id_Compra,
            "id_materia_prima": c.Id_Materia_Prima,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "cantidad_restante": float(c.Cantidad_Restante_Compra),
            "precio_compra": float(c.Precio_Compra),
            "cantidad_compra": float(c.Cantidad_Compra),
            "proveedor": prov.Nombre_Proveedor if prov else None,
        })
    return resultado


@router.get("/comparacion-precios-proveedor")
def comparacion_precios_proveedor(sesion: Session = Depends(get_sesion)):
    """Precio unitario (precio/cantidad) de cada materia prima por proveedor,
    a partir del historial de compras: minimo, promedio, maximo y ultimo.
    Sirve para decidir a que proveedor conviene comprar (mejora 5.1)."""
    compras = (
        sesion.query(Compra)
        .filter(Compra.Id_Proveedor.isnot(None))
        .order_by(Compra.Fecha_Compra, Compra.Id_Compra)
        .all()
    )
    # (id_materia, id_proveedor) -> lista de (unitario, nombres)
    acum = {}
    for c in compras:
        if not c.Cantidad_Compra:
            continue
        unit = float(c.Precio_Compra) / float(c.Cantidad_Compra)
        clave = (c.Id_Materia_Prima, c.Id_Proveedor)
        acum.setdefault(clave, []).append(unit)

    resultado = []
    for (id_mp, id_prov), unitarios in acum.items():
        mp = sesion.get(Materia_Prima, id_mp)
        prov = sesion.get(Proveedor, id_prov)
        resultado.append({
            "id_materia_prima": id_mp,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "unidad": mp.Unidad_Materia_Prima if mp else "",
            "id_proveedor": id_prov,
            "nombre_proveedor": prov.Nombre_Proveedor if prov else "?",
            "compras": len(unitarios),
            "precio_min": round(min(unitarios), 4),
            "precio_promedio": round(sum(unitarios) / len(unitarios), 4),
            "precio_max": round(max(unitarios), 4),
            "precio_ultimo": round(unitarios[-1], 4),
        })
    # Ordenar por materia y luego por precio promedio (mas barato primero)
    resultado.sort(key=lambda r: (r["nombre_materia"], r["precio_promedio"]))
    return resultado


@router.get("/stock-materia-prima")
def stock_materia_prima(sesion: Session = Depends(get_sesion)):
    """Stock general de materia prima: suma el restante de todos los lotes por
    cada materia, con su costo unitario promedio ponderado (mismo patron que
    stock-intermedio-general y stock-terminado-general)."""
    materias = sesion.query(Materia_Prima).all()
    lotes = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()

    resumen = {
        m.Id_Materia_Prima: {
            "descripcion": m.Descripcion_Materia_Prima,
            "unidad": m.Unidad_Materia_Prima,
            "stock_total": 0.0,
            "valor_total": 0.0,
        }
        for m in materias
    }
    for c in lotes:
        datos = resumen.get(c.Id_Materia_Prima)
        if datos is None:
            continue
        cant = float(c.Cantidad_Restante_Compra)
        costo_unit = float(c.Precio_Compra) / float(c.Cantidad_Compra) if c.Cantidad_Compra else 0
        datos["stock_total"] += cant
        datos["valor_total"] += cant * costo_unit

    resultado = []
    for mid, datos in resumen.items():
        stock = datos["stock_total"]
        costo_prom = datos["valor_total"] / stock if stock > 0 else 0
        resultado.append({
            "id_materia_prima": mid,
            "descripcion": datos["descripcion"],
            "unidad": datos["unidad"],
            "stock_total": stock,
            "costo_promedio": round(costo_prom, 4),
        })
    return resultado
