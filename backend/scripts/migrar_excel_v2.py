# Migracion unica: excel consolidado V1 -> BD V2 (jul 2026).
#
# Lee el excel consolidado desde datos_reales/ (una sola hoja con ~22 bloques
# de tablas lado a lado) y carga toda la historia en PostgreSQL en UNA sola
# transaccion: catalogos, compras, jornadas, producciones (con detalle de
# insumos), ventas, prorrateo de gastos extra, movimientos de dinero
# (gastos familiares, amortizacion de deudas, transferencias) y saldos.
#
# Decisiones acordadas (ver DECISIONES_DISENO.md):
#  - Saldos de cuenta: ultimo snapshot conocido del excel.
#  - Deudas: se migran todas (incl. saldo 0); "BOTELLAS JULIETA" duplicada
#    se fusiona en una sola.
#  - Gastos con varias cuentas el mismo dia: asignacion greedy en orden.
#  - Absorciones UOE historicas: contra un Item_Absorcion generico, porque
#    el excel no dice que utensilio absorbio cada lote.
#  - Taxi de una venta: la diferencia entre PV*CANTIDAD y la columna TOTAL del
#    excel (ver seccion 5). Requiere la columna Venta.Taxi_Venta, o sea correr
#    antes migraciones/027_venta_taxi.sql.
#
# Uso:  python backend/scripts/migrar_excel_v2.py [--dry-run]
#
# Despues de correr esto, aplicar tambien migraciones/022_jornadas_migradas_pagadas.sql:
# las jornadas quedan con Id_Pago_Trabajador NULL (el excel no tenia tabla de
# pagos), y en V2 eso significa "pendiente de pago" -sin ese fix, el endpoint
# de pago sugerido suma todas las horas historicas de un trabajador como si
# nunca se le hubiera pagado nada.
import datetime
import importlib.util
import os
import re
import sys
from collections import defaultdict

import openpyxl
import psycopg2
import psycopg2.extras

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATOS_REALES = os.path.join(os.path.dirname(BASE), "datos_reales")

# Los nombres reales de cuentas/banco y el del excel son DATOS, no codigo, asi
# que viven en datos_reales/config_migracion.py (gitignoreado). Plantilla en
# backend/scripts/config_migracion.ejemplo.py.
_cfg_path = os.path.join(DATOS_REALES, "config_migracion.py")
if not os.path.exists(_cfg_path):
    raise SystemExit(
        "Falta datos_reales/config_migracion.py. Copia la plantilla "
        "backend/scripts/config_migracion.ejemplo.py ahi y completa los "
        "nombres reales de cuentas y del excel."
    )
_spec = importlib.util.spec_from_file_location("config_migracion", _cfg_path)
config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(config)

RUTA_EXCEL = os.path.join(DATOS_REALES, config.NOMBRE_EXCEL)
CUENTAS = config.CUENTAS
ALIAS_CUENTA = config.ALIAS_CUENTA
# Derivados del rol, para no hardcodear nombres en la logica de mas abajo:
CUENTA_MARCADOR_BLOQUE = next(n for n, rol in CUENTAS if rol == "FABRICA")
CUENTA_FALLBACK = next(n for n, rol in CUENTAS if rol == "CASA")
DRY_RUN = "--dry-run" in sys.argv

anomalias = defaultdict(int)
ejemplos_anomalias = defaultdict(list)


def anota(clave, ejemplo=None):
    anomalias[clave] += 1
    if ejemplo is not None and len(ejemplos_anomalias[clave]) < 3:
        ejemplos_anomalias[clave].append(str(ejemplo)[:80])


# ---------- conexion ----------
def conectar():
    envvars = {}
    with open(os.path.join(BASE, ".env"), encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"^\s*([^#=]+?)\s*=\s*(.*)\s*$", linea)
            if m:
                envvars[m.group(1)] = m.group(2)
    return psycopg2.connect(
        host=envvars["DB_HOST"], port=envvars["DB_PORT"],
        user=envvars["DB_USER"], password=envvars["DB_PASSWORD"],
        dbname=envvars["DB_NAME"],
    )


# ---------- parsers ----------
def parse_fecha(v):
    """Acepta datetime, 'F11072021', 'F11/07/2021', 'F1/7/2021'."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip()
    if s.startswith("F"):
        s = s[1:]
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s) or re.match(r"^(\d{2})(\d{2})(\d{4})$", s)
    if m:
        dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(yyyy, mm, dd)
        except ValueError:
            # fecha imposible en el excel (ej. 31/06): clamp al ultimo dia del mes
            anota("fecha_invalida_clampeada", v)
            import calendar
            if 1 <= mm <= 12:
                return datetime.date(yyyy, mm, min(dd, calendar.monthrange(yyyy, mm)[1]))
            return None
    anota("fecha_no_parseable", v)
    return None


def fecha_de_lote(codigo):
    """'PT0002CADF12072021S4' -> date(2021,7,12)."""
    m = re.search(r"F(\d{2})(\d{2})(\d{4})S\d+", str(codigo))
    if m:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def seq_de_lote(codigo):
    m = re.search(r"S(\d+)I?$", str(codigo))
    return int(m.group(1)) if m else 0


# ---------- carga excel ----------
print(f"Leyendo {RUTA_EXCEL} ...")
wb = openpyxl.load_workbook(RUTA_EXCEL, data_only=True, read_only=True)
ws = wb["Hoja1"]
filas = list(ws.iter_rows(values_only=True))
fila_header = filas[1]
datos = filas[2:]
print(f"  {len(datos)} filas de datos, {len(fila_header)} columnas")

con = conectar()
cur = con.cursor()


def uno(sql, params):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def lote_insert(sql, filas_v):
    if filas_v:
        psycopg2.extras.execute_values(cur, sql, filas_v, page_size=1000)


resumen = {}

# =====================================================================
# 1. CATALOGOS
# =====================================================================

# --- Sector (col 83) ---
sector_id = {}
for f in datos:
    nombre = f[83]
    if nombre in (None, ""):
        continue
    nombre = str(nombre).strip()
    if nombre not in sector_id:
        sector_id[nombre] = uno(
            'INSERT INTO "Sector" ("Nombre_Sector", "Habilitado_Sector") VALUES (%s, true) RETURNING "Id_Sector"',
            (nombre,))
resumen["Sector"] = len(sector_id)

# --- Grupo_Movimiento (grupos de gastos familiares, col 117) ---
grupo_id = {}
for f in datos:
    g = f[117]
    if g in (None, "") or str(g).strip() == "":
        continue
    g = str(g).strip()
    if g not in grupo_id:
        grupo_id[g] = uno(
            'INSERT INTO "Grupo_Movimiento" ("Nombre_Grupo_Movimiento", "Habilitado_Grupo_Movimiento") VALUES (%s, true) RETURNING "Id_Grupo_Movimiento"',
            (g,))
resumen["Grupo_Movimiento"] = len(grupo_id)

# --- Materia_Prima (cols 0-2) ---
mp_id = {}
for f in datos:
    cod = f[0]
    if cod in (None, "") or not str(cod).startswith("MP"):
        continue
    if cod in mp_id:
        anota("mp_codigo_duplicado", cod)
        continue
    mp_id[cod] = uno(
        'INSERT INTO "Materia_Prima" ("Descripcion_Materia_Prima", "Unidad_Materia_Prima", "Habilitado_Materia_Prima") VALUES (%s, %s, true) RETURNING "Id_Materia_Prima"',
        (str(f[1]).strip(), str(f[2]).strip() if f[2] else None))
resumen["Materia_Prima"] = len(mp_id)

# --- Trabajador (cols 4-7) ---
trab_id = {}
for f in datos:
    cod = f[4]
    if cod in (None, "") or not str(cod).startswith("T0"):
        continue
    trab_id[cod] = uno(
        'INSERT INTO "Trabajador" ("Nombre_Trabajador", "Pago_Trabajador", "Horas_Base_Trabajador", "Habilitado_Trabajador") VALUES (%s, %s, %s, true) RETURNING "Id_Trabajador"',
        (str(f[5]).strip(), num(f[6]), num(f[7])))
resumen["Trabajador"] = len(trab_id)

# --- Producto_Intermedio (cols 9-10) ---
pi_id = {}
for f in datos:
    cod = f[9]
    if cod in (None, "") or not str(cod).startswith("PI"):
        continue
    pi_id[cod] = uno(
        'INSERT INTO "Producto_Intermedio" ("Descripcion_Producto_Intermedio", "Habilitado_Producto_Intermedio") VALUES (%s, true) RETURNING "Id_Producto_Intermedio"',
        (str(f[10]).strip(),))
resumen["Producto_Intermedio"] = len(pi_id)

# --- Producto_Terminado (cols 32-34) ---
pt_id = {}
for f in datos:
    cod = f[32]
    if cod in (None, "") or not str(cod).startswith("PT"):
        continue
    pt_id[cod] = uno(
        'INSERT INTO "Producto_Terminado" ("Descripcion_Producto_Terminado", "Precio_Venta_Recomendado_Producto_Terminado", "Habilitado_Producto_Terminado") VALUES (%s, %s, true) RETURNING "Id_Producto_Terminado"',
        (str(f[33]).strip(), num(f[34])))
resumen["Producto_Terminado"] = len(pt_id)

# --- Gasto_Extra (cols 85-88) ---
ge_id = {}
for f in datos:
    cod = f[85]
    if cod in (None, "") or not str(cod).startswith("GE"):
        continue
    ge_id[cod] = uno(
        'INSERT INTO "Gasto_Extra" ("Descripcion_Gasto_Extra", "Precio_Mensual_Gasto_Extra", "Habilitado_Gasto_Extra") VALUES (%s, %s, true) RETURNING "Id_Gasto_Extra"',
        (str(f[86]).strip(), num(f[87])))
resumen["Gasto_Extra"] = len(ge_id)

# --- Cliente (cols 64-71); clave de match para ventas = col 68 CONCATENAR ---
cliente_id = {}
for f in datos:
    concat = f[68]
    if concat in (None, ""):
        continue
    concat = str(concat).strip()
    if concat in cliente_id:
        anota("cliente_concat_duplicado", concat)
        continue
    lat, lng = num(f[69]), num(f[70])
    sec = f[71]
    sec_nombre = str(sec).strip() if sec not in (None, "", 0, "0") else None
    id_sector = None
    if sec_nombre:
        if sec_nombre not in sector_id:
            sector_id[sec_nombre] = uno(
                'INSERT INTO "Sector" ("Nombre_Sector", "Habilitado_Sector") VALUES (%s, true) RETURNING "Id_Sector"',
                (sec_nombre,))
            anota("sector_creado_desde_cliente", sec_nombre)
        id_sector = sector_id[sec_nombre]
    cliente_id[concat] = uno(
        'INSERT INTO "Cliente" ("Nombre_Cliente", "Apellido_Cliente", "Celular_Cliente", "Licoreria_Cliente", "Latitud_Cliente", "Longitud_Cliente", "Id_Sector", "Habilitado_Cliente") VALUES (%s,%s,%s,%s,%s,%s,%s,true) RETURNING "Id_Cliente"',
        (str(f[65]).strip() if f[65] is not None else "",
         str(f[66]).strip() if f[66] is not None else None,
         str(f[67]).strip() if f[67] is not None else None,
         str(f[64]).strip() if f[64] is not None else None,
         lat if lat else None, lng if lng else None, id_sector))
resumen["Cliente"] = len(cliente_id)

# --- Tipo_Bien + Activo (cols 104-106) ---
# El titulo de esa tabla en el Excel ("TABLA ANTERIOR ESTE SE DIVIDE AHORA")
# lo dice: era el balance viejo todo junto. En V2 se reparte en tres lugares
# distintos, y solo UNO de ellos es Activo:
#   BILLETERA* / CAJA DE AHORROS -> Cuenta (el efectivo, mas abajo)
#   INVENTARIOS                  -> no se carga: el stock lo calcula el
#                                   balance desde las compras/producciones
#   el resto (inmueble, vehiculo, bienes) -> Activo, que es lo unico que
#                                   distingue el Escenario A del B
# Sin este filtro los bancos quedaban contados dos veces (como Cuenta y como
# Activo) y el stock tambien (calculado y ademas como activo "INVENTARIOS").
CATEGORIA_TIPO_BIEN = {"INMUEBLE": "INMUEBLE", "BIENES DEL NEGOCIO": "EQUIPO"}
TIPOS_QUE_NO_SON_ACTIVO = ("BILLETERA", "CAJA DE AHORROS", "INVENTARIOS")
tipo_bien_id = {}
n_activos = 0
for f in datos:
    tipo, desc, valor = f[104], f[105], num(f[106])
    if tipo in (None, ""):
        continue
    tipo = str(tipo).strip()
    if any(t in tipo.upper() for t in TIPOS_QUE_NO_SON_ACTIVO):
        anota("activo_omitido_no_es_activo_fijo", f"{tipo}: {desc}")
        continue
    if tipo not in tipo_bien_id:
        tipo_bien_id[tipo] = uno(
            'INSERT INTO "Tipo_Bien" ("Nombre_Tipo_Bien", "Categoria_Tipo_Bien") VALUES (%s, %s) RETURNING "Id_Tipo_Bien"',
            (tipo, CATEGORIA_TIPO_BIEN.get(tipo.upper(), "OTRO")))
    cur.execute(
        'INSERT INTO "Activo" ("Id_Tipo_Bien", "Descripcion_Activo", "Valor_Activo") VALUES (%s, %s, %s)',
        (tipo_bien_id[tipo], str(desc).strip() if desc else "", valor or 0))
    n_activos += 1
resumen["Tipo_Bien"] = len(tipo_bien_id)
resumen["Activo"] = n_activos

# --- Deuda (col 108 desc, col 109 saldo). La fila de header ES la primera deuda ---
deuda_id = {}
deudas_crudas = []
if fila_header[108] not in (None, ""):
    deudas_crudas.append((str(fila_header[108]).strip(), num(fila_header[109]) or 0))
for f in datos:
    if f[108] in (None, ""):
        continue
    deudas_crudas.append((str(f[108]).strip(), num(f[109]) or 0))
for desc, saldo in deudas_crudas:
    clave = desc.upper()
    if clave in deuda_id:
        # duplicada (ej. BOTELLAS JULIETA): fusionar sumando saldos
        cur.execute('UPDATE "Deuda" SET "Saldo_Actual_Deuda" = "Saldo_Actual_Deuda" + %s WHERE "Id_Deuda" = %s',
                    (saldo, deuda_id[clave]))
        anota("deuda_duplicada_fusionada", desc)
        continue
    deuda_id[clave] = uno(
        'INSERT INTO "Deuda" ("Descripcion_Deuda", "Saldo_Actual_Deuda") VALUES (%s, %s) RETURNING "Id_Deuda"',
        (desc, saldo))
resumen["Deuda"] = len(deuda_id)

# --- Cuenta --- (CUENTAS y ALIAS_CUENTA vienen del config, ver arriba)
cuenta_id = {}
for nombre, rol in CUENTAS:
    cuenta_id[nombre] = uno(
        'INSERT INTO "Cuenta" ("Nombre_Cuenta", "Saldo_Actual_Cuenta", "Habilitado_Cuenta", "Rol_Cuenta") VALUES (%s, 0, true, %s) RETURNING "Id_Cuenta"',
        (nombre, rol))


def cuenta_de(nombre):
    n = str(nombre).strip()
    n = ALIAS_CUENTA.get(n.upper(), ALIAS_CUENTA.get(n, n))
    return cuenta_id.get(n if n in cuenta_id else n.upper() if n.upper() in cuenta_id else n)


resumen["Cuenta"] = len(cuenta_id)

# --- Item_Absorcion (cols 135-139) + item generico para lo historico ---
n_items = 0
for f in datos:
    desc = f[135]
    if desc in (None, ""):
        continue
    desc = str(desc).replace("\n", " ").strip()
    tipo = "FERIADO" if desc.upper().startswith("HORAS PAGADAS") else "UTENSILIO"
    cur.execute(
        'INSERT INTO "Item_Absorcion" ("Tipo_Item_Absorcion", "Descripcion_Item_Absorcion", "Costo_Item_Absorcion", "Botellas_Estimadas_Item_Absorcion", "Botellas_Restantes_Item_Absorcion", "Fecha_Item_Absorcion") VALUES (%s,%s,%s,%s,%s,%s)',
        (tipo, desc, num(f[136]) or 0, num(f[137]) or 0, num(f[139]) or 0, parse_fecha(f[138])))
    n_items += 1
resumen["Item_Absorcion"] = n_items  # el generico se agrega al final con totales

# =====================================================================
# 2. LOTES: Compra (MP) y Registro_Trabajador (T) desde TABLA MP/T/PI
#    (cols 23-30). Las filas PI de esta tabla solo aportan el restante.
# =====================================================================
compra_lote = {}      # 'MP0001AZBF11072021S2' -> Id_Compra
registro_lote = {}    # 'T0002CAARF...S5' -> Id_Registro_Trabajador
pi_restante = {}      # 'PI0002LIROF...S3I' -> cantidad restante
n_compras = n_registros = 0
for f in datos:
    cod, lote = f[23], f[25]
    if cod in (None, "") or lote in (None, ""):
        continue
    cod, lote = str(cod), str(lote)
    if cod.startswith("MP"):
        if cod not in mp_id:
            # codigo con hueco en el catalogo: crear la MP desde la propia compra
            mp_id[cod] = uno(
                'INSERT INTO "Materia_Prima" ("Descripcion_Materia_Prima", "Unidad_Materia_Prima", "Habilitado_Materia_Prima") VALUES (%s, %s, true) RETURNING "Id_Materia_Prima"',
                (str(f[26]).strip() if f[26] else cod, str(f[28]).strip() if f[28] else None))
            anota("mp_creada_desde_compra", cod)
        compra_lote[lote] = uno(
            'INSERT INTO "Compra" ("Id_Materia_Prima", "Fecha_Compra", "Cantidad_Compra", "Precio_Compra", "Cantidad_Restante_Compra", "Recibida_Compra") VALUES (%s,%s,%s,%s,%s,true) RETURNING "Id_Compra"',
            (mp_id[cod], parse_fecha(f[24]), num(f[27]) or 0, num(f[29]) or 0, num(f[30]) or 0))
        n_compras += 1
    elif cod.startswith("T0"):
        if cod not in trab_id:
            anota("registro_trab_sin_catalogo", cod)
            continue
        registro_lote[lote] = uno(
            'INSERT INTO "Registro_Trabajador" ("Id_Trabajador", "Fecha_Registro_Trabajador", "Horas_Registro_Trabajador", "Horas_Restante_Registro_Trabajador") VALUES (%s,%s,%s,%s) RETURNING "Id_Registro_Trabajador"',
            (trab_id[cod], parse_fecha(f[24]), num(f[27]) or 0, num(f[30]) or 0))
        n_registros += 1
    elif cod.startswith("PI"):
        pi_restante[lote] = num(f[30]) or 0
resumen["Compra"] = n_compras
resumen["Registro_Trabajador"] = n_registros

# =====================================================================
# 3. Produccion_Intermedio + detalles (UNIONES PI, cols 12-21)
# =====================================================================
lotes_pi = {}
for f in datos:
    lote = f[15]
    if lote in (None, ""):
        continue
    lote = str(lote)
    base = lote[:-1] if lote.endswith("I") else lote
    d = lotes_pi.setdefault(base, {"codigo": str(f[12]), "fecha": None, "cantidad": 0,
                                   "costo_u": 0, "horas": 0, "insumos": []})
    if d["fecha"] is None:
        d["fecha"] = parse_fecha(f[14]) or fecha_de_lote(base)
    ref, desc_ref, usado, inv, hrs = f[16], f[17], f[18], f[20], f[21]
    if desc_ref is not None and str(desc_ref).startswith("BOTELLA"):
        if num(usado):
            d["cantidad"] = num(usado)
        if num(inv):
            d["costo_u"] = num(inv)
    elif ref not in (None, ""):
        d["insumos"].append((str(ref), num(usado) or 0))
    if num(hrs):
        d["horas"] = max(d["horas"], num(hrs))

pi_lote = {}  # base y base+'I' -> Id_Produccion_Intermedio
det_pi_mp, det_pi_pi, det_pi_trab = [], [], []
for base in sorted(lotes_pi, key=seq_de_lote):
    d = lotes_pi[base]
    if d["codigo"] not in pi_id:
        anota("lote_pi_sin_catalogo", base)
        continue
    horas_trab = sum(u for r, u in d["insumos"] if r.startswith("T0"))
    horas = d["horas"] or horas_trab
    restante = pi_restante.get(base + "I", pi_restante.get(base, 0))
    id_nuevo = uno(
        'INSERT INTO "Produccion_Intermedio" ("Id_Producto_Intermedio", "Fecha_Produccion_Intermedio", "Cantidad_Producida", "Cantidad_Restante_Producida", "Costo_Unitario_Produccion_Intermedio", "Horas_Acumuladas") VALUES (%s,%s,%s,%s,%s,%s) RETURNING "Id_Produccion_Intermedio"',
        (pi_id[d["codigo"]], d["fecha"], d["cantidad"], restante, d["costo_u"], horas))
    pi_lote[base] = pi_lote[base + "I"] = id_nuevo
    for ref, usado in d["insumos"]:
        if ref.startswith("MP"):
            if ref in compra_lote:
                det_pi_mp.append((id_nuevo, compra_lote[ref], usado))
            else:
                anota("det_pi_mp_sin_lote", ref)
        elif ref.startswith("T0"):
            if ref in registro_lote:
                det_pi_trab.append((id_nuevo, registro_lote[ref], usado))
            else:
                anota("det_pi_trab_sin_lote", ref)
        elif ref.startswith("PI"):
            if ref in pi_lote:
                det_pi_pi.append((id_nuevo, pi_lote[ref], usado))
            else:
                anota("det_pi_pi_sin_lote", ref)
        else:
            anota("det_pi_ref_desconocida", ref)

lote_insert('INSERT INTO "Detalle_PI_Materia_Prima" ("Id_Produccion_Intermedio", "Id_Compra", "Cantidad_Usada") VALUES %s', det_pi_mp)
lote_insert('INSERT INTO "Detalle_PI_Trabajo" ("Id_Produccion_Intermedio", "Id_Registro_Trabajador", "Horas_Usadas") VALUES %s', det_pi_trab)
lote_insert('INSERT INTO "Detalle_PI_Intermedio" ("Id_Produccion_Intermedio", "Id_Produccion_Intermedio_Origen", "Cantidad_Usada") VALUES %s', det_pi_pi)
resumen["Produccion_Intermedio"] = len(pi_lote) // 2
resumen["Detalle_PI_Materia_Prima"] = len(det_pi_mp)
resumen["Detalle_PI_Trabajo"] = len(det_pi_trab)
resumen["Detalle_PI_Intermedio"] = len(det_pi_pi)

# =====================================================================
# 4. Produccion + detalles + absorcion (TABLA PT cols 46-52 + UNIONES PT cols 36-44)
# =====================================================================
# insumos por lote desde UNIONES PT
insumos_pt = defaultdict(list)   # lote -> [(ref, usado, monto_uoe)]
for f in datos:
    lote = f[39]
    if lote in (None, ""):
        continue
    lote = str(lote)
    ref, desc_ref, usado, pu = f[40], f[41], f[42], f[43]
    if desc_ref is not None and str(desc_ref).startswith("BOTELLA"):
        continue  # fila de salida: cantidad/PU ya vienen de TABLA PT
    if ref in (None, ""):
        continue
    insumos_pt[lote].append((str(ref), num(usado) or 0, num(pu) or 0))

prod_lote = {}
det_prod_mp, det_prod_pi, det_prod_trab, absorciones = [], [], [], []
n_prod = 0
for f in datos:
    lote, cod = f[46], f[47]
    if lote in (None, "") or cod in (None, ""):
        continue
    lote, cod = str(lote), str(cod)
    if cod not in pt_id:
        anota("lote_pt_sin_catalogo", lote)
        continue
    horas_trab = sum(u for r, u, _ in insumos_pt.get(lote, []) if r.startswith("T0"))
    id_nuevo = uno(
        'INSERT INTO "Produccion" ("Id_Producto_Terminado", "Fecha_Produccion", "Cantidad_Producida_Produccion", "Precio_Unitario_Producto_Terminado", "Cantidad_Restante_Produccion", "Horas_Acumuladas") VALUES (%s,%s,%s,%s,%s,%s) RETURNING "Id_Produccion"',
        (pt_id[cod], fecha_de_lote(lote), num(f[52]) or 0, num(f[49]) or 0, num(f[51]) or 0, horas_trab))
    prod_lote[lote] = id_nuevo
    n_prod += 1
    for ref, usado, monto in insumos_pt.get(lote, []):
        if ref.startswith("MP"):
            if ref in compra_lote:
                det_prod_mp.append((id_nuevo, compra_lote[ref], usado))
            else:
                anota("det_prod_mp_sin_lote", ref)
        elif ref.startswith("T0"):
            if ref in registro_lote:
                det_prod_trab.append((id_nuevo, registro_lote[ref], usado))
            else:
                anota("det_prod_trab_sin_lote", ref)
        elif ref.startswith("PI"):
            if ref in pi_lote:
                det_prod_pi.append((id_nuevo, pi_lote[ref], usado))
            else:
                anota("det_prod_pi_sin_lote", ref)
        elif ref == "UOE":
            absorciones.append((id_nuevo, usado, monto))
        else:
            anota("det_prod_ref_desconocida", ref)

# item generico para las absorciones historicas
if absorciones:
    total_monto = sum(m for _, _, m in absorciones)
    total_bot = sum(b for _, b, _ in absorciones)
    id_item_gen = uno(
        'INSERT INTO "Item_Absorcion" ("Tipo_Item_Absorcion", "Descripcion_Item_Absorcion", "Costo_Item_Absorcion", "Botellas_Estimadas_Item_Absorcion", "Botellas_Restantes_Item_Absorcion", "Fecha_Item_Absorcion") VALUES (%s,%s,%s,%s,0,%s) RETURNING "Id_Item_Absorcion"',
        ("UTENSILIO", "ABSORCION HISTORICA (MIGRACION EXCEL)", total_monto, total_bot,
         min(fecha_de_lote(l) for l in prod_lote)))
    lote_insert(
        'INSERT INTO "Absorcion_Produccion" ("Id_Item_Absorcion", "Id_Produccion", "Botellas_Absorbidas", "Monto_Absorbido") VALUES %s',
        [(id_item_gen, idp, b, m) for idp, b, m in absorciones])

lote_insert('INSERT INTO "Detalle_Prod_Materia_Prima" ("Id_Produccion", "Id_Compra", "Cantidad_Usada") VALUES %s', det_prod_mp)
lote_insert('INSERT INTO "Detalle_Prod_Trabajador" ("Id_Produccion", "Id_Registro_Trabajador", "Horas_Usadas") VALUES %s', det_prod_trab)
lote_insert('INSERT INTO "Detalle_Prod_Intermedio" ("Id_Produccion", "Id_Produccion_Intermedio", "Cantidad_Usada") VALUES %s', det_prod_pi)
resumen["Produccion"] = n_prod
resumen["Detalle_Prod_Materia_Prima"] = len(det_prod_mp)
resumen["Detalle_Prod_Trabajador"] = len(det_prod_trab)
resumen["Detalle_Prod_Intermedio"] = len(det_prod_pi)
resumen["Absorcion_Produccion"] = len(absorciones)

# =====================================================================
# 5. Ventas (cols 73-81): agrupar lineas por (cliente, fecha) -> Venta
# =====================================================================
ventas_agrupadas = defaultdict(list)
for f in datos:
    cli = f[73]
    if cli in (None, ""):
        continue
    cli = str(cli).strip()
    fecha = f[81] if isinstance(f[81], (datetime.date, datetime.datetime)) else None
    fecha = parse_fecha(fecha) if fecha else parse_fecha(f[80])
    if fecha is None:
        anota("venta_sin_fecha", f[74])
        continue
    ventas_agrupadas[(cli, fecha)].append(
        (str(f[74]), num(f[78]) or 0, num(f[77]) or 0, num(f[79])))

n_ventas = n_det_ventas = 0
for (cli, fecha), lineas in sorted(ventas_agrupadas.items(), key=lambda kv: kv[0][1]):
    if cli not in cliente_id:
        cliente_id[cli] = uno(
            'INSERT INTO "Cliente" ("Nombre_Cliente", "Licoreria_Cliente", "Habilitado_Cliente") VALUES (%s, %s, true) RETURNING "Id_Cliente"',
            (cli[:60], cli))
        anota("cliente_creado_desde_ventas", cli)
    detalles = []
    taxi = 0.0
    for lote, cantidad, pv, total in lineas:
        if lote not in prod_lote:
            anota("venta_lote_sin_produccion", lote)
            continue
        detalles.append((prod_lote[lote], cantidad, pv))
        # PV es el precio de lista y TOTAL lo que realmente cobro el reparto:
        # cuando difieren, la diferencia es el taxi ya prorrateado entre las
        # botellas de esa entrega. Se acumula por venta -que es donde vive el
        # taxi en V2 (Venta.Taxi_Venta, migracion 027)- y el precio por linea
        # se guarda BRUTO (decision 3.9). En las filas donde el precio ya venia
        # prorrateado, TOTAL == PV*CANTIDAD y esto da 0: el taxi de esas ventas
        # es irrecuperable, quedo dentro del propio PV.
        if total is not None:
            taxi += cantidad * pv - total
    if not detalles:
        continue
    if taxi < 0:
        # TOTAL mayor que PV*CANTIDAD no es un taxi: es un recargo o un error
        # de tipeo del excel. Se ignora en vez de escribir un taxi negativo.
        anota("venta_total_mayor_que_bruto", f"{cli[:40]} {fecha}")
        taxi = 0.0
    id_venta = uno(
        'INSERT INTO "Venta" ("Id_Cliente", "Fecha_Venta", "Taxi_Venta") VALUES (%s, %s, %s) RETURNING "Id_Venta"',
        (cliente_id[cli], fecha, round(taxi, 2)))
    lote_insert('INSERT INTO "Detalle_Venta" ("Id_Venta", "Id_Produccion", "Cantidad_Venta", "Precio_Venta_Real") VALUES %s',
                [(id_venta, idp, c, p) for idp, c, p in detalles])
    n_ventas += 1
    n_det_ventas += len(detalles)
resumen["Venta"] = n_ventas
resumen["Detalle_Venta"] = n_det_ventas

# =====================================================================
# 5b. Reparar lotes de producto terminado que el Excel dejo en negativo.
#
# El Excel no validaba stock: su macro podia descontar una venta de un lote
# ya agotado, dejandolo en negativo, y no descontarla del lote que si tenia
# las botellas (que queda inflado). La venta es un hecho -el cliente se llevo
# las botellas-; lo que estaba mal es a que lote se le atribuye.
#
# Se reasigna en orden cronologico: las ventas que caen despues de agotar la
# capacidad del lote pasan al siguiente lote del mismo producto que tenga
# stock. Importa para el balance, que valoriza el restante de cada lote: un
# lote inflado sobrevalora el patrimonio (el negativo, en cambio, ya lo
# ignora el filtro > UMBRAL_STOCK_MINIMO).
#
# Solo producto terminado: en materia prima / jornadas / intermedios los
# negativos se dejan como estan (el balance los ignora y no inflan nada).
#
# Se mueven lineas de venta enteras. Si el corte no cae justo en el limite de
# una linea, se mueve la linea completa: el resultado sigue siendo coherente
# (el restante se recalcula desde las ventas reales), solo que el reparto
# entre los dos lotes queda aproximado. Queda logueado para poder revisarlo.
# =====================================================================
cur.execute("""
    SELECT "Id_Produccion", "Id_Producto_Terminado", "Fecha_Produccion",
           "Cantidad_Producida_Produccion"
    FROM "Produccion" WHERE "Cantidad_Restante_Produccion" < 0
    ORDER BY "Fecha_Produccion"
""")
for id_origen, id_pt, fecha_lote, producido in cur.fetchall():
    cur.execute("""
        SELECT d."Id_Detalle_Venta", d.acum FROM (
            SELECT dv."Id_Detalle_Venta",
                   SUM(dv."Cantidad_Venta") OVER (
                       ORDER BY v."Fecha_Venta", dv."Id_Detalle_Venta") AS acum
            FROM "Detalle_Venta" dv JOIN "Venta" v ON v."Id_Venta" = dv."Id_Venta"
            WHERE dv."Id_Produccion" = %s
        ) d WHERE d.acum > %s ORDER BY d.acum
    """, (id_origen, producido))
    exceso = cur.fetchall()
    cur.execute("""
        SELECT "Id_Produccion" FROM "Produccion"
        WHERE "Id_Producto_Terminado" = %s AND "Fecha_Produccion" >= %s
          AND "Id_Produccion" <> %s AND "Cantidad_Restante_Produccion" > 0
        ORDER BY "Fecha_Produccion" LIMIT 1
    """, (id_pt, fecha_lote, id_origen))
    destino = cur.fetchone()
    if not exceso or not destino:
        anota("lote_pt_negativo_sin_lote_destino", id_origen)
        continue
    id_destino = destino[0]
    for id_detalle, _ in exceso:
        cur.execute('UPDATE "Detalle_Venta" SET "Id_Produccion" = %s WHERE "Id_Detalle_Venta" = %s',
                    (id_destino, id_detalle))
    # El restante deja de venir del Excel: se deriva de las ventas reales.
    for id_p in (id_origen, id_destino):
        cur.execute("""
            UPDATE "Produccion" p SET "Cantidad_Restante_Produccion" =
                p."Cantidad_Producida_Produccion" - COALESCE((
                    SELECT SUM(dv."Cantidad_Venta") FROM "Detalle_Venta" dv
                    WHERE dv."Id_Produccion" = p."Id_Produccion"), 0)
            WHERE p."Id_Produccion" = %s
        """, (id_p,))
    anota("lote_pt_negativo_reparado",
          f"lote {id_origen} -> {id_destino}: {len(exceso)} ventas movidas")

# =====================================================================
# 6. Prorrateo gastos extra (cols 94-102) -> Horas_Producto_Mes,
#    Gasto_Extra_Mes, Prorrateo_Mensual
# =====================================================================
hpm_id = {}
gem = {}          # (cod_ge, anio_mes) -> [monto_total, fecha_pago]
prorrateos = []   # (cod_p, anio_mes, cod_ge, monto)
for f in datos:
    periodo = f[94]
    if periodo in (None, "") or not isinstance(periodo, (datetime.date, datetime.datetime)):
        continue
    anio_mes = periodo.strftime("%Y-%m")
    cod_p, horas, cod_ge, monto = f[97], num(f[99]) or 0, f[100], num(f[102]) or 0
    if cod_p not in pt_id or cod_ge not in ge_id:
        anota("prorrateo_codigo_desconocido", f"{cod_p}/{cod_ge}")
        continue
    clave_h = (cod_p, anio_mes)
    if clave_h not in hpm_id:
        hpm_id[clave_h] = uno(
            'INSERT INTO "Horas_Producto_Mes" ("Id_Producto_Terminado", "Anio_Mes", "Horas_Producto_Mes") VALUES (%s,%s,%s) RETURNING "Id_Horas_Producto_Mes"',
            (pt_id[cod_p], anio_mes, horas))
    clave_g = (cod_ge, anio_mes)
    fecha_pago = parse_fecha(f[95]) or parse_fecha(f[96])
    if clave_g not in gem:
        gem[clave_g] = [0, fecha_pago]
    gem[clave_g][0] += monto
    if fecha_pago and (gem[clave_g][1] is None or fecha_pago > gem[clave_g][1]):
        gem[clave_g][1] = fecha_pago
    prorrateos.append((hpm_id[clave_h], ge_id[cod_ge], monto))

for (cod_ge, anio_mes), (monto, fecha_pago) in gem.items():
    cur.execute(
        'INSERT INTO "Gasto_Extra_Mes" ("Id_Gasto_Extra", "Anio_Mes", "Monto_Gasto_Extra_Mes", "Fecha_Pago_Gasto_Extra_Mes") VALUES (%s,%s,%s,%s)',
        (ge_id[cod_ge], anio_mes, round(monto, 2), fecha_pago))
lote_insert('INSERT INTO "Prorrateo_Mensual" ("Id_Horas_Producto_Mes", "Id_Gasto_Extra", "Gasto_Extra_Asignado") VALUES %s', prorrateos)
resumen["Horas_Producto_Mes"] = len(hpm_id)
resumen["Gasto_Extra_Mes"] = len(gem)
resumen["Prorrateo_Mensual"] = len(prorrateos)

# =====================================================================
# 7. Bloques de dinero: gastos familiares y amortizacion de deudas.
#    Cada bloque son 6+ filas: 6 cuentas a la izquierda (con DISPONIBLE y
#    UTILIZADO) y lineas de gasto a la derecha, cerradas por TOTAL.
# =====================================================================
snapshot_saldo = {}   # nombre cuenta -> (fecha, saldo)


def registrar_snapshot(nombre, fecha, valor):
    if valor is None or fecha is None:
        return
    n = ALIAS_CUENTA.get(str(nombre).strip(), str(nombre).strip())
    if n not in cuenta_id:
        return
    if n not in snapshot_saldo or fecha >= snapshot_saldo[n][0]:
        snapshot_saldo[n] = (fecha, valor)


def procesar_bloques(col_fuente, col_disp, col_util, col_espec, col_bs, col_fecha, col_grupo=None):
    """Devuelve lista de bloques: (fecha, [(cuenta, monto_utilizado)], [(espec, bs, grupo)])."""
    bloques, actual = [], None
    for f in datos:
        fuente = f[col_fuente]
        if fuente is not None and str(fuente).strip() == CUENTA_MARCADOR_BLOQUE:
            if actual:
                bloques.append(actual)
            actual = {"cuentas": [], "lineas": [], "fecha": None}
        if actual is None:
            continue
        fila_vacia = all(f[c] in (None, "") for c in
                         ([col_fuente, col_disp, col_util, col_espec, col_bs, col_fecha] +
                          ([col_grupo] if col_grupo is not None else [])))
        if fila_vacia:
            continue
        fecha = parse_fecha(f[col_fecha]) if f[col_fecha] not in (None, "") else None
        if fecha and actual["fecha"] is None:
            actual["fecha"] = fecha
        if fuente is not None:
            nombre = str(fuente).strip()
            if nombre in cuenta_id:
                if num(f[col_disp]) is not None:
                    registrar_snapshot(nombre, fecha or actual["fecha"], num(f[col_disp]))
                if num(f[col_util]):
                    actual["cuentas"].append([nombre, num(f[col_util])])
        espec = f[col_espec]
        if espec not in (None, "") and str(espec).strip().upper() != "TOTAL":
            bs = num(f[col_bs])
            if bs and bs > 0:
                grupo = str(f[col_grupo]).strip() if (col_grupo is not None and f[col_grupo] not in (None, "")) else None
                actual["lineas"].append((str(espec).strip(), bs, grupo, fecha))
    if actual:
        bloques.append(actual)
    return bloques


def asignar_greedy(bloque, clave_anomalia):
    """Asigna cada linea de gasto a una cuenta en orden hasta agotar lo utilizado."""
    cuentas = [list(c) for c in bloque["cuentas"]]
    if not cuentas:
        cuentas = [[CUENTA_FALLBACK, float("inf")]]
        anota(clave_anomalia + "_sin_cuenta")
    idx, resultado = 0, []
    for espec, bs, grupo, fecha in bloque["lineas"]:
        while idx < len(cuentas) - 1 and cuentas[idx][1] <= 0.005:
            idx += 1
        cuentas[idx][1] -= bs
        resultado.append((cuentas[idx][0], espec, bs, grupo, fecha or bloque["fecha"]))
    return resultado


# --- gastos familiares (cols 111-117) -> Movimiento SALIDA ---
movs_gastos = []
for bloque in procesar_bloques(111, 112, 113, 114, 115, 116, 117):
    for cuenta, espec, bs, grupo, fecha in asignar_greedy(bloque, "gasto_familiar"):
        movs_gastos.append((fecha, "SALIDA", cuenta_id[cuenta], None, bs, espec,
                            grupo_id.get(grupo)))
lote_insert(
    'INSERT INTO "Movimiento" ("Fecha_Movimiento", "Tipo_Movimiento", "Id_Cuenta_Origen", "Id_Cuenta_Destino", "Monto_Movimiento", "Descripcion_Movimiento", "Id_Grupo_Movimiento") VALUES %s',
    movs_gastos)
resumen["Movimiento (gastos familiares)"] = len(movs_gastos)

# --- amortizacion de deudas (cols 119-124) -> Movimiento PAGO_DEUDA + Movimiento_Deuda ---
n_pagos_deuda = 0
for bloque in procesar_bloques(119, 120, 121, 122, 123, 124):
    for cuenta, espec, bs, _, fecha in asignar_greedy(bloque, "amortizacion"):
        clave = espec.upper()
        if clave not in deuda_id:
            deuda_id[clave] = uno(
                'INSERT INTO "Deuda" ("Descripcion_Deuda", "Saldo_Actual_Deuda") VALUES (%s, 0) RETURNING "Id_Deuda"',
                (espec,))
            anota("deuda_creada_desde_amortizacion", espec)
        cur.execute(
            'INSERT INTO "Movimiento" ("Fecha_Movimiento", "Tipo_Movimiento", "Id_Cuenta_Origen", "Monto_Movimiento", "Descripcion_Movimiento") VALUES (%s,%s,%s,%s,%s)',
            (fecha, "PAGO_DEUDA", cuenta_id[cuenta], bs, f"Pago deuda {espec}"))
        cur.execute(
            'INSERT INTO "Movimiento_Deuda" ("Id_Deuda", "Fecha_Movimiento_Deuda", "Tipo_Movimiento_Deuda", "Monto_Movimiento_Deuda", "Id_Cuenta_Pago") VALUES (%s,%s,%s,%s,%s)',
            (deuda_id[clave], fecha, "PAGO", bs, cuenta_id[cuenta]))
        n_pagos_deuda += 1
resumen["Movimiento_Deuda (pagos)"] = n_pagos_deuda

# =====================================================================
# 8. Transacciones (cols 126-131): TRANSFERENCIA o INGRESO_EXTERNO.
#    Filas 'ACTUAL' = snapshot de saldo del destino.
# =====================================================================
n_transf = n_ingresos = 0
for f in datos:
    origen, monto, destino, fecha = f[126], f[128], f[129], parse_fecha(f[131])
    if origen in (None, "") or destino in (None, ""):
        continue
    origen, destino = str(origen).strip(), str(destino).strip()
    id_destino = cuenta_de(destino)
    if id_destino is None:
        anota("transaccion_destino_desconocido", destino)
        continue
    if str(monto).strip().upper() == "ACTUAL":
        registrar_snapshot(ALIAS_CUENTA.get(destino, destino), fecha, num(f[130]))
        continue
    monto_n = num(monto)
    if not monto_n or monto_n <= 0:
        anota("transaccion_monto_invalido", monto)
        continue
    id_origen = cuenta_de(origen)
    if id_origen:
        cur.execute(
            'INSERT INTO "Movimiento" ("Fecha_Movimiento", "Tipo_Movimiento", "Id_Cuenta_Origen", "Id_Cuenta_Destino", "Monto_Movimiento", "Descripcion_Movimiento") VALUES (%s,%s,%s,%s,%s,%s)',
            (fecha, "TRANSFERENCIA", id_origen, id_destino, monto_n, f"Transferencia {origen} -> {destino}"))
        n_transf += 1
    else:
        cur.execute(
            'INSERT INTO "Movimiento" ("Fecha_Movimiento", "Tipo_Movimiento", "Id_Cuenta_Destino", "Monto_Movimiento", "Descripcion_Movimiento") VALUES (%s,%s,%s,%s,%s)',
            (fecha, "INGRESO_EXTERNO", id_destino, monto_n, origen))
        n_ingresos += 1
resumen["Movimiento (transferencias)"] = n_transf
resumen["Movimiento (ingresos externos)"] = n_ingresos

# =====================================================================
# 9. Saldos de cuenta: ultimo snapshot conocido del excel
# =====================================================================
print("\nSaldos finales (ultimo snapshot del excel):")
for nombre, id_c in cuenta_id.items():
    if nombre in snapshot_saldo:
        fecha, saldo = snapshot_saldo[nombre]
        cur.execute('UPDATE "Cuenta" SET "Saldo_Actual_Cuenta" = %s WHERE "Id_Cuenta" = %s', (saldo, id_c))
        print(f"  {nombre:32s} = {saldo:>12,.2f}  (al {fecha})")
    else:
        print(f"  {nombre:32s} = sin snapshot, queda en 0")

# =====================================================================
# Resumen y cierre
# =====================================================================
print("\n===== RESUMEN DE CARGA =====")
for k, v in resumen.items():
    print(f"  {k:38s} {v:>8}")
print("\n===== ANOMALIAS =====")
if not anomalias:
    print("  (ninguna)")
for k in sorted(anomalias):
    print(f"  {k:38s} {anomalias[k]:>8}   ej: {'; '.join(ejemplos_anomalias[k])}")

if DRY_RUN:
    con.rollback()
    print("\n--dry-run: ROLLBACK, no se guardo nada.")
else:
    con.commit()
    print("\nCOMMIT: migracion guardada.")
con.close()
