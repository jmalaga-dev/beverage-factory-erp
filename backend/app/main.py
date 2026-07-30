"""
main.py
Punto de entrada de la API de Fabrica V2 (FastAPI).
Solo ensambla: crea la app, configura CORS y manejo de errores,
y registra los routers de app/rutas (uno por dominio).
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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


# Carpeta del frontend ya compilado (`npm run build`). Solo existe cuando se
# compilo: en desarrollo no esta, porque ahi el frontend lo sirve Vite en su
# propio puerto con recarga en caliente.
#
# Si esta, este mismo proceso sirve tambien la interfaz (mejora 8.8): un solo
# proceso, un solo puerto, sin CORS ni Node corriendo. Es el modo del
# lanzador local. Si no esta, el backend se comporta exactamente como
# siempre y solo responde la API.
RUTA_DIST = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()

# Rutas que son de la API o de sus herramientas y nunca de la interfaz.
PREFIJOS_API = ("/assets/", "/docs", "/redoc", "/openapi.json")


def _es_navegacion(request: Request) -> bool:
    """True si el pedido es el navegador ABRIENDO una pagina (no un fetch)."""
    if request.method != "GET":
        return False
    if request.url.path.startswith(PREFIJOS_API):
        return False
    # Un archivo concreto (favicon.svg, algo.png) lo resuelve la ruta comodin
    # del final, que lo busca en dist.
    if "." in request.url.path.rsplit("/", 1)[-1]:
        return False

    # `Sec-Fetch-Mode: navigate` es la señal exacta: los navegadores la mandan
    # solo cuando el usuario ABRE una direccion (link, F5, marcador), y ponen
    # `cors`/`same-origin` en las llamadas de fetch(). Si no viene (navegador
    # viejo), se cae al Accept: una navegacion pide text/html, un fetch() sin
    # cabeceras propias pide */*.
    modo = request.headers.get("sec-fetch-mode")
    if modo:
        return modo == "navigate"
    return "text/html" in request.headers.get("accept", "")


@app.middleware("http")
async def frontend_antes_que_api(request: Request, call_next):
    """Le da la interfaz al navegador cuando la direccion es de una pantalla.

    Hace falta porque las rutas de la app se llaman IGUAL que los endpoints:
    la pantalla de ventas es /ventas y la API de ventas tambien. Con el
    frontend en su propio puerto (desarrollo con Vite, o nginx en Docker) no
    hay conflicto, son dos origenes distintos. Sirviendo todo desde un solo
    puerto sí: sin esto, entrar directo a /ventas o apretar F5 ahi devolveria
    el JSON crudo de la API en vez de la pantalla.

    No se puede resolver con una ruta comodin al final, porque FastAPI
    resuelve en orden de registro y /ventas de la API gana antes de llegar.
    De ahi que sea un middleware, que corre ANTES del ruteo.

    Se distingue por el tipo de pedido, no por la direccion: el navegador
    abriendo una pagina recibe la interfaz, y el fetch() de esa misma
    interfaz pidiendo /ventas recibe los datos. Las dos cosas conviven en la
    misma direccion.
    """
    if RUTA_DIST.is_dir() and _es_navegacion(request):
        return FileResponse(RUTA_DIST / "index.html")
    return await call_next(request)


@app.get("/")
def inicio():
    if RUTA_DIST.is_dir():
        return FileResponse(RUTA_DIST / "index.html")
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


# Ultima ruta a proposito: FastAPI resuelve en orden de registro, asi que
# todos los endpoints de arriba (y /docs, /openapi.json) ganan sobre este
# comodin. Solo llega aca lo que no es de la API.
#
# Es el equivalente del `try_files $uri $uri/ /index.html` de nginx en el
# modo Docker: las rutas de la app (/ventas, /balance...) no son archivos en
# disco, las resuelve react-router en el navegador. Sin esto, entrar directo
# a /ventas o recargar con F5 daria 404.
@app.get("/{ruta_spa:path}", include_in_schema=False)
def servir_frontend(ruta_spa: str):
    if not RUTA_DIST.is_dir():
        raise HTTPException(status_code=404, detail="No encontrado")

    # Un pedido como `../../backend/.env` saldria de dist y serviria archivos
    # del repositorio. Se resuelve la ruta y se exige que quede adentro.
    archivo = (RUTA_DIST / ruta_spa).resolve()
    if ruta_spa and RUTA_DIST in archivo.parents and archivo.is_file():
        return FileResponse(archivo)

    return FileResponse(RUTA_DIST / "index.html")
