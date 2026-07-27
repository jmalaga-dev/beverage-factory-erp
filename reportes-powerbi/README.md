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
5. **Evolución año contra año (estacionalidad):** dos gráficos de **líneas**,
   uno de `[Cantidad Vendida]` y otro de `[Margen bruto]` (separados a
   propósito, ver el ⚠️ de abajo). En cada uno, cada **año** es su propia
   línea, todas sobre el mismo eje de 12 meses (enero→diciembre). Responde
   "¿cómo se compara cada año, mes a mes?" — deja ver estacionalidad (ej. si
   febrero es un pico de margen todos los años) y qué años fueron mejores.
   Es una pregunta distinta al ranking de productos de los puntos 2-3.

   El truco es un solo cambio respecto de un gráfico de tiempo normal: en vez
   de poner una fecha continua en el eje, se separa mes y año en dos roles:
   - **Eje X** → `Calendario[Nombre Mes]` (los 12 meses)
   - **Leyenda** → `Calendario[Año]` (esto convierte cada año en una línea)
   - **Valores** → `[Cantidad Vendida]` en un gráfico, `[Margen bruto]` en el
     otro. Copiás el primero, lo pegás y cambiás solo la medida.

   ⚠️ **Una métrica por gráfico, no las dos juntas.** Cada gráfico ya tiene
   una línea por año (con datos de varios años son ~6 líneas). Meter cantidad
   Y margen en el mismo sería el doble de líneas, ilegible — y además tienen
   escalas muy distintas. Separándolos, cada uno se lee limpio y no hace falta
   eje secundario.

   ⚠️ **Depende del orden de `Nombre Mes`.** Si no configuraste "Ordenar
   `Nombre Mes` por `Mes`" (ver la sección de la tabla Calendario), el eje
   sale alfabético (abril, agosto, diciembre…) en vez de cronológico y el
   gráfico parece roto. Es el mismo fix de "Ordenar por columna" de antes.

   **El primer y el último año se ven cortados, y está bien.** Los datos
   arrancan a mitad del primer año y llegan hasta mitad del último, así que
   esas dos líneas solo cubren parte de los meses (no es un error, esos años
   están incompletos en la realidad). Los años del medio, completos, son los
   que mejor se comparan entre sí.

   Opcional estético: para líneas curvas en vez de quebradas, seleccionar el
   gráfico → formato → *Líneas* → **Suavizado**. No cambia los datos.

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
el sistema anterior no tenían coordenadas cargadas y quedaron en `(0, 0)` — en el mapa se
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

# Dashboard 5 — Ingreso externo mes a mes, año contra año

*¿En qué mes y qué año entró más plata de afuera (no ventas)?*

"Ingreso externo" es plata que entra a una cuenta sin que sea el cobro de una
venta: aportes propios, préstamos, cualquier entrada registrada desde la
pantalla de Transferencias con el botón de ingreso externo. Vive en
`Movimiento` como `Tipo_Movimiento = 'INGRESO_EXTERNO'`, junto con todo el
resto de la plata que se mueve (ventas, pagos, transferencias entre cuentas
propias) — no es una tabla aparte.

## Tablas a cargar

`Movimiento`, más la tabla `Calendario` ya armada para los dashboards 2 a 4
(reusarla, no crear otra).

## Relación

```
Calendario[Fecha] (1)  →  Movimiento[Fecha_Movimiento] (muchos)
```

## Medida nueva

```dax
Ingreso Externo =
CALCULATE (
    SUM ( 'Movimiento'[Monto_Movimiento] ),
    'Movimiento'[Tipo_Movimiento] = "INGRESO_EXTERNO"
)
```

## Armar el visual

Mismo truco del Dashboard 2 (separar mes y año en dos roles en vez de una
fecha continua en el eje):

- **Eje X** → `Calendario[Nombre Mes]` (los 12 meses)
- **Leyenda** → `Calendario[Año]` (cada año, una línea)
- **Valores** → `[Ingreso Externo]`

Gráfico de **líneas**, igual que la captura de referencia (Dashboard 2): un
color por año, los 12 meses en el eje, así se ve de un vistazo qué mes
concentra más ingreso externo y si eso se repite año a año o fue un pico
puntual.

⚠️ Depende del mismo fix de orden que el Dashboard 2: si `Nombre Mes` no
está configurado como "Ordenar por → `Mes`" (ver la sección de la tabla
Calendario), el eje sale alfabético en vez de cronológico.

Opcional: una tarjeta con `[Ingreso Externo]` filtrada al año en curso, para
el total acumulado sin abrir el gráfico.

## Verificación

```sql
SELECT to_char("Fecha_Movimiento", 'YYYY') AS anio,
       to_char("Fecha_Movimiento", 'MM') AS mes,
       SUM("Monto_Movimiento") AS ingreso_externo
FROM "Movimiento"
WHERE "Tipo_Movimiento" = 'INGRESO_EXTERNO'
GROUP BY 1, 2
ORDER BY 1, 2;
```

Cada fila de esta consulta tiene que coincidir con el punto de la línea de
ese año en ese mes, en Power BI.

---

# Dashboard 6 — Rentabilidad acumulada por producto (recuperación de inversión)

*¿Qué productos ya le devolvieron a la fábrica lo que costó producirlos, y
cuáles todavía están en rojo?*

Ojo: **no es el Pareto (Dashboard 1)**. El Pareto mira la ganancia de lo
**vendido**; esto mira la **recuperación de capital**: resta el costo de **todo
lo producido**, incluido el stock que todavía no se vendió. Un producto nuevo
con mucha producción y pocas ventas sale muy negativo acá aunque cada botella
vendida deje margen — es exactamente el `saldo` de la mejora 2.C
(`saldo_producto.py`), la misma cuenta que usa el reparto 70/30 al vender.

```
saldo del producto = ingresos de todas sus ventas − inversión en producirlo
inversión = Σ ( Cantidad_Producida × Precio_Unitario ) de todos sus lotes
```

## Tablas a cargar

Ninguna nueva: reusa `Produccion`, `Detalle_Venta`, `Producto_Terminado` del
Dashboard 1. Las relaciones que hacen falta ya están armadas ahí
(`Detalle_Venta → Produccion → Producto_Terminado`).

## Medidas DAX

```dax
Inversión acumulada =
SUMX (
    'Produccion',
    'Produccion'[Cantidad_Producida_Produccion]
        * 'Produccion'[Precio_Unitario_Producto_Terminado]
)
```

`[Ingresos]` ya existe (Dashboard 1). Al ponerlo junto a un producto en un
visual, el filtro viaja `Producto_Terminado → Produccion → Detalle_Venta`, así
que da los ingresos **de ese producto** sin escribir nada nuevo.

```dax
Saldo del producto = [Ingresos] - [Inversión acumulada]
```

```dax
Recuperó inversión =
IF ( [Saldo del producto] > 0, "Sí", "No" )
```

KPI — cuántos productos siguen sin recuperar:

```dax
Productos sin recuperar =
COUNTROWS (
    FILTER (
        VALUES ( 'Producto_Terminado'[Descripcion_Producto_Terminado] ),
        [Saldo del producto] < 0
    )
)
```

> **Ajuste por reproceso (hoy = 0, incluir cuando exista).** Al reprocesar,
> las botellas pasan de un lote a otro pero la `Cantidad_Producida` del origen
> no baja, así que su costo queda contado en los dos lotes y la inversión se
> infla. `saldo_producto.py` lo corrige restando ese costo duplicado
> (`Movimiento_Inventario` tipo `REPROCESO`/`SALIDA`). En esta base **no hay
> ningún reproceso todavía**, así que la medida de arriba coincide exacto con
> la app. Cuando haya reprocesos, restarle a `[Inversión acumulada]` el costo
> arrastrado (`Σ Cantidad_Movimiento × Precio_Unitario del lote origen`) para
> volver a cuadrar.

## Armar el visual

1. **Gráfico de barras**: eje `Producto_Terminado[Descripcion_Producto_Terminado]`,
   valor `[Saldo del producto]`, **ordenado ascendente** (los más negativos
   arriba: son los que más lejos están de recuperar).
2. Color por `[Recuperó inversión]` (rojo = No, verde = Sí) para leer de un
   golpe quién está en rojo.
3. Tarjeta con `[Productos sin recuperar]`.
4. Filtro visual *Top/Bottom N* por `[Saldo del producto]` si hay demasiados
   productos para leerlos todos.

Opcional — si querés el mismo corte **por mes** (¿cómo venía el saldo hace 3
meses?), sumá la tabla `Calendario` y su relación a `Venta`; pero recordá que
la inversión también es acumulada, así que un corte por fecha necesita una
medida de saldo "hasta la fecha" más elaborada. La foto de todos los tiempos
(la de arriba) es la que responde la pregunta principal.

## Verificación

```sql
WITH inv AS (
  SELECT "Id_Producto_Terminado" AS pid,
         SUM("Cantidad_Producida_Produccion" * "Precio_Unitario_Producto_Terminado") AS inversion
  FROM "Produccion" GROUP BY 1),
ing AS (
  SELECT p."Id_Producto_Terminado" AS pid,
         SUM(dv."Cantidad_Venta" * dv."Precio_Venta_Real") AS ingresos
  FROM "Detalle_Venta" dv
  JOIN "Produccion" p ON p."Id_Produccion" = dv."Id_Produccion"
  GROUP BY 1)
SELECT pt."Descripcion_Producto_Terminado",
       ROUND(COALESCE(ing.ingresos,0)::numeric, 2) AS ingresos,
       ROUND(COALESCE(inv.inversion,0)::numeric, 2) AS inversion,
       ROUND((COALESCE(ing.ingresos,0) - COALESCE(inv.inversion,0))::numeric, 2) AS saldo
FROM "Producto_Terminado" pt
LEFT JOIN inv ON inv.pid = pt."Id_Producto_Terminado"
LEFT JOIN ing ON ing.pid = pt."Id_Producto_Terminado"
WHERE COALESCE(inv.inversion,0) <> 0 OR COALESCE(ing.ingresos,0) <> 0
ORDER BY saldo ASC;
```

El `saldo` de cada fila tiene que coincidir con `[Saldo del producto]` de ese
producto en Power BI. La cuenta de filas con `saldo < 0` es
`[Productos sin recuperar]`.

---

# Dashboard 7 — Evolución de precio por materia prima (y detección de outliers)

*¿Cómo se movió el precio de cada insumo en el tiempo, y qué precios viejos
parecen errores de carga heredados del sistema anterior?*

Este dashboard es la cara visual de la mejora **5.2**: hay materias primas cuyo
precio unitario mínimo histórico está muy por debajo de cualquier compra
reciente (algún insumo puede ir de un precio muy bajo a varios múltiplos más a
lo largo de los años; algunos envases muestran saltos parecidos). Parte es
inflación de varios años, parte son probables errores de tipeo arrastrados del
sistema anterior. Verlos en una línea temporal es lo que permite distinguir una
cosa de la otra.

## Tablas a cargar

`Compra`, `Materia_Prima`, más la tabla `Calendario`.

## Relaciones

```
Compra[Id_Materia_Prima] (muchos) → Materia_Prima[Id_Materia_Prima] (1)
Calendario[Fecha]        (1)       → Compra[Fecha_Compra]           (muchos)
```

⚠️ **`Precio_Compra` es el precio TOTAL de la compra, no el unitario.** El
precio por unidad es `Precio_Compra / Cantidad_Compra`. Por eso el promedio
correcto es **ponderado** (total Bs ÷ total cantidad), no el promedio de los
unitarios: una compra de 1 kg no puede pesar igual que una de 100 kg. Es el
mismo criterio del costo promedio del stock (mejora 1.3) y de la simulación
(1.5), así que los números son comparables entre pantallas.

## Medidas DAX

```dax
Bs comprados = SUM ( 'Compra'[Precio_Compra] )
```
```dax
Cantidad comprada = SUM ( 'Compra'[Cantidad_Compra] )
```
```dax
Precio unitario ponderado = DIVIDE ( [Bs comprados], [Cantidad comprada] )
```

Para los outliers, el mínimo y el máximo precio unitario de una sola compra en
el filtro actual:

```dax
PU mínimo = MINX ( 'Compra', DIVIDE ( 'Compra'[Precio_Compra], 'Compra'[Cantidad_Compra] ) )
```
```dax
PU máximo = MAXX ( 'Compra', DIVIDE ( 'Compra'[Precio_Compra], 'Compra'[Cantidad_Compra] ) )
```
```dax
Ratio máx/mín = DIVIDE ( [PU máximo], [PU mínimo] )
```

Un `[Ratio máx/mín]` alto (ej. > 3) es la señal de "acá hay un precio raro":
puede ser inflación real o un error. La línea temporal dice cuál.

## Armar los visuales

**Línea de evolución (el visual principal):**
1. Segmentación (slicer) con `Materia_Prima[Descripcion_Materia_Prima]` — se
   elige **un** insumo por vez (si no, la línea mezcla peras con manzanas).
2. Gráfico de **líneas**: eje `Calendario[Año-Mes]` (o `Calendario[Año]` para
   una vista más gruesa), valor `[Precio unitario ponderado]`.
3. ⚠️ Depende del mismo fix de orden de `Año-Mes` de la tabla Calendario; sin
   eso el eje sale desordenado.

**Tabla de outliers (para barrer todos los insumos de un vistazo):**
- Tabla: filas `Materia_Prima[Descripcion_Materia_Prima]`, columnas
  `[PU mínimo]`, `[Precio unitario ponderado]`, `[PU máximo]`,
  `[Ratio máx/mín]`, ordenada por `[Ratio máx/mín]` descendente.
- Filtro visual: `[Cantidad comprada]` con "n.º de compras" alto (o un recuento)
  para no marcar como outlier un insumo con 2 compras — el ratio sólo es
  informativo con suficiente historia.
- Formato condicional (fondo de la columna `[Ratio máx/mín]`) para pintar de
  rojo los ratios altos.

**Cómo usarlo:** ordenás la tabla por ratio, y para cada insumo sospechoso
hacés clic (o lo elegís en el slicer) y mirás la línea. Si el precio bajo es un
punto aislado de hace años y todo lo reciente es más caro, es candidato a error
de carga (mejora 5.2). Si la subida es gradual, es inflación real.

## Verificación

```sql
SELECT mp."Descripcion_Materia_Prima",
       COUNT(*) AS n_compras,
       ROUND(MIN(c."Precio_Compra" / c."Cantidad_Compra")::numeric, 2) AS pu_min,
       ROUND((SUM(c."Precio_Compra") / SUM(c."Cantidad_Compra"))::numeric, 2) AS pu_ponderado,
       ROUND(MAX(c."Precio_Compra" / c."Cantidad_Compra")::numeric, 2) AS pu_max
FROM "Compra" c
JOIN "Materia_Prima" mp ON mp."Id_Materia_Prima" = c."Id_Materia_Prima"
WHERE c."Cantidad_Compra" > 0
GROUP BY 1
HAVING COUNT(*) > 15
ORDER BY (MAX(c."Precio_Compra" / c."Cantidad_Compra")
          / NULLIF(MIN(c."Precio_Compra" / c."Cantidad_Compra"), 0)) DESC;
```

`pu_ponderado` tiene que coincidir con `[Precio unitario ponderado]` de ese
insumo (sin segmentación de fecha), y `pu_min` / `pu_max` con las medidas
homónimas. La materia prima al tope de esta lista es la de ratio más alto — la
primera candidata a revisar.

---

# Dashboard 8 — Mano de obra por trabajador y mes

*¿Cuántas horas puso cada trabajador, cuánto costó, y cuántas botellas salieron
por hora?*

## Tablas a cargar

`Registro_Trabajador` (las jornadas), `Trabajador`, `Produccion` (ya cargada
del Dashboard 1) y la tabla `Calendario`.

## Relaciones

```
Registro_Trabajador[Id_Trabajador] (muchos) → Trabajador[Id_Trabajador]        (1)
Calendario[Fecha]                  (1)       → Registro_Trabajador[Fecha_Registro_Trabajador] (muchos)
Calendario[Fecha]                  (1)       → Produccion[Fecha_Produccion]     (muchos)
```

Las dos relaciones de `Calendario` a tablas distintas conviven sin problema (es
una por tabla de hechos).

## Columna calculada (sobre `Trabajador`)

La tarifa por hora se **deriva** del sueldo semanal y las horas base — es la
misma cuenta que hizo la mejora 10.1 en la app (`sueldo / horas base`), no un
dato aparte:

```dax
Tarifa hora = DIVIDE ( 'Trabajador'[Pago_Trabajador], 'Trabajador'[Horas_Base_Trabajador] )
```

## Medidas DAX

```dax
Horas trabajadas = SUM ( 'Registro_Trabajador'[Horas_Registro_Trabajador] )
```

```dax
Costo mano de obra =
SUMX (
    'Registro_Trabajador',
    'Registro_Trabajador'[Horas_Registro_Trabajador]
        * RELATED ( 'Trabajador'[Tarifa hora] )
)
```

```dax
Botellas producidas = SUM ( 'Produccion'[Cantidad_Producida_Produccion] )
```

```dax
Botellas por hora = DIVIDE ( [Botellas producidas], [Horas trabajadas] )
```

## Armar los visuales

1. Slicers de `Calendario[Año]` y `Calendario[Nombre Mes]` para acotar el
   período.
2. **Horas y costo por trabajador:** gráfico de barras, eje
   `Trabajador[Nombre_Trabajador]`, valores `[Horas trabajadas]` y
   `[Costo mano de obra]` (o dos gráficos si preferís no mezclar escalas).
3. **Costo de mano de obra mes a mes:** gráfico de líneas, eje
   `Calendario[Año-Mes]`, valor `[Costo mano de obra]` — la tendencia del gasto
   en sueldos.
4. **Eficiencia (nivel fábrica):** tarjeta o línea con `[Botellas por hora]`.

⚠️ **`[Botellas por hora]` sólo tiene sentido a nivel fábrica/mes, NO por
trabajador.** La producción no se atribuye a una persona: el cierre semanal
(mejora 3.7) reparte las horas entre los productos por botellas equivalentes,
no al revés. Poner `[Botellas por hora]` con `Trabajador` en el eje daría un
número sin significado. Dejá esa métrica en una tarjeta global o cortada sólo
por fecha.

⚠️ **Dato de calidad:** las jornadas migradas del sistema anterior traen su
tarifa,
pero si algún trabajador viejo quedó cargado en Bs/hora (en vez de sueldo
semanal, ver mejora 10.1) su `[Tarifa hora]` va a salir distorsionada hasta que
se reingrese su sueldo. Revisá la columna `[Tarifa hora]` en una tabla simple
antes de confiar en el costo.

## Verificación

```sql
SELECT t."Nombre_Trabajador",
       to_char(rt."Fecha_Registro_Trabajador", 'YYYY-MM') AS anio_mes,
       ROUND(SUM(rt."Horas_Registro_Trabajador")::numeric, 1) AS horas,
       ROUND(SUM(rt."Horas_Registro_Trabajador"
             * (t."Pago_Trabajador" / NULLIF(t."Horas_Base_Trabajador", 0)))::numeric, 2) AS costo
FROM "Registro_Trabajador" rt
JOIN "Trabajador" t ON t."Id_Trabajador" = rt."Id_Trabajador"
GROUP BY 1, 2
ORDER BY 1, 2;
```

Filtrá el mismo trabajador y mes en Power BI y comparás `horas` contra
`[Horas trabajadas]` y `costo` contra `[Costo mano de obra]`.

---

# Dashboard 9 — Deudas: saldo vivo y pagos en el tiempo

*¿A quién se le debe hoy, y cuánto se viene pagando de deuda mes a mes?*

⚠️ **Por qué NO es un "aging" clásico.** Un aging reparte la deuda por
antigüedad (0-30 días, 30-60…) usando la **fecha de vencimiento**, y `Deuda` no
la tiene. Además `Movimiento_Deuda` en esta base sólo guarda movimientos tipo
`PAGO` — los aumentos de deuda no quedaron con fecha en la migración del sistema
anterior,
así que **el saldo histórico no se puede reconstruir** (no se sabe cuánto se
debía en una fecha pasada). Lo que sí es real y útil son dos cosas: la **foto
del saldo vivo de hoy** (`Deuda[Saldo_Actual_Deuda]`, cacheado y correcto) y el
**esfuerzo de pago en el tiempo** (los `PAGO` sí tienen fecha).

## Tablas a cargar

`Deuda`, `Movimiento_Deuda`, más la tabla `Calendario`.

## Relaciones

```
Movimiento_Deuda[Id_Deuda]         (muchos) → Deuda[Id_Deuda]                    (1)
Calendario[Fecha]                  (1)       → Movimiento_Deuda[Fecha_Movimiento_Deuda] (muchos)
```

## Medidas DAX

```dax
Saldo vivo = SUM ( 'Deuda'[Saldo_Actual_Deuda] )
```

```dax
Pagos de deuda =
CALCULATE (
    SUM ( 'Movimiento_Deuda'[Monto_Movimiento_Deuda] ),
    'Movimiento_Deuda'[Tipo_Movimiento_Deuda] = "PAGO"
)
```

Deudas que todavía tienen saldo (para una tarjeta):

```dax
Deudas vivas =
COUNTROWS ( FILTER ( 'Deuda', 'Deuda'[Saldo_Actual_Deuda] > 0 ) )
```

## Armar los visuales

1. **A quién se le debe hoy:** gráfico de barras, eje
   `Deuda[Descripcion_Deuda]`, valor `[Saldo vivo]`, ordenado descendente,
   filtro visual `Saldo_Actual_Deuda > 0` (las saldadas no aportan). Es común que
   una deuda grande (capital + interés de un préstamo) domine y el resto sean
   deudas chicas.
2. **Esfuerzo de pago año contra año:** gráfico de **líneas** con el truco del
   Dashboard 2 — eje `Calendario[Nombre Mes]`, leyenda `Calendario[Año]`, valor
   `[Pagos de deuda]`. Deja ver en qué meses se paga más deuda y si hay un
   patrón anual.
3. Tarjetas: `[Saldo vivo]` (total que se debe hoy) y `[Deudas vivas]`
   (cuántas siguen abiertas).

Opcional — agrupar deudas por su origen (todas las de un mismo acreedor juntas):
en Power Query, columna nueva que tome la primera palabra o un prefijo de
`Descripcion_Deuda`. No es imprescindible; el gráfico de barras ya las muestra
ordenadas.

## Verificación

```sql
-- Saldo vivo de hoy (comparar contra [Saldo vivo] sin filtros):
SELECT ROUND(SUM("Saldo_Actual_Deuda")::numeric, 2) AS saldo_vivo,
       COUNT(*) FILTER (WHERE "Saldo_Actual_Deuda" > 0) AS deudas_vivas
FROM "Deuda";

-- Pagos de deuda por mes (comparar contra la línea):
SELECT to_char("Fecha_Movimiento_Deuda", 'YYYY-MM') AS anio_mes,
       ROUND(SUM("Monto_Movimiento_Deuda")::numeric, 2) AS pagos
FROM "Movimiento_Deuda"
WHERE "Tipo_Movimiento_Deuda" = 'PAGO'
GROUP BY 1 ORDER BY 1;
```

`saldo_vivo` tiene que dar igual que `[Saldo vivo]` y cada fila de la segunda
consulta tiene que coincidir con el punto de la línea de ese mes.

---

# Dashboard 10 — Gastos por grupo, mes a mes y año contra año

*¿En qué grupo se gasta más, y cómo evoluciona mes a mes y de un año a otro?*

Es el dashboard analítico del pedido "ver los gastos por grupos por año". La app
registra cada gasto con un **grupo** (etiqueta validada) desde la pantalla de
Gastos; acá se agregan por grupo y por tiempo para ver dónde se va la plata.

## Qué cuenta como "gasto" (y qué NO)

Un gasto es un `Movimiento` con `Tipo_Movimiento = 'SALIDA'` **que no es una
compra, ni un pago a trabajador, ni un servicio**. Las tres también son SALIDA,
pero cada una tiene su propia tabla y se identifica por su **vínculo**
(`Compra[Id_Movimiento]`, `Pago_Trabajador[Id_Movimiento]`,
`Gasto_Extra_Mes[Id_Movimiento]`), no adivinando por texto — es el mismo criterio
"categorizar sin adivinar" que usa el balance de la app (DECISIONES_DISENO 4,
mejora 4.1). "Gasto" es el **residuo**: lo que sale y no es ninguna de las otras
tres. Si no se excluyeran, el gráfico sumaría toda la materia prima, los sueldos
y la luz como si fueran gastos del día a día.

**Por qué los servicios van aparte** (luz, agua, internet, teléfono, impuestos de
fábrica): se registran en `Gasto_Extra_Mes` y se pagan desde la pantalla de
Prorrateo. Pero sólo los pagados **desde la app** generan un `Movimiento`: los
meses migrados del sistema anterior quedaron marcados como pagados sin generar
ninguno.
Si contaran como gasto, aparecerían en el dashboard únicamente a partir del mes
en que se empezó a pagarlos desde la app y en ningún año anterior — una
discontinuidad que haría mentir a la comparación año contra año. Excluyéndolos,
la serie es homogénea en todo el histórico. Su evolución propia se mira sobre
`Gasto_Extra_Mes`, que sí tiene la historia completa (ver el final de esta
sección), y su total de la semana está desglosado en el balance de la app.

Nota: un gasto **cubierto por un aporte externo** (item 10b — lo pagó otra
persona) igual aparece acá, y está bien: es un gasto real de la fábrica/casa. El
aporte que lo financió se ve por separado en el Dashboard 5 (ingreso externo).

## Tablas a cargar

`Movimiento`, `Grupo_Movimiento`, `Compra`, `Pago_Trabajador` y `Gasto_Extra_Mes`
(estas tres últimas solo para excluir sus movimientos), más la tabla `Calendario`
ya armada para los dashboards 2 a 5 (reusarla, no crear otra). Si querés además
el gráfico de servicios del final, cargá también `Gasto_Extra`.

## Relaciones

```
Movimiento[Id_Grupo_Movimiento] (muchos) → Grupo_Movimiento[Id_Grupo_Movimiento] (1)
Calendario[Fecha]               (1)       → Movimiento[Fecha_Movimiento]          (muchos)
```

La relación `Calendario → Movimiento` ya existe si armaste el Dashboard 5. Las de
`Compra` / `Pago_Trabajador` / `Gasto_Extra_Mes` a `Movimiento` por
`Id_Movimiento` **no hacen falta** como relación del modelo (la exclusión de
abajo usa `VALUES`, no el filtro que viaja por relación); si Power BI las detecta
solas, dejalas en *inactivas* para que no cambien el sentido de los filtros.

## La clasificación va en una columna, no en la medida

Modelado → **Nueva columna**, sobre `Movimiento`:

```dax
Es_Gasto =
'Movimiento'[Tipo_Movimiento] = "SALIDA"
    && NOT ( 'Movimiento'[Id_Movimiento] IN VALUES ( 'Compra'[Id_Movimiento] ) )
    && NOT ( 'Movimiento'[Id_Movimiento] IN VALUES ( 'Pago_Trabajador'[Id_Movimiento] ) )
    && NOT ( 'Movimiento'[Id_Movimiento] IN VALUES ( 'Gasto_Extra_Mes'[Id_Movimiento] ) )
```

Las compras, los pagos y los servicios tienen su `Id_Movimiento` en esas tablas;
los gastos no (su vínculo no existe), así que quedan afuera de las exclusiones y
sí se suman.

⚠️ **Esto tiene que ser una columna calculada, no un filtro dentro de la medida** —
y no es cosmético, es la diferencia entre que el dashboard responda o se cuelgue.
Un filtro como `NOT ( Movimiento[Id_Movimiento] IN VALUES ( Compra[Id_Movimiento] ) )`
mezcla dos tablas, así que DAX no lo puede resolver en el motor de
almacenamiento: lo convierte en un `FILTER` sobre **la lista entera** de
`Id_Movimiento` y lo recorre **una vez por cada celda del visual**. Con 10 grupos
en el eje ni se nota. Al bajar a nivel de descripción son miles de celdas, cada
una repitiendo el barrido completo, y el visual muere con *"se superaron los
límites de recursos visuales"*. Como columna, la clasificación se calcula **una
sola vez al Actualizar** y después es una comparación booleana sobre una columna
comprimida.

Con eso, las medidas quedan triviales:

```dax
Gastos = CALCULATE ( SUM ( 'Movimiento'[Monto_Movimiento] ), 'Movimiento'[Es_Gasto] = TRUE )
```

```dax
Cantidad de gastos = CALCULATE ( COUNTROWS ( 'Movimiento' ), 'Movimiento'[Es_Gasto] = TRUE )
```

**Ya no debería existir el bucket "(en blanco)"** en el eje de grupos: los gastos
anteriores a que el sistema viejo tuviera columna de grupo llegaron sin etiquetar
y se reasignaron a mano (ver `backend/scripts/aplicar_grupos_validados.py`). Si
vuelve a aparecer, es un gasto nuevo que alguien cargó sin elegir grupo en la app.

## Armar los visuales

1. **Slicers:** `Calendario[Año]` y `Grupo_Movimiento[Nombre_Grupo_Movimiento]`.
   El slicer de grupo es el "filtro de grupo" del pedido — permite mirar un grupo
   puntual, o dejarlo abierto para verlos todos. Poné **dos** slicers de grupo
   (uno al lado del otro) si querés comparar dos grupos rápido, o usá uno solo con
   selección múltiple.
2. **Evolución mes a mes, año contra año** (el visual principal, mismo truco del
   Dashboard 2/5):
   - **Eje X** → `Calendario[Nombre Mes]` (los 12 meses)
   - **Leyenda** → `Calendario[Año]` (cada año, una línea)
   - **Valores** → `[Gastos]`
   Gráfico de **líneas**. Responde "¿qué mes gasta más y se repite el patrón año
   a año?". ⚠️ Depende del fix de orden de `Nombre Mes` (Ordenar por → `Mes`, ver
   la sección de la tabla Calendario); sin eso el eje sale alfabético.
3. **Ranking por grupo:** gráfico de **barras**, eje
   `Grupo_Movimiento[Nombre_Grupo_Movimiento]`, valor `[Gastos]`, ordenado
   descendente. Responde "¿en qué grupo se va más plata?" en el período filtrado.
4. **Composición año contra año:** gráfico de **columnas apiladas**, eje
   `Calendario[Año]`, leyenda `Grupo_Movimiento[Nombre_Grupo_Movimiento]`, valor
   `[Gastos]` — cada año una columna, partida por grupo. Deja ver si cambió el
   mix de gastos entre años.
5. Tarjetas: `[Gastos]` (total del período) y `[Cantidad de gastos]`.

## Ver los gastos concretos detrás de un grupo

El ranking dice *cuánto* se fue en mantenimiento, pero no *en qué*. Para eso hace
falta bajar a `Movimiento[Descripcion_Movimiento]`, que es texto libre y casi
único por fila. Dos reglas para que eso no reviente el visual:

**Filtrar por columna, no por medida.** Una tabla de detalle no agrega nada: sólo
lista filas. Si la filtrás con la medida `[Gastos]`, Power BI la evalúa celda por
celda; si la filtrás con la columna `Es_Gasto`, resuelve todo escaneando una
columna booleana.

**No dejarla en la página principal.** Aunque sea rápida, listar todos los gastos
de todos los años es ruido. Va en una página de *drill through*:

1. Página nueva, `Detalle de gastos`. En su panel de Filtros → **Extraer datos**
   (*Drill through*) → arrastrar `Grupo_Movimiento[Nombre_Grupo_Movimiento]`.
   Dejar activado **Mantener todos los filtros**, así los slicers de año y mes de
   la página principal viajan con vos.
2. Visual **Tabla** con: `Movimiento[Fecha_Movimiento]`,
   `Grupo_Movimiento[Nombre_Grupo_Movimiento]`, `Movimiento[Descripcion_Movimiento]`,
   `Movimiento[Monto_Movimiento]` (con **No resumir**) y `Movimiento[Id_Movimiento]`.
3. Filtro de ese objeto visual: `Movimiento[Es_Gasto]` → *is True*.

`Monto` **sin resumir** evita que el visual agrupe por descripción, y
`Id_Movimiento` garantiza **una fila por movimiento**: sin él, dos gastos del
mismo día, mismo grupo y misma descripción se fusionarían en una sola fila con el
importe mal. Si molesta verlo, se le baja el ancho de columna al mínimo.

**Cómo se usa:** click derecho sobre una barra del ranking por grupo → *Extraer
datos* → *Detalle de gastos*, y ves exactamente los movimientos de ese grupo en
el período que tenías filtrado.

Si preferís tenerlo a la vista sin cambiar de página, la alternativa es la misma
tabla en la página principal con un filtro visual **Top N = 50 por
`Monto_Movimiento`** ("los 50 gastos más grandes del período"), que suele ser lo
que interesa mirar.

## Los servicios, aparte

Los gastos extra están excluidos de `[Gastos]` a propósito (ver arriba). Su
evolución se mira sobre `Gasto_Extra_Mes`, que tiene la historia completa desde
2021 aunque casi ninguna fila tenga movimiento asociado:

```dax
Servicios = SUM ( 'Gasto_Extra_Mes'[Monto_Gasto_Extra_Mes] )
```

`Gasto_Extra_Mes[Anio_Mes]` es texto `YYYY-MM`, así que sirve directo como eje sin
pasar por `Calendario`. Un gráfico de líneas con ese eje y `[Servicios]`, y una
leyenda con `Gasto_Extra[Descripcion_Gasto_Extra]`, responde "¿cuál servicio se
disparó y desde cuándo?". Al ser costos fijos, su peso sobre el total de salidas
suele ser parecido año tras año: si un año se despega, ahí hay algo que mirar.

**Recordatorio operativo:** el reporte está en modo *Importar*, así que hay que
tocar **Actualizar** en Power BI Desktop para que tome los gastos nuevos. Ojo que
`Es_Gasto` es una **columna calculada**: se recalcula en ese mismo Actualizar, no
hay que hacer nada aparte.

## Verificación

```sql
-- Gastos por grupo y mes (SALIDA que no es compra ni pago), comparar contra el visual:
SELECT to_char(m."Fecha_Movimiento", 'YYYY') AS anio,
       to_char(m."Fecha_Movimiento", 'MM') AS mes,
       COALESCE(g."Nombre_Grupo_Movimiento", '(sin grupo)') AS grupo,
       ROUND(SUM(m."Monto_Movimiento")::numeric, 2) AS gastos
FROM "Movimiento" m
LEFT JOIN "Grupo_Movimiento" g ON g."Id_Grupo_Movimiento" = m."Id_Grupo_Movimiento"
WHERE m."Tipo_Movimiento" = 'SALIDA'
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Compra" WHERE "Id_Movimiento" IS NOT NULL)
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Pago_Trabajador" WHERE "Id_Movimiento" IS NOT NULL)
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Gasto_Extra_Mes" WHERE "Id_Movimiento" IS NOT NULL)
GROUP BY 1, 2, 3
ORDER BY 1, 2, gastos DESC;
```

Cada fila (año-mes-grupo) tiene que coincidir con el punto/segmento de ese grupo
en Power BI. El total sin filtros tiene que dar igual que `[Gastos]` y que la
fila "Gastos de la semana" del balance de la app para el mismo período (misma
definición de gasto, las mismas tres exclusiones).

Y esta otra tiene que devolver **cero filas** — si devuelve alguna, hay gastos sin
grupo y en el dashboard van a aparecer como "(en blanco)":

```sql
SELECT to_char(m."Fecha_Movimiento",'YYYY') AS anio, COUNT(*)
FROM "Movimiento" m
WHERE m."Tipo_Movimiento" = 'SALIDA' AND m."Id_Grupo_Movimiento" IS NULL
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Compra" WHERE "Id_Movimiento" IS NOT NULL)
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Pago_Trabajador" WHERE "Id_Movimiento" IS NOT NULL)
  AND m."Id_Movimiento" NOT IN (SELECT "Id_Movimiento" FROM "Gasto_Extra_Mes" WHERE "Id_Movimiento" IS NOT NULL)
GROUP BY 1;
```

---

## Dashboards pendientes (no documentados todavía)

- **Análisis de precios por proveedor** → distinto del Dashboard 7 (que compara
  el precio de un insumo **en el tiempo**); éste compararía el mismo insumo
  **entre proveedores**. Bloqueado por **datos, no por código**: la mejora 5.1
  ya creó las tablas `Proveedor` / `Proveedor_Materia_Prima` y la columna
  `Compra[Id_Proveedor]`, pero hoy están **vacías** (las compras migradas
  del sistema anterior tienen `Id_Proveedor` en NULL). Se puede documentar y
  armar recién
  cuando se carguen proveedores reales y las compras nuevas empiecen a quedar
  atadas a uno.
