# Plantilla de configuracion para migrar_excel_v2.py.
#
# El script de migracion necesita datos especificos del negocio (nombres reales
# de cuentas y banco, y el nombre del excel de origen). Esos son DATOS, no
# codigo, asi que no se versionan: viven en datos_reales/config_migracion.py,
# que Git ignora por completo.
#
# Para correr el script:
#   1. Copiar este archivo a  datos_reales/config_migracion.py
#   2. Reemplazar los valores de abajo por los reales.
#   3. Poner el excel en datos_reales/ con el nombre que pongas en NOMBRE_EXCEL.
#
# El script no arranca si falta datos_reales/config_migracion.py (avisa como
# corregirlo). Y de todos modos no puede correr sin el excel, que tambien vive
# en datos_reales/ y tampoco se versiona: estos nombres solo tienen sentido
# junto a ese archivo.

NOMBRE_EXCEL = "Migracion datos.xlsx"

# (nombre_cuenta, rol) — rol en {FABRICA, CASA, OTRA}. Debe haber exactamente
# una cuenta FABRICA (marca el inicio de cada bloque de dinero en el excel) y
# una CASA (cuenta de respaldo cuando un gasto no dice de que cuenta salio).
CUENTAS = [
    ("BILLETERA FABRICA", "FABRICA"),
    ("BILLETERA CASA", "CASA"),
    ("BANCO EJEMPLO 1", "OTRA"),
    ("BANCO EJEMPLO 2", "OTRA"),
    ("INGRESOS EXTERNOS", "OTRA"),
]

# Etiquetas del excel que son alias de una cuenta ya listada arriba.
ALIAS_CUENTA = {
    "DINERO DE LA CASA": "BILLETERA CASA",
    "DINERO DEL NEGOCIO": "BILLETERA FABRICA",
}
