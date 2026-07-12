"""
horas.py
Motor de horas-hombre acumuladas y heredadas en cadena (mejora 1.1).

Cada produccion "recuerda" cuantas horas-hombre lleva embebidas en el lote
completo (Horas_Acumuladas). Al consumir q unidades de un lote origen, el
consumidor hereda q * (Horas_Acumuladas_origen / Cantidad_Producida_origen):
la tasa de horas por unidad es constante, asi lo que se consume se lleva su
parte y lo que queda conserva la suya (por mes de consumo, no de produccion).
"""

from decimal import Decimal


def horas_por_unidad(horas_acumuladas, cantidad_producida):
    """Horas-hombre por unidad de un lote (0 si no hay datos)."""
    if not cantidad_producida or cantidad_producida <= 0:
        return Decimal(0)
    return (horas_acumuladas or Decimal(0)) / cantidad_producida


def horas_heredadas_de(source_intermedio, cantidad):
    """Horas que hereda quien consume `cantidad` de un lote intermedio origen."""
    return cantidad * horas_por_unidad(
        source_intermedio.Horas_Acumuladas, source_intermedio.Cantidad_Producida
    )
