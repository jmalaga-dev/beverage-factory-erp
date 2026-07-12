"""
compra_dividida.py
Compra "madre" que se despieza en N materias primas con reparto proporcional
(mejora 3.8, del Excel: un pliego de etiquetas cuesta 100 Bs y salen 5 de A,
3 de B y 4 de C de tamanos distintos; el costo se reparte por AREA).

Cada linea tiene un "factor" (tipicamente el area total que ocupa esa materia
en el pliego, pero puede ser cualquier numero proporcional: peso, volumen...).
El reparto del precio_total es SOLO por factor (factor_linea / factor_total):
la cantidad NO participa del reparto, se usa unicamente para registrar el
lote (Cantidad_Compra) y calcular el precio unitario resultante.
El resultado es N registros de Compra normales (una materia prima cada uno,
con su precio proporcional), del mismo proveedor y cuenta, en UNA transaccion
atomica (todo o nada). Reutiliza el pago parcial/pedido pendiente de las
compras normales (5.1), repartiendo monto_pagado con el mismo factor.
"""

from app.models import Cuenta
from app.servicios.compras import _aplicar_compra


def registrar_compra_dividida(
    sesion, id_cuenta, precio_total, lineas,
    fecha=None, id_proveedor=None, monto_pagado=None, recibida=True,
):
    """
    Reparte precio_total (y monto_pagado, si se paga parcial) entre las
    lineas, proporcional al factor de cada una (la cantidad NO pesa en el
    reparto, solo sirve para registrar el lote y el precio unitario), y
    registra una Compra por linea.

    lineas: lista de dicts {"id_materia_prima": int, "cantidad": Decimal,
            "factor": Decimal} (factor > 0, ej. area total de esa materia).

    Devuelve una lista de dicts con el detalle de cada compra creada:
        {id_compra, id_materia_prima, cantidad, proporcion, precio_asignado}
    Lanza ValueError si algo no es valido (mismas reglas que una compra normal).
    """

    # ----- VALIDACIONES -----
    if not lineas:
        raise ValueError("La compra dividida debe tener al menos una linea")
    if precio_total <= 0:
        raise ValueError("El precio total debe ser mayor a cero")

    cuenta = sesion.get(Cuenta, id_cuenta)
    if cuenta is None:
        raise ValueError(f"No existe cuenta con Id {id_cuenta}")

    if monto_pagado is None:
        monto_pagado = precio_total
    if monto_pagado < 0:
        raise ValueError("El monto pagado no puede ser negativo")
    if monto_pagado > precio_total:
        raise ValueError("El monto pagado no puede superar el precio total")

    for linea in lineas:
        if linea["cantidad"] <= 0:
            raise ValueError("La cantidad de cada linea debe ser mayor a cero")
        if linea["factor"] <= 0:
            raise ValueError("El factor (ej. area) de cada linea debe ser mayor a cero")

    factor_total = sum(linea["factor"] for linea in lineas)
    if factor_total <= 0:
        raise ValueError("El factor total debe ser mayor a cero")

    # ----- EJECUTAR (todo o nada): una Compra por linea, mismo proveedor/cuenta -----
    try:
        resultado = []
        precio_asignado_acum = 0
        pagado_acum = 0
        n = len(lineas)
        for i, linea in enumerate(lineas):
            proporcion = linea["factor"] / factor_total
            es_ultima = (i == n - 1)
            # La ultima linea absorbe el redondeo (para que la suma cierre
            # exacto con precio_total y monto_pagado, no quede un resto suelto).
            if es_ultima:
                precio_linea = precio_total - precio_asignado_acum
                pagado_linea = monto_pagado - pagado_acum
            else:
                precio_linea = round(precio_total * proporcion, 2)
                pagado_linea = round(monto_pagado * proporcion, 2)
            precio_asignado_acum += precio_linea
            pagado_acum += pagado_linea

            compra = _aplicar_compra(
                sesion,
                id_materia_prima=linea["id_materia_prima"],
                id_cuenta=id_cuenta,
                cantidad=linea["cantidad"],
                precio_total=precio_linea,
                fecha=fecha,
                id_proveedor=id_proveedor,
                monto_pagado=pagado_linea,
                recibida=recibida,
            )
            resultado.append({
                "id_compra": None,   # se completa despues del flush
                "compra_obj": compra,
                "id_materia_prima": linea["id_materia_prima"],
                "cantidad": linea["cantidad"],
                "proporcion": proporcion,
                "precio_asignado": precio_linea,
            })

        sesion.flush()  # asigna los Id_Compra de todas las lineas
        for r in resultado:
            r["id_compra"] = r.pop("compra_obj").Id_Compra

        sesion.commit()
        return resultado

    except Exception as e:
        sesion.rollback()
        raise e
