"""
config.py
Constantes de configuracion compartidas por toda la app.
"""

from decimal import Decimal

# Un lote con menos que esto se considera agotado y no aparece en las listas
# de stock disponible (dropdowns, tablas de stock), aunque tecnicamente le
# quede un resto positivo. El resto no es basura de punto flotante (Decimal
# ya evita eso) sino un remanente real demasiado chico para usarse. Ajustar
# este valor segun que tan chico es, en la practica, un resto inutilizable.
UMBRAL_STOCK_MINIMO = Decimal("0.0001")

# Tasa por defecto para la absorcion de costos indirectos por botella (mejora
# 1.4): cuantas botellas se estima que absorberan cada boliviano de un costo
# indirecto (utensilio, feriado, merma). Ej: 10 => un costo de 100 Bs se
# reparte entre 100*10 = 1000 botellas (0.10 Bs/botella). Es solo el valor
# SUGERIDO al registrar un utensilio/feriado (editable en el formulario), y el
# usado al crear automaticamente el item de una merma. Ajustable en un lugar.
TASA_ABSORCION_DEFECTO = 10

# Roles de cuenta (mejora 2): distinguen las billeteras para el reparto por
# prioridad. FABRICA y CASA son las dos billeteras del reparto; OTRA es
# cualquier otra cuenta (ej. un banco) que no entra en las reglas de prioridad.
ROLES_CUENTA = ["FABRICA", "CASA", "OTRA"]

# Orden de prioridad de las cuentas para cubrir una salida, segun el tipo de
# gasto (mejora 2.B). El reparto propone drenar las cuentas en este orden de
# rol (respetando saldos) hasta cubrir el total.
PRIORIDAD_CUENTAS = {
    "FAMILIAR": ["CASA", "FABRICA", "OTRA"],   # gasto de la casa: primero Casa
    "FABRICA": ["FABRICA", "CASA", "OTRA"],    # compra/pago de la fabrica: primero Fabrica
}

# Categorias fijas para clasificar Tipo_Bien en el balance (mejora 4.2).
# Elegidas explicitamente al crear/editar un tipo de bien, en vez de
# adivinar por texto en el nombre. Ligadas a las columnas de Balance
# (Total_Inmuebles/Total_Equipos/Total_Otros_Activos), asi que agregar una
# categoria nueva tambien requeriria una columna nueva en Balance.
CATEGORIAS_TIPO_BIEN = ["INMUEBLE", "EQUIPO", "OTRO"]
