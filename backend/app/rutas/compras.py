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
from app.servicios.compras import registrar_compra, recibir_compra
from app.servicios.compra_dividida import registrar_compra_dividida
from app.servicios.compras_lote import previsualizar_compras_lote, registrar_compras_lote

router = APIRouter(tags=["compras"])


class CompraEntrada(BaseModel):
    id_materia_prima: int
    id_cuenta: int
    cantidad: Decimal
    precio_total: Decimal
    fecha: date | None = None
    id_proveedor: int | None = None
    # None = pago total. Si es menor al precio, el faltante va a deuda (5.1).
    monto_pagado: Decimal | None = None
    # False = pedido pendiente (aun no llego, no cuenta como stock) (5.1).
    recibida: bool = True


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
            monto_pagado=datos.monto_pagado,
            recibida=datos.recibida,
        )
        return {
            "mensaje": "Compra registrada" if compra.Recibida_Compra else "Pedido pendiente registrado",
            "id_compra": compra.Id_Compra,
            "cantidad_restante": float(compra.Cantidad_Restante_Compra),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LineaCompraDividida(BaseModel):
    id_materia_prima: int
    cantidad: Decimal
    factor: Decimal   # ej. area de una unidad; proporcional a lo que se reparte


class CompraDivididaEntrada(BaseModel):
    id_cuenta: int
    precio_total: Decimal
    lineas: list[LineaCompraDividida]
    fecha: date | None = None
    id_proveedor: int | None = None
    monto_pagado: Decimal | None = None
    recibida: bool = True


@router.post("/compras-divididas")
def crear_compra_dividida(datos: CompraDivididaEntrada, sesion: Session = Depends(get_sesion)):
    """Compra 'madre' (ej. un pliego) que se reparte proporcionalmente entre
    varias materias primas (mejora 3.8). Registra una Compra por linea."""
    try:
        lineas = [
            {"id_materia_prima": l.id_materia_prima, "cantidad": l.cantidad, "factor": l.factor}
            for l in datos.lineas
        ]
        resultado = registrar_compra_dividida(
            sesion,
            id_cuenta=datos.id_cuenta,
            precio_total=datos.precio_total,
            lineas=lineas,
            fecha=datos.fecha or date.today(),
            id_proveedor=datos.id_proveedor,
            monto_pagado=datos.monto_pagado,
            recibida=datos.recibida,
        )
        return {
            "mensaje": "Compra dividida registrada",
            "lineas": [
                {
                    "id_compra": r["id_compra"],
                    "id_materia_prima": r["id_materia_prima"],
                    "cantidad": float(r["cantidad"]),
                    "proporcion": round(float(r["proporcion"]) * 100, 2),
                    "precio_asignado": float(r["precio_asignado"]),
                }
                for r in resultado
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LineaCompraLote(BaseModel):
    id_materia_prima: int
    cantidad: Decimal
    precio_total: Decimal
    id_proveedor: int | None = None


class ComprasLoteEntrada(BaseModel):
    lineas: list[LineaCompraLote]
    fecha: date | None = None


def _lineas_lote_dict(datos: ComprasLoteEntrada):
    return [
        {
            "id_materia_prima": l.id_materia_prima,
            "cantidad": l.cantidad,
            "precio_total": l.precio_total,
            "id_proveedor": l.id_proveedor,
        }
        for l in datos.lineas
    ]


@router.post("/compras-lote/preview")
def previsualizar_compras_lote_ruta(datos: ComprasLoteEntrada, sesion: Session = Depends(get_sesion)):
    """Calcula, sin registrar nada, de qué cuenta saldría cada línea (mejora:
    tabla de compras con reparto de gasto Fábrica primero, Casa después)."""
    try:
        return previsualizar_compras_lote(sesion, _lineas_lote_dict(datos))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compras-lote")
def crear_compras_lote(datos: ComprasLoteEntrada, sesion: Session = Depends(get_sesion)):
    """Registra varias compras a la vez (una por línea), pagando primero
    desde la cuenta Fábrica y luego desde Casa. Todo o nada."""
    try:
        resultado = registrar_compras_lote(
            sesion,
            lineas=_lineas_lote_dict(datos),
            fecha=datos.fecha or date.today(),
        )
        return {
            "mensaje": f"{len(resultado['lineas'])} compras registradas",
            "total_fabrica": float(resultado["total_fabrica"]),
            "total_casa": float(resultado["total_casa"]),
            "lineas": [
                {"id_compra": r["id_compra"], "cuenta": r["cuenta"]}
                for r in resultado["lineas"]
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pedidos-pendientes")
def listar_pedidos_pendientes(sesion: Session = Depends(get_sesion)):
    """Compras registradas como pedido pero aún no recibidas (sin stock)."""
    pedidos = sesion.query(Compra).filter(Compra.Recibida_Compra.is_(False)).all()
    resultado = []
    for c in pedidos:
        mp = sesion.get(Materia_Prima, c.Id_Materia_Prima)
        prov = sesion.get(Proveedor, c.Id_Proveedor) if c.Id_Proveedor else None
        resultado.append({
            "id_compra": c.Id_Compra,
            "nombre_materia": mp.Descripcion_Materia_Prima if mp else "?",
            "cantidad": float(c.Cantidad_Compra),
            "precio_compra": float(c.Precio_Compra),
            "proveedor": prov.Nombre_Proveedor if prov else None,
            "fecha": c.Fecha_Compra.isoformat() if c.Fecha_Compra else None,
        })
    return resultado


@router.post("/compras/{id_compra}/recibir")
def recibir_pedido(id_compra: int, sesion: Session = Depends(get_sesion)):
    """Marca un pedido pendiente como recibido: el stock aparece."""
    try:
        compra = recibir_compra(sesion, id_compra)
        return {
            "mensaje": "Pedido recibido",
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


@router.get("/ultima-compra/{id_materia_prima}/{id_proveedor}")
def ultima_compra(id_materia_prima: int, id_proveedor: int, sesion: Session = Depends(get_sesion)):
    """Cantidad y precio total de la ULTIMA compra de esa materia prima a ese
    proveedor, para predeterminar el formulario de compra (mejora 10.3). Si no
    hay ninguna compra previa de ese par, devuelve hay=False."""
    c = (
        sesion.query(Compra)
        .filter(
            Compra.Id_Materia_Prima == id_materia_prima,
            Compra.Id_Proveedor == id_proveedor,
        )
        .order_by(Compra.Fecha_Compra.desc(), Compra.Id_Compra.desc())
        .first()
    )
    if c is None:
        return {"hay": False}
    return {
        "hay": True,
        "cantidad": float(c.Cantidad_Compra),
        "precio_total": float(c.Precio_Compra),
        "fecha": c.Fecha_Compra.isoformat() if c.Fecha_Compra else None,
    }


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
    stock-intermedio-general y stock-terminado-general: solo aparecen las
    materias con stock > 0, no todo el catalogo)."""
    lotes = sesion.query(Compra).filter(Compra.Cantidad_Restante_Compra > UMBRAL_STOCK_MINIMO).all()

    resumen = {}
    for c in lotes:
        mid = c.Id_Materia_Prima
        if mid not in resumen:
            materia = sesion.get(Materia_Prima, mid)
            resumen[mid] = {
                "descripcion": materia.Descripcion_Materia_Prima if materia else "?",
                "unidad": materia.Unidad_Materia_Prima if materia else "",
                "stock_total": 0.0,
                "valor_total": 0.0,
            }
        cant = float(c.Cantidad_Restante_Compra)
        costo_unit = float(c.Precio_Compra) / float(c.Cantidad_Compra) if c.Cantidad_Compra else 0
        resumen[mid]["stock_total"] += cant
        resumen[mid]["valor_total"] += cant * costo_unit

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


@router.get("/ultimo-precio-materia/{id_materia_prima}")
def ultimo_precio_materia(id_materia_prima: int, sesion: Session = Depends(get_sesion)):
    """
    Ultima compra de esa materia prima: precio unitario, cantidad y fecha
    (mejora 6.7). Sirve para predeterminar el precio al cargar una compra
    nueva, que es el dato que mas se repite entre compras seguidas.

    Es por MATERIA, no por proveedor: hoy las 2454 compras migradas del excel
    tienen Id_Proveedor en NULL, asi que filtrar por proveedor devolveria
    vacio para casi todo el catalogo. Cuando haya historial con proveedor,
    afinarlo es un WHERE mas (ver 5.1).

    Devuelve null en `precio_unitario` si nunca se compro: el frontend deja el
    campo vacio en vez de sugerir un cero que se registraria sin querer.
    """
    ultima = (
        sesion.query(Compra)
        .filter(Compra.Id_Materia_Prima == id_materia_prima, Compra.Cantidad_Compra > 0)
        .order_by(Compra.Fecha_Compra.desc(), Compra.Id_Compra.desc())
        .first()
    )
    if ultima is None:
        return {"precio_unitario": None, "cantidad": None, "precio_total": None, "fecha": None}
    return {
        "precio_unitario": float(ultima.Precio_Compra / ultima.Cantidad_Compra),
        "cantidad": float(ultima.Cantidad_Compra),
        "precio_total": float(ultima.Precio_Compra),
        "fecha": ultima.Fecha_Compra.isoformat(),
    }
