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

## Próximos dashboards (8.1)

Pendientes, en orden sugerido:

- **Producto más vendido / con más margen por período** → necesita una tabla
  Calendario y marcarla como tabla de fechas, para poder cortar por mes/año.
  Es el paso natural siguiente y habilita a los demás.
- **Mejor cliente / mejor zona** → `Cliente` + `Sector` (ya hay lat/long cargadas).
- **Evolución mensual de patrimonio y escenarios** → tabla `Balance` (las fotos).
  Ojo: hoy solo hay fotos desde jul 2026 en adelante.
- **Rentabilidad real por producto con el acumulado de la sección 2** → ese sí usa
  la lógica de `saldo_producto.py` (recuperación de capital), no este margen.
- **Análisis de precios por proveedor** → cuando exista 5.1.
