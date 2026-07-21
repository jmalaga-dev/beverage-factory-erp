"""
main.py
Punto de entrada de la API de Fabrica V2 (FastAPI).
Solo ensambla: crea la app, configura CORS y manejo de errores,
y registra los routers de app/rutas (uno por dominio).
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.rutas import (
    absorcion,
    activos,
    balance,
    catalogos,
    cierre,
    clientes,
    compras,
    deudas,
    devoluciones,
    fifo,
    gastos,
    inventario,
    jornadas,
    pagos,
    produccion,
    prorrateo,
    proveedores,
    recetas,
    saldo_producto,
    simulacion,
    transferencias,
    ventas,
)

app = FastAPI(
    title="Fabrica V2 API",
    description="API de gestion para la fabrica de bebidas",
    version="1.0.0",
)

# Permitir que el frontend (que corre en otro puerto) pueda pedir datos a esta
# API. Los origenes salen del .env (CORS_ORIGINS, separados por coma) para que
# el despliegue en Docker —donde el frontend se sirve con nginx en otro
# puerto— pueda agregar el suyo sin tocar codigo. Sin la variable, quedan los
# dos de desarrollo de siempre: el entorno local no cambia.
CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],   # permite GET, POST, etc.
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def error_bd(request: Request, exc: SQLAlchemyError):
    # Muestra solo una linea corta en la terminal, no el traceback gigante
    print(f"ERROR BD en {request.url.path}: {str(exc)[:200]}")
    return JSONResponse(status_code=500, content={"detail": "Error de base de datos"})


@app.get("/")
def inicio():
    return {"mensaje": "API de Fabrica V2 funcionando"}


app.include_router(clientes.router)
app.include_router(catalogos.router)
app.include_router(compras.router)
app.include_router(jornadas.router)
app.include_router(produccion.router)
app.include_router(ventas.router)
app.include_router(pagos.router)
app.include_router(gastos.router)
app.include_router(inventario.router)
app.include_router(prorrateo.router)
app.include_router(activos.router)
app.include_router(balance.router)
app.include_router(transferencias.router)
app.include_router(proveedores.router)
app.include_router(deudas.router)
app.include_router(absorcion.router)
app.include_router(fifo.router)
app.include_router(recetas.router)
app.include_router(devoluciones.router)
app.include_router(cierre.router)
app.include_router(saldo_producto.router)
app.include_router(simulacion.router)
