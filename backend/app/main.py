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

app = FastAPI(
    title="Fabrica V2 API",
    description="API de gestion para la fabrica de bebidas",
    version="1.0.0",
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