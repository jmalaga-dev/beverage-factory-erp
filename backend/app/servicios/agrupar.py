"""
agrupar.py
Helper para sumar insumos repetidos por lote antes de validar/descontar.

Sin esto, dos lineas del mismo lote (ej. 5 + 5 de la compra #1) pasan la
validacion por separado (cada 5 <= restante) pero al ejecutar descuentan 10
de un lote que tenia 5 -> stock negativo. Agrupando primero, la validacion ve
la cantidad total real y el descuento es correcto.
"""


def agrupar_pares(pares):
    """Suma las cantidades de pares (id, cantidad) con el mismo id, preservando
    el orden de primera aparicion."""
    acum = {}
    orden = []
    for id_, cantidad in pares:
        if id_ not in acum:
            acum[id_] = 0
            orden.append(id_)
        acum[id_] += cantidad
    return [(id_, acum[id_]) for id_ in orden]
