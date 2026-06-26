"""
clientes.py
Logica para registrar clientes y sectores.
El cliente es un catalogo; su unica regla es que el sector (si se indica)
debe existir en la tabla Sector (lista validada para el mapa de zonas).
"""

from app.models import Cliente, Sector


def crear_sector(sesion, nombre):
    """Crea un sector si no existe. Normaliza para evitar duplicados por
    mayusculas o espacios (Centro / centro / 'Centro ' = el mismo)."""

    if not nombre or nombre.strip() == "":
        raise ValueError("El nombre del sector es obligatorio")

    # Normalizar: quitar espacios de los extremos
    nombre_limpio = nombre.strip()

    # Buscar si ya existe uno que coincida sin importar mayusculas/minusculas
    existente = (
        sesion.query(Sector)
        .filter(Sector.Nombre_Sector.ilike(nombre_limpio))  # ilike = ignora mayus/minus
        .first()
    )
    if existente is not None:
        return existente   # ya existe (aunque este escrito distinto), devuelve ese

    try:
        sector = Sector(Nombre_Sector=nombre_limpio)
        sesion.add(sector)
        sesion.commit()
        return sector
    except Exception as e:
        sesion.rollback()
        raise e


def registrar_cliente(sesion, nombre, apellido=None, celular=None,
                      licoreria=None, latitud=None, longitud=None, id_sector=None):
    """
    Registra un cliente. El sector es opcional, pero si se indica debe existir.
    Devuelve el objeto Cliente creado.
    """

    # ----- VALIDACIONES -----
    if not nombre or nombre.strip() == "":
        raise ValueError("El nombre del cliente es obligatorio")

    if id_sector is not None:
        sector = sesion.get(Sector, id_sector)
        if sector is None:
            raise ValueError(f"No existe sector con Id {id_sector}")

    # ----- EJECUTAR -----
    try:
        cliente = Cliente(
            Nombre_Cliente=nombre,
            Apellido_Cliente=apellido,
            Celular_Cliente=celular,
            Licoreria_Cliente=licoreria,
            Latitud_Cliente=latitud,
            Longitud_Cliente=longitud,
            Id_Sector=id_sector,
        )
        sesion.add(cliente)
        sesion.commit()
        return cliente
    except Exception as e:
        sesion.rollback()
        raise e