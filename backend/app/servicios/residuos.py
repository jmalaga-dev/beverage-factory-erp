"""
residuos.py
Limpieza de residuos de stock bajo el umbral (mejora 3.5).

El problema: el redondeo a cero de 3.2 solo ESCONDE de las listas los lotes
cuyo restante quedo bajo `UMBRAL_STOCK_MINIMO`; la fila en la BD sigue con su
resto positivo. No molesta (las mismas consultas que arman el balance ya los
excluyen, asi que no distorsionan ningun numero), pero los lotes nunca se
cierran del todo y se acumulan.

Como se cierran: NO borrando la fila —eso violaria la inmutabilidad del
historico, que es un principio del sistema— sino con una MERMA por el resto
exacto, que deja el lote en 0 y el evento registrado en el inventario, igual
que cualquier otro ajuste.

Dos decisiones (jul 2026):

1. FLUJO EN DOS PASOS, nunca automatico. Primero `listar_residuos` muestra
   exactamente que lotes se van a poner en cero y el usuario confirma; recien
   ahi `limpiar_residuos` los aplica, y solo sobre los ids confirmados. Un
   disparador automatico en cada consumo (la otra opcion que estaba anotada)
   generaria mermas invisibles que nadie pidio.

2. NO ABSORBEN COSTO (1.4). Una merma normal reparte su costo entre las
   botellas que se produzcan despues; estos restos valen fracciones de
   centavo y crear un item de absorcion por cada uno seria puro ruido en la
   pantalla de Absorcion, para un monto que no mueve ningun numero.
"""

from datetime import date
from decimal import Decimal

from app.config import UMBRAL_STOCK_MINIMO
from app.models import Compra, Materia_Prima, Produccion, Produccion_Intermedio, Producto_Intermedio, Producto_Terminado
from app.servicios.inventario import _aplicar_movimiento_inventario

# Como se describe cada origen: (modelo, campo de restante, origen_lote, clave del id)
ORIGENES = {
    "MP": (Compra, "Cantidad_Restante_Compra", "COMPRA", "id_compra"),
    "INTERMEDIO": (Produccion_Intermedio, "Cantidad_Restante_Producida", "PRODUCCION_INTERMEDIO", "id_prod_intermedio"),
    "TERMINADO": (Produccion, "Cantidad_Restante_Produccion", "PRODUCCION", "id_produccion"),
}


def _nombre(sesion, origen, lote):
    if origen == "MP":
        p = sesion.get(Materia_Prima, lote.Id_Materia_Prima)
        return p.Descripcion_Materia_Prima if p else "?"
    if origen == "INTERMEDIO":
        p = sesion.get(Producto_Intermedio, lote.Id_Producto_Intermedio)
        return p.Descripcion_Producto_Intermedio if p else "?"
    p = sesion.get(Producto_Terminado, lote.Id_Producto_Terminado)
    return p.Descripcion_Producto_Terminado if p else "?"


def _id_lote(origen, lote):
    if origen == "MP":
        return lote.Id_Compra
    if origen == "INTERMEDIO":
        return lote.Id_Produccion_Intermedio
    return lote.Id_Produccion


def listar_residuos(sesion):
    """
    Lotes con un resto positivo pero por debajo del umbral, en los tres
    origenes. Es la vista previa: no toca nada.

    El filtro es `0 < restante <= umbral`. El limite inferior importa: los
    restantes NEGATIVOS (5 casos conocidos que quedaron de la migracion del
    excel, ver 8.4) quedan fuera a proposito — no son residuos, son evidencia
    de un sobre-consumo del excel, y "limpiarlos" con una merma agregaria una
    salida sobre un lote que ya esta en rojo.
    """
    umbral = Decimal(str(UMBRAL_STOCK_MINIMO))
    resultado = []
    for origen, (modelo, campo, _origen_lote, _clave) in ORIGENES.items():
        col = getattr(modelo, campo)
        for lote in sesion.query(modelo).filter(col > 0, col <= umbral).all():
            resultado.append({
                "origen": origen,
                "id_lote": _id_lote(origen, lote),
                "nombre": _nombre(sesion, origen, lote),
                "restante": float(getattr(lote, campo)),
            })
    resultado.sort(key=lambda r: (r["origen"], r["nombre"]))
    return resultado


def limpiar_residuos(sesion, seleccion, fecha=None):
    """
    Cierra en cero los lotes confirmados, con una MERMA por su resto exacto.

    `seleccion` = [{origen, id_lote}]. Se re-lee el resto de la BD en vez de
    confiar en el que vino del navegador: entre la vista previa y la
    confirmacion el lote pudo cambiar, y hay que mermar lo que hay ahora.

    Todo en UNA transaccion (o se cierran todos o ninguno), reutilizando el
    core sin commit de inventario.py, igual que devoluciones y reproceso.
    """
    umbral = Decimal(str(UMBRAL_STOCK_MINIMO))
    fecha = fecha or date.today()
    limpiados = []
    omitidos = []

    try:
        for item in seleccion:
            origen = item["origen"]
            if origen not in ORIGENES:
                raise ValueError(f"Origen invalido: {origen}")
            modelo, campo, origen_lote, clave = ORIGENES[origen]

            lote = sesion.get(modelo, item["id_lote"])
            if lote is None:
                raise ValueError(f"No existe el lote {item['id_lote']} de {origen}")

            restante = Decimal(getattr(lote, campo) or 0)
            # Pudo cambiar desde la vista previa: si ya no es un residuo, se
            # salta con aviso en vez de mermar algo que si tiene stock util.
            if restante <= 0 or restante > umbral:
                omitidos.append({
                    "origen": origen, "id_lote": item["id_lote"],
                    "restante": float(restante),
                    "motivo": "ya no es un residuo (cambió desde la vista previa)",
                })
                continue

            _aplicar_movimiento_inventario(
                sesion,
                tipo="MERMA",
                sentido="SALIDA",
                origen_lote=origen_lote,
                cantidad=restante,
                motivo="Limpieza de residuo bajo el umbral",
                fecha=fecha,
                absorber_costo=False,   # ver nota del encabezado
                **{clave: item["id_lote"]},
            )
            limpiados.append({
                "origen": origen, "id_lote": item["id_lote"],
                "restante": float(restante),
            })

        sesion.commit()
    except Exception:
        sesion.rollback()
        raise

    return {"limpiados": limpiados, "omitidos": omitidos}
