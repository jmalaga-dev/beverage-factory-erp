"""
dependencias.py
Piezas reutilizables para los endpoints. Por ahora, la sesion de base de datos:
abre una sesion al recibir una peticion y la cierra al terminar.
"""

from app.database import SessionLocal


def get_sesion():
    """Entrega una sesion de base de datos y la cierra al terminar la peticion."""
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()