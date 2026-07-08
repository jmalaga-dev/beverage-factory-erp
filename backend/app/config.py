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

# Categorias fijas para clasificar Tipo_Bien en el balance (mejora 4.2).
# Elegidas explicitamente al crear/editar un tipo de bien, en vez de
# adivinar por texto en el nombre. Ligadas a las columnas de Balance
# (Total_Inmuebles/Total_Equipos/Total_Otros_Activos), asi que agregar una
# categoria nueva tambien requeriria una columna nueva en Balance.
CATEGORIAS_TIPO_BIEN = ["INMUEBLE", "EQUIPO", "OTRO"]
