# Reportes en Power BI

Los dashboards de análisis (histórico, exploratorio) viven acá; el frontend web
se queda con lo **operativo** del día a día (registrar, validar, balance,
resumen diario). Criterio de reparto en MEJORAS_FUTURAS.md 8.1.

## Qué se versiona y qué no

**Se versiona:** este README (conexión + medidas DAX + cómo armar cada visual).
Eso es lo reutilizable: si se pierde el `.pbix`, con esto se reconstruye.

**NO se versiona el `.pbix`** (está en `.gitignore`). En modo *Importar*, Power
BI guarda una **copia completa de los datos** dentro del archivo: sería meter
ventas, clientes y deudas reales en un blob binario, versionado para siempre en
el historial de git — el mismo problema que `datos_reales/`, pero peor porque no
se puede diffear ni borrar del historial fácilmente.

Si algún día se quiere versionar el diseño del reporte (layout, visuales), existe
el formato **Power BI Project (.pbip)**, que guarda todo como carpeta de
JSON/texto y sin datos embebidos. Ese sí podría entrar al repo. No hace falta
para empezar.

## Conexión

Power BI se conecta con un usuario de PostgreSQL **de solo lectura**
(`powerbi_lectura`), no con el usuario de la app. Si algo sale mal en el reporte,
no puede tocar un dato: solo tiene `SELECT`.

| Campo | Valor |
|---|---|
| Servidor | `localhost:5432` |
| Base de datos | `fabrica_V2` |
| Modo | **Importar** (no DirectQuery) |
| Autenticación | Base de datos |
| Usuario | `powerbi_lectura` |
| Contraseña | *(la definida al crear el rol — a propósito no está acá)* |

La contraseña no se versiona por la misma razón que `.env`: este repo va a
GitHub (8.5). Si se pierde, se cambia con
`ALTER ROLE powerbi_lectura WITH PASSWORD '...';`.

**Por qué Importar y no DirectQuery:** con este volumen (miles de filas, no
millones) importar es más rápido para armar medidas y no depende de que la base
esté levantada. Se actualiza con el botón *Actualizar*. DirectQuery tiene sentido
con datos enormes o necesidad de tiempo real; no es el caso.

El rol se creó así (documentado por si hay que rehacerlo):

```sql
CREATE ROLE powerbi_lectura WITH LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE "fabrica_V2" TO powerbi_lectura;   -- comillas: la BD tiene mayúscula
GRANT USAGE ON SCHEMA public TO powerbi_lectura;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_lectura;
-- para que las tablas de migraciones futuras también queden visibles:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO powerbi_lectura;
```

---

# Dashboard 1 — Pareto 80/20 de rentabilidad

*¿Qué 20% de los productos deja el 80% de la ganancia?*

## Tablas a cargar

`Venta`, `Detalle_Venta`, `Produccion`, `Producto_Terminado`,
`Prorrateo_Mensual`, `Horas_Producto_Mes`.

Verificar que Power BI haya detectado estas relaciones (Modelo → vista de
relaciones). Todas son *muchos a uno*, dirección simple:

```
Detalle_Venta[Id_Venta]              → Venta[Id_Venta]
Detalle_Venta[Id_Produccion]         → Produccion[Id_Produccion]
Produccion[Id_Producto_Terminado]    → Producto_Terminado[Id_Producto_Terminado]
Horas_Producto_Mes[Id_Producto_Terminado] → Producto_Terminado[Id_Producto_Terminado]
Prorrateo_Mensual[Id_Horas_Producto_Mes]  → Horas_Producto_Mes[Id_Horas_Producto_Mes]
```

## Qué mide cada cosa (y por qué NO es el "saldo" de la app)

La app tiene su propio acumulador por producto (`saldo-productos`, mejora 2.C),
pero **mide otra cosa** y es correcto que no coincida:

| | Qué resta | Qué responde |
|---|---|---|
| **Saldo** (app, para el 70/30) | costo de **todo lo producido**, incluido el stock sin vender | ¿ya recuperó la plata que puse? → recuperación de capital |
| **Ganancia** (este Pareto) | costo de **solo lo vendido** | ¿cuánto gané con lo que vendí? → rentabilidad |

Qué hay dentro de `Produccion[Precio_Unitario_Producto_Terminado]` (el costo del
lote): materia prima + trabajo + **absorción de utensilios/feriados** (1.4).
Qué **no** hay: los gastos extra mensuales (luz, agua, internet, impuestos) —
esos solo viven en `Prorrateo_Mensual`. Por eso restarlos en el margen neto **no**
es doble conteo.

El costo es **exacto, no un promedio**: cada línea de venta apunta al lote del que
salió (`Detalle_Venta[Id_Produccion]`), así que se sabe qué costó *esa* botella.

## Tabla de selector (para alternar bruto/neto)

Inicio → **Escribir datos**. Tabla llamada `Métrica`, una sola columna `Métrica`,
dos filas:

```
Margen bruto
Margen neto
```

No se relaciona con nada (es una tabla desconectada): solo sirve para que el
usuario elija y `SWITCH` reaccione.

## Medidas DAX

```dax
Ingresos =
SUMX (
    'Detalle_Venta',
    'Detalle_Venta'[Cantidad_Venta] * 'Detalle_Venta'[Precio_Venta_Real]
)
```

```dax
Costo de lo vendido =
SUMX (
    'Detalle_Venta',
    'Detalle_Venta'[Cantidad_Venta]
        * RELATED ( 'Produccion'[Precio_Unitario_Producto_Terminado] )
)
```

```dax
Margen bruto = [Ingresos] - [Costo de lo vendido]
```

```dax
Gastos extra asignados = SUM ( 'Prorrateo_Mensual'[Gasto_Extra_Asignado] )
```

```dax
Margen neto = [Margen bruto] - [Gastos extra asignados]
```

La medida que obedece al selector. Todo el resto del Pareto usa **esta**, así que
el gráfico entero cambia con un clic:

```dax
Ganancia =
SWITCH (
    SELECTEDVALUE ( 'Métrica'[Métrica], "Margen bruto" ),
    "Margen neto", [Margen neto],
    [Margen bruto]
)
```

Acumulado del Pareto: por cada producto, la suma de su ganancia y la de todos los
que ganan **más** que él (o sea, el acumulado leyendo de mayor a menor):

```dax
Ganancia acumulada =
VAR GananciaActual = [Ganancia]
VAR Tabla =
    ADDCOLUMNS (
        ALLSELECTED ( 'Producto_Terminado'[Descripcion_Producto_Terminado] ),
        "@Ganancia", [Ganancia]
    )
RETURN
    IF (
        NOT ISBLANK ( GananciaActual ),
        SUMX ( FILTER ( Tabla, [@Ganancia] >= GananciaActual ), [@Ganancia] )
    )
```

```dax
% acumulado =
VAR Total =
    SUMX (
        ALLSELECTED ( 'Producto_Terminado'[Descripcion_Producto_Terminado] ),
        [Ganancia]
    )
RETURN
    DIVIDE ( [Ganancia acumulada], Total )
```

Formato de `% acumulado`: **Porcentaje, 1 decimal**.

KPI para una tarjeta ("cuántos productos hacen el 80%"):

```dax
Productos hasta el 80% =
VAR TablaBase =
    ADDCOLUMNS (
        ALLSELECTED ( 'Producto_Terminado'[Descripcion_Producto_Terminado] ),
        "@Ganancia", [Ganancia]
    )
VAR Total = SUMX ( TablaBase, [@Ganancia] )
VAR ConAcum =
    ADDCOLUMNS (
        TablaBase,
        "@Acum",
            VAR G = [@Ganancia]
            RETURN SUMX ( FILTER ( TablaBase, [@Ganancia] >= G ), [@Ganancia] )
    )
RETURN
    COUNTROWS ( FILTER ( ConAcum, DIVIDE ( [@Acum], Total ) < 0.8 ) ) + 1
```

## Armar el visual

1. Visual: **Gráfico de líneas y columnas apiladas**.
2. **Eje X:** `Producto_Terminado[Descripcion_Producto_Terminado]`
3. **Eje de columnas:** `[Ganancia]`
4. **Eje de líneas:** `[% acumulado]`
5. **Ordenar** el visual por `[Ganancia]`, **descendente** ← sin esto el Pareto no
   tiene sentido: la curva acumulada asume orden de mayor a menor.
6. **Línea del 80%:** panel *Análisis* → *Línea constante* en el eje de líneas,
   valor `0.8`.
7. **Segmentación** (slicer) con `Métrica[Métrica]` para alternar bruto/neto.
8. Tarjeta con `[Productos hasta el 80%]`.

Con muchos productos el eje X queda apretado: conviene un filtro visual *Top N*
por `[Ganancia]` (ej. Top 25) para leerlo, o dejar el scroll.

## Cómo saber que las medidas están bien

El margen bruto en DAX y en SQL leen la misma base, así que **tienen que dar el
mismo número**. Corré esta consulta con `psql` (o pgAdmin) y compará el total
contra `[Margen bruto]` sin filtros en Power BI — si coinciden, la medida está
bien. La consulta no lleva datos, solo nombres de tablas/columnas (que ya están
en el esquema del repo):

```sql
SELECT ROUND(SUM(dv."Cantidad_Venta"
        * (dv."Precio_Venta_Real" - p."Precio_Unitario_Producto_Terminado")), 2)
FROM "Detalle_Venta" dv
JOIN "Produccion" p ON p."Id_Produccion" = dv."Id_Produccion";
```

Para el margen neto, restarle a ese total `SUM("Gasto_Extra_Asignado")` de
`Prorrateo_Mensual`. Para el KPI de "productos hasta el 80%", ordenar los
productos por ganancia descendente y contar hasta llegar al 80% acumulado.

Qué mirar cuando lo tengas armado (sin poner los valores acá, salen de tu
propia base):

- El Pareto debería mostrar la forma clásica: unos pocos productos a la
  izquierda con barras altas, y la curva de % acumulado subiendo rápido y
  aplanándose. La tarjeta de "productos hasta el 80%" te dice el número exacto.
- Al cambiar el selector de bruto a neto, **algunos productos cambian de
  puesto** — no es cosmético. Un producto que vende mucho volumen consume
  muchas horas de fábrica, así que carga más gastos extra y puede caer varios
  puestos en el margen neto. Fijate cuáles se mueven: son los que "parecen"
  rentables pero se comen la fábrica en luz/agua/trabajo.

## Limitación conocida del margen neto

El prorrateo asigna los gastos extra por **horas producidas** en el mes — incluye
las botellas que siguen en stock. El margen, en cambio, es de lo **vendido**. Así
que el margen neto le carga a cada producto gastos de botellas que todavía no
vendió. Con el histórico completo pesa poco (el stock es una fracción chica de lo
vendido), pero al cortar por mes puede distorsionar un mes de mucha producción y
poca venta.
Si molesta, la corrección sería prorratear el gasto por botella y multiplicar por
las botellas vendidas.

---

# Tabla Calendario (base para los dashboards 2 a 4)

Power BI no corta bien por mes/año usando directamente una fecha de una tabla
de hechos (`Venta[Fecha_Venta]`, `Balance[Fecha_Balance]`): hace falta una
tabla de fechas dedicada, marcada como tal, para que el *time intelligence*
(comparar mes contra mes, año contra año) funcione. Se arma una sola vez y la
usan los tres dashboards siguientes.

## Crear la tabla

Modelado → **Nueva tabla**:

```dax
Calendario =
VAR PrimeraFecha = MIN ( 'Venta'[Fecha_Venta] )
VAR UltimaFecha = MAX ( TODAY (), MAX ( 'Venta'[Fecha_Venta] ) )
RETURN
    CALENDAR ( PrimeraFecha, UltimaFecha )
```

Se calcula sola desde la fecha más vieja de `Venta` hasta hoy — no hace falta
escribir ninguna fecha a mano ni saber de antemano desde cuándo hay datos.

Columnas de apoyo (Modelado → **Nueva columna**, sobre `Calendario`):

```dax
Año = YEAR ( 'Calendario'[Fecha] )
```
```dax
Mes = MONTH ( 'Calendario'[Fecha] )
```
```dax
Nombre Mes = FORMAT ( 'Calendario'[Fecha], "MMMM" )
```
```dax
Año-Mes = FORMAT ( 'Calendario'[Fecha], "YYYY-MM" )
```

⚠️ **Importantísimo — sin esto, cualquier gráfico que use `Año-Mes` o
`Nombre Mes` como eje puede quedar ordenado mal (no por fecha).** `Año-Mes` y
`Nombre Mes` son texto (`FORMAT` devuelve texto). Power BI, si no le decís
explícitamente por qué otra columna ordenar un campo de texto, en un gráfico
de líneas puede terminar ordenando el eje **por el valor de una medida** (de
mayor a menor) en vez de por la fecha. El síntoma es exactamente el que se ve
al armar el gráfico de evolución: el eje muestra los meses salteados sin
ningún orden cronológico, y la línea conecta los puntos en cualquier orden —
no es que los datos estén mal, es que el eje no respeta la fecha.

Se arregla con una columna de apoyo numérica (esta sí queda "fea" a propósito,
nunca se muestra, solo ordena):

```dax
Año-Mes (orden) = YEAR ( 'Calendario'[Fecha] ) * 100 + MONTH ( 'Calendario'[Fecha] )
```

(da `202109` para septiembre de 2021, `202201` para enero de 2022— ordena
bien como número aunque el texto no lo haría).

Después, en **Vista de modelo** (el ícono de la izquierda con las tablas
conectadas, no la vista de informe):

1. Click en la tabla `Calendario`, seleccioná la columna `Año-Mes`.
2. Arriba aparece la pestaña **Herramientas de columna** → botón
   **Ordenar por columna** → elegí `Año-Mes (orden)`.
3. Repetí para `Nombre Mes` → **Ordenar por columna** → elegí `Mes` (ya
   existe, es 1-12, no hace falta crear nada nuevo para este).

Esto se configura **una sola vez, a nivel del modelo** — no por cada gráfico.
Una vez hecho, todos los visuales que ya usan `Año-Mes` o `Nombre Mes` (los
que armaste y los que armes después) se ordenan solos, correctamente, sin
tocar nada en cada uno.

Arreglo rápido mientras tanto (por si querés confirmar el efecto antes de
crear la columna): en el gráfico de líneas, `...` (esquina superior derecha
del visual) → **Ordenar por** → `Año-Mes` → ascendente. Es un parche por
visual, no dura si armás un gráfico nuevo — por eso el arreglo de fondo es el
de arriba.

## Marcarla como tabla de fechas

Clic derecho en `Calendario` → **Marcar como tabla de fechas** → columna
`Fecha`. Sin este paso el `SWITCH`/time intelligence de más abajo no funciona
bien (Power BI necesita saber cuál es "la" columna de fecha continua, sin
huecos).

## Relación

```
Calendario[Fecha] (1)  →  Venta[Fecha_Venta] (muchos)
```

Con esto, cualquier medida que dependa de `Detalle_Venta` (como `[Ingresos]` o
`[Margen bruto]` del Pareto) queda automáticamente cortable por
`Calendario[Año]` / `[Año-Mes]`, porque el filtro se propaga en cadena:
`Calendario → Venta → Detalle_Venta → Produccion`.

---

# Dashboard 2 — Producto más vendido / con más margen por período

*¿Cuál es el producto que más se vendió (en cantidad) y cuál dejó más
margen, en un mes/año dado?*

## Tablas a cargar

Ninguna nueva: reusa `Venta`, `Detalle_Venta`, `Produccion`,
`Producto_Terminado` del Dashboard 1, más la tabla `Calendario` de arriba.

## Medida nueva

```dax
Cantidad Vendida = SUM ( 'Detalle_Venta'[Cantidad_Venta] )
```

El margen ya existe: reusa `[Margen bruto]` (o `[Ganancia]`, si querés que
también respete el selector bruto/neto del Dashboard 1).

## Armar el visual

1. Segmentación (slicer) con `Calendario[Año]` y otra con
   `Calendario[Nombre Mes]` (o un slicer de tipo *Entre* sobre `Calendario[Fecha]`
   si preferís un rango libre en vez de mes calendario).
2. Un **gráfico de barras**: eje `Producto_Terminado[Descripcion_Producto_Terminado]`,
   valor `[Cantidad Vendida]`, ordenado descendente, filtro visual *Top N* (ej.
   Top 10) — responde "más vendido".
3. Otro **gráfico de barras** igual pero con `[Margen bruto]` — responde "con
   más margen". No van a coincidir necesariamente: el más vendido no siempre es
   el más rentable (ver la tabla de comparación bruto/neto del Dashboard 1).
4. Opcional: una tarjeta con `[Cantidad Vendida]` y otra con `[Margen bruto]`
   totales del período filtrado, para ver el tamaño del mes de un vistazo.
5. **Evolución en el tiempo (no es un ranking, es una tendencia):** dos
   gráficos de **líneas**, uno con eje `Calendario[Año-Mes]` y otro con eje
   `Calendario[Año]`, ambos con `[Cantidad Vendida]` y `[Margen bruto]` como
   líneas. Responde "¿cómo viene la fábrica en el tiempo?", en vez de "¿qué
   producto ganó ese mes?". Va en esta misma página: usa las mismas dos
   medidas y la misma tabla Calendario, sin nada nuevo que configurar.

   ⚠️ **Poné `[Margen bruto]` en el eje Y secundario.** Cantidad vendida y
   margen bruto tienen escalas muy distintas (decenas contra cientos/miles);
   compartiendo un solo eje, la línea de cantidad queda aplastada cerca del
   cero y se pierde el detalle de su propio movimiento. En el panel de
   formato del visual: `Margen bruto` → *Eje Y* → activar **Eje secundario**.
   Cada línea se lee con su propia escala a la derecha/izquierda y el gráfico
   se entiende mucho mejor.

   **Tip opcional — drill down/up, explicado paso a paso** (no obligatorio;
   tus dos gráficos separados, uno por mes y otro por año, funcionan
   perfectamente y son más simples de leer sin aprender ningún gesto nuevo.
   Esto es solo si en algún momento te cansás de mantener dos gráficos y
   preferís uno solo que se "abre" al año o al mes según quieras):

   Power BI permite apilar más de un campo en el mismo eje, uno "adentro" del
   otro — eso se llama jerarquía. Si en el eje del gráfico de líneas ponés
   primero `Calendario[Año]` y **debajo, en el mismo casillero del eje**,
   arrastrás también `Calendario[Nombre Mes]`, Power BI arma automáticamente
   la jerarquía Año → Mes.

   El gráfico arranca mostrando solo los años (4-5 puntos, uno por año, como
   tu segundo gráfico de antes). Al pasar el mouse por arriba del visual
   aparecen unas flechitas chiquitas arriba a la izquierda: una flecha para
   abajo ("Ir al siguiente nivel") y una para arriba ("Subir un nivel"). Si
   hacés **doble clic sobre un año puntual** (ej. 2022), el mismo gráfico
   deja de mostrar los años y muestra los 12 meses de *ese* 2022 — es la
   versión "zoom" de tu primer gráfico, pero solo para el año que elegiste.
   Doble clic de nuevo (o la flecha para arriba) te devuelve a ver todos los
   años.

   En criollo: en vez de dos gráficos fijos (uno siempre por mes, otro
   siempre por año), tenés UN gráfico que arranca por año y que podés
   "abrir" haciendo doble clic en el año que te interese, para ver el detalle
   mes a mes de ese año en particular, sin tener los dos visuales ocupando
   lugar en la página. De nuevo: es una comodidad de espacio, no cambia
   ningún dato ni ninguna medida.

## Verificación

```sql
SELECT to_char(v."Fecha_Venta", 'YYYY-MM') AS anio_mes,
       pt."Descripcion_Producto_Terminado",
       SUM(dv."Cantidad_Venta") AS cantidad,
       SUM(dv."Cantidad_Venta" * (dv."Precio_Venta_Real" - p."Precio_Unitario_Producto_Terminado")) AS margen
FROM "Detalle_Venta" dv
JOIN "Venta" v ON v."Id_Venta" = dv."Id_Venta"
JOIN "Produccion" p ON p."Id_Produccion" = dv."Id_Produccion"
JOIN "Producto_Terminado" pt ON pt."Id_Producto_Terminado" = p."Id_Producto_Terminado"
WHERE to_char(v."Fecha_Venta", 'YYYY-MM') = '2024-01'   -- cambiar por el mes que estés mirando en Power BI
GROUP BY 1, 2
ORDER BY cantidad DESC;
```

Filtrá el mismo mes en Power BI (slicer de Año + Mes) y comparalo con esta
consulta — el orden de productos por `cantidad` y por `margen` tiene que
coincidir.

---

# Dashboard 3 — Mejor cliente / mejor zona

*¿Quién compra más, y en qué zona de la ciudad está la mejor venta?*

## Tablas a cargar

`Cliente`, `Sector` (además de las del Dashboard 1).

## Relaciones

```
Venta[Id_Cliente]     (muchos) →  Cliente[Id_Cliente]  (1)
Cliente[Id_Sector]    (muchos) →  Sector[Id_Sector]    (1)
```

Con esto `[Ingresos]` (ya definido en el Dashboard 1) se puede cortar por
cliente o por sector sin escribir nada nuevo: el filtro viaja
`Cliente/Sector → Venta → Detalle_Venta`.

## Columna nueva (comodidad)

```dax
Nombre completo = 'Cliente'[Nombre_Cliente] & " " & 'Cliente'[Apellido_Cliente]
```

## Armar los visuales

**Mejor cliente:** tabla o gráfico de barras — eje `Cliente[Nombre completo]`,
valor `[Ingresos]`, ordenado descendente, Top N (ej. Top 15).

**Mejor zona:** igual pero con eje `Sector[Nombre_Sector]`.

**Mapa (opcional, ya hay lat/long cargadas):** visual *Mapa*, latitud/longitud
= `Cliente[Latitud_Cliente]` / `Cliente[Longitud_Cliente]`, tamaño de burbuja =
`[Ingresos]`.

⚠️ **Dato de calidad a tener en cuenta:** parte de los clientes migrados desde
el Excel no tenían coordenadas cargadas y quedaron en `(0, 0)` — en el mapa se
van a ver todos apilados en un mismo punto (el `(0,0)` del planeta). Si molesta,
agregar un filtro visual `Latitud_Cliente <> 0` al mapa (no a las tablas de
ranking, esas están bien igual).

## Verificación

```sql
SELECT c."Nombre_Cliente", c."Apellido_Cliente", s."Nombre_Sector",
       SUM(dv."Cantidad_Venta" * dv."Precio_Venta_Real") AS ingresos
FROM "Detalle_Venta" dv
JOIN "Venta" v ON v."Id_Venta" = dv."Id_Venta"
JOIN "Cliente" c ON c."Id_Cliente" = v."Id_Cliente"
LEFT JOIN "Sector" s ON s."Id_Sector" = c."Id_Sector"
GROUP BY 1, 2, 3
ORDER BY ingresos DESC
LIMIT 15;
```

Comparar el orden contra la tabla de "mejor cliente" en Power BI (sin
segmentación de fecha, para que sea el acumulado de siempre igual que el SQL).

---

# Dashboard 4 — Evolución mensual de patrimonio y escenarios

*¿Cómo viene cambiando el patrimonio y los tres escenarios (C/B/A) foto a
foto?*

## Tablas a cargar

`Balance` (las fotos que se toman desde la pantalla de Balance de la app).

## Relación (opcional pero prolija)

```
Calendario[Fecha] (1)  →  Balance[Fecha_Balance] (muchos)
```

No es obligatoria (`Balance` ya tiene una fecha propia por fila), pero
conecta este dashboard al mismo eje de tiempo que los otros tres.

## Medidas

```dax
Escenario A = SUM ( 'Balance'[Escenario_A] )
```
```dax
Escenario B = SUM ( 'Balance'[Escenario_B] )
```
```dax
Escenario C = SUM ( 'Balance'[Escenario_C] )
```
```dax
Patrimonio = SUM ( 'Balance'[Patrimonio] )
```

## Armar el visual

**Gráfico de líneas**: eje `Balance[Fecha_Balance]` (o `Calendario[Fecha]` si
armaste la relación), cuatro líneas: `[Escenario A]`, `[Escenario B]`,
`[Escenario C]`, `[Patrimonio]`.

⚠️ **Este dashboard muestra tantos puntos como filas tenga `Balance`.** Se
llena de dos maneras, las dos válidas:
- Foto a foto, hacia adelante, desde la pantalla de Balance de la app.
- Cargando a mano fotos **reales** de semanas pasadas, si existen (una
  libreta, un excel viejo con el total de esa semana) — se insertan como
  filas directas en `Balance`, no se recalculan. Da igual el orden en que se
  carguen: el eje es la fecha, así que Power BI las va a ordenar
  cronológicamente aunque se agreguen después.

Lo que **no** conviene es que el sistema "adivine" fechas pasadas
recalculando desde los movimientos (para eso faltan datos, ver la nota sobre
el historial de deudas incompleto en la conversación de esta sesión) — eso sí
daría números incorrectos con apariencia de precisos.

**Recordatorio operativo:** el reporte está en modo *Importar* (ver
"Conexión" arriba), así que no se entera solo de las filas nuevas — hay que
tocar **Actualizar** en Power BI Desktop cada vez que se agregue una fila a
`Balance` (una foto nueva, o una cargada a mano) para que el gráfico la
muestre.

## Verificación

```sql
SELECT "Fecha_Balance", "Escenario_A", "Escenario_B", "Escenario_C", "Patrimonio"
FROM "Balance"
ORDER BY "Fecha_Balance";
```

Cada fila de esta consulta tiene que ser un punto en el gráfico de líneas.

---

## Dashboards pendientes (no documentados todavía)

- **Rentabilidad real por producto con el acumulado de la sección 2** → ese sí
  usa la lógica de `saldo_producto.py` (recuperación de capital), no el margen
  de los dashboards 1-2. Tablas: `Produccion`, `Detalle_Venta`,
  `Movimiento_Inventario` (para el ajuste por reproceso).
- **Análisis de precios por proveedor** → cuando exista la mejora 5.1
  (base de datos de proveedores).
