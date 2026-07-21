# Mejoras y sugerencias para próximas versiones — Fábrica V2

Este documento recoge funcionalidades, mejoras y refinamientos identificados
durante el desarrollo del MVP que se dejaron **fuera del MVP a propósito**, para
construirlas en versiones posteriores. Está organizado por módulos.

El MVP (lo que SÍ se construyó) está descrito en `DECISIONES_DISENO.md`.

---

## 1. COSTEO Y PRORRATEO

### 1.1 Horas heredadas en cadena (prorrateo real) — ALTA PRIORIDAD
La pieza más importante pendiente. El prorrateo mensual debe repartir los gastos
extra (luz, agua, internet) entre los **productos terminados** según las horas
hombre que cada uno consumió ese mes, incluyendo las horas **heredadas** de los
productos intermedios que consumió.

Lógica exacta (según se usaba en Excel):
- Cada producción intermedia acumula sus "horas invertidas" = horas directas de
  trabajo + horas heredadas de los intermedios que consumió. Ej: Jarabe A = 4h
  de Juan + 2h heredadas del Jarabe Concentrado = 6h invertidas.
- Las horas se heredan en el momento del **consumo**, proporcionalmente a la
  cantidad consumida. Si un producto terminado consume 1/3 de un lote de jarabe
  (que tenía 6h acumuladas), hereda 2h. Las otras 4h quedan "guardadas" en el
  jarabe restante para cuando se consuma en meses futuros.
- La atribución es por **mes de consumo**, no de producción. Un jarabe hecho hace
  3 meses, si se consume 1/3 este mes, hereda esas horas a este mes.
- Los gastos se reparten SOLO entre productos terminados (los intermedios
  trasladan sus horas, no cargan gastos directamente).
- El rastreo es recursivo/cíclico: intermedio que consume intermedio que consume
  intermedio, hasta llegar a la materia prima.

Objetivo del cálculo: saber cada mes qué producto "rentó la fábrica" y cuántas
horas hombre le corresponden, para decidir si vale la pena producirlo.

Implicación técnica: probablemente requiere agregar un campo "horas acumuladas"
a las producciones (intermedia y terminada), llenado al producir (replicando la
columna de Excel), y modificar el servicio de prorrateo para calcular desde las
producciones reales del mes en vez de leer una tabla `Horas_Producto_Mes` llenada
a mano. Es un mini-proyecto en sí mismo.

**Diseño confirmado (comparación con el Excel, jul 2026):** columnas de
"horas acumuladas" (y su equivalente en dinero) en `Produccion_Intermedia` y
`Produccion`. Una producción nace con la suma de horas de sus jornadas más
las heredadas de los intermedios que consumió; al consumirse parcialmente
traslada horas y dinero en proporción a la cantidad consumida. Así el
producto terminado responde directo "cuánto costó, cuántas botellas y
cuántas horas hombre", y el prorrateo mensual se vuelve una suma simple
sobre esas columnas en vez de una recursión al vuelo. Las horas directas de
la semana se asignan con el cierre semanal de 3.7.

**Estado: implementado (todo de una).** Migración 018: columna
`Horas_Acumuladas` en `Produccion_Intermedio` y `Produccion`, y tabla
`Gasto_Extra_Mes` (monto real y pago de un gasto en un mes).
- **Motor de horas** (`app/servicios/horas.py`): una producción nace con sus
  horas directas (jornadas) + las **heredadas** de los intermedios que
  consumió (`cantidad × Horas_Acumuladas_origen / Cantidad_Producida_origen`,
  tasa por unidad constante). Se llena en `producir_intermedio`,
  `producir_terminado` (heredadas; directas = 0 hasta el cierre), el **cierre
  3.7** (suma las horas que asigna) y el **reproceso** (hereda del origen +
  trabajo nuevo). Se hizo **backfill** de las producciones existentes
  (recalculado desde sus detalles de trabajo, en orden de dependencia; solo
  llena la columna, no toca costos/stock).
- **Prorrateo mensual** (`app/servicios/prorrateo.py`): ya no lee horas a mano
  — las computa sumando `Horas_Acumuladas` de los terminados del mes por
  producto (atribución por mes de producción). Vista previa + ejecutar, con la
  foto en `Prorrateo_Mensual` (última línea absorbe el redondeo).
- **Gastos variables por mes** (`app/servicios/gastos_mensuales.py`): se
  registra el monto real de cada gasto del mes y se paga (SALIDA de una
  cuenta); el prorrateo **exige que todos estén pagados**.
- Frontend: pantalla **Cierre de mes** (grupo *Cierre*, antes oculta): gestiona
  los montos del mes, sus pagos, y el reparto por horas con preview. El stock
  por lote de Prod. Terminada ahora muestra las horas acumuladas.
- Verificado con pruebas de integración: cadena
  concentrado→jarabe→terminado→cierre→reproceso (herencia exacta) y el flujo
  mensual (montos→pago→reparto 75/25 sin fugas, re-ejecución bloqueada), más el
  backfill sobre datos reales y `vite build`.

### Estado del prorrateo — RESUELTO (con 1.1)
La pantalla `PaginaProrrateo.jsx` ya está **visible y funcional** (grupo
*Cierre* → "Cierre de mes"). Todo lo que le faltaba quedó cubierto por 1.1:
- ✅ Gastos extra POR MES con monto variable y su pago (`Gasto_Extra_Mes`).
- ✅ Control de qué gastos del mes están pagados (estado por fila en la pantalla).
- ✅ El prorrateo exige que todos los gastos del mes estén pagados.
- ✅ Horas reales por producto computadas desde `Horas_Acumuladas` (1.1).
- ✅ Reparto proporcional solo entre los productos que produjeron ese mes.
- Pendiente menor (no urgente): marcar visualmente el mes completo/incompleto en
  un calendario, y editar/anular un prorrateo ya hecho.

### 1.2 Recálculo fiel del costo de trabajo (Camino 2)
En el MVP, el costo del trabajo se calcula con la **tarifa pactada** al producir
(Camino 1), y las diferencias con el pago real van al flujo de caja general. La
mejora (Camino 2) sería recalcular el costo de las producciones de la semana
cuando el pago real difiere del estimado, repartiendo la diferencia. Complejo por
el reparto proporcional entre producciones; se pospuso.

### 1.3 Costo promedio ponderado en producto terminado
Ya se implementó el consolidado con promedio ponderado en intermedios y
terminados. Verificar que esté completo en todas las vistas de stock.

**Estado: verificado y completado.** `/stock-materia-prima` también expone
`costo_promedio` ahora (antes solo intermedios y terminados lo tenían), mismo
patrón de cálculo. Hecho como parte del trabajo de 4.5.

### 1.4 Absorción de costos indirectos por botella producida — del Excel
Lógica del Excel sin equivalente hoy: ciertas compras y costos que no son
insumos directos deben ser "absorbidos" de a poco por las botellas
producidas, para que nada quede sin que alguien lo pague:
- **Utensilios y equipos** (ej. un barril de roble): tabla con descripción,
  costo de compra, fecha, "botellas estimadas a prorratear" (tasa móvil que
  se elige al comprar; ej. 10 botellas por cada boliviano) y botellas
  restantes. Cada producción consulta los items con saldo pendiente y agrega
  una línea de costo como si fuera una materia prima más (ej. "PU pagado por
  utensilios: 168 botellas → 56.28 Bs" = 0.335 Bs/botella), descontando las
  botellas de cada item hasta llegar a 0.
- **Horas pagadas por feriado** (se paga al trabajador sin producción a
  cambio): en el Excel vivían en la misma tabla de absorción.
- **Desechos/mermas**: hoy la merma solo descuenta stock; en el Excel su
  costo también lo absorbían las botellas producidas después.

Decisión pendiente al implementar: cómo convive con **Activos fijos** (7.2)
— un barril hoy se registraría como activo (suma al patrimonio); si además
su costo se absorbe al producto habría doble contabilización. Propuesta:
una sola vía por compra — utensilios menores van a absorción, bienes
durables van a activo.

**Estado: implementado (jul 2026).** Migración 014 crea `Item_Absorcion`
(tipo UTENSILIO/FERIADO/MERMA, costo, botellas estimadas, botellas
restantes) y `Absorcion_Produccion` (libro inmutable de qué producción
absorbió cuánto de cada ítem). Servicio `absorcion.py`:
- **Motor `absorber_en_produccion`:** enganchado en `producir_terminado`,
  cada producción de N botellas descuenta de cada ítem con saldo
  `min(N, restante) × (costo/botellas_estimadas)` (regla de 3 si al ítem le
  queda menos que N) y lo suma al costo del producto, como una línea más.
- **Utensilios y feriados:** `POST /utensilios` y `/feriados` — sale dinero
  de una cuenta (SALIDA, gasto real) y se crea el ítem. La tasa por defecto
  (`TASA_ABSORCION_DEFECTO = 10` botellas/Bs en `config.py`) sugiere las
  botellas estimadas; editable al registrar.
- **Mermas:** la merma se registra en **Cierre → Mermas** (que descuenta el
  stock del lote, lo estructural), y esa misma acción atómica crea el ítem
  MERMA valorado al costo del stock perdido. No es un segundo lugar de
  registro: es una acción con dos efectos (descontar stock + repartir su
  costo). El control vive en la pantalla de Mermas: al elegir tipo MERMA se
  ve el costo a absorber, se pueden editar las botellas estimadas (tasa) y
  hay un checkbox "absorber este costo" (marcado por defecto) por si una
  merma no debe encarecer los productos. Ajustes/devoluciones/reprocesos
  nunca absorben. La pantalla de Absorción solo muestra estos ítems (aclara
  que nacen en Cierre) y registra utensilios/feriados.

**Decisión de negocio (jul 2026):** un solo camino por compra — un utensilio
va SOLO a absorción, nunca a Activo fijo, para no contar su costo dos veces
(la otra opción, activo con depreciación, se descartó por complejidad).

**Nota contable:** al sumar la absorción al costo del producto, ese costo se
capitaliza en el valor del stock terminado. Es el comportamiento buscado
(que el precio de venta cubra estos gastos indirectos) y replica el Excel;
en el balance, el costo pendiente de absorber baja el patrimonio hasta que
las producciones lo trasladan al stock. Nueva pantalla **Absorción** (grupo
*Producción*). Verificado: motor (reparto, regla de 3, ítem saldado) con
script de rollback, y las tres puntas (utensilio/feriado/merma → absorbidas
en una producción real) contra la BD; datos de prueba limpiados.

### 1.5 Simulación de nuevo producto (3 escenarios de costo) — del Excel
Réplica de la hoja de simulación del Excel (de las más usadas y más lentas).
Para una receta hipotética (ej. 20 L de jarabe base + 5 kg de azúcar para
30 L de producto nuevo), calcular el costo unitario por litro en 3
escenarios según el histórico real de cada insumo: la vez más barata, el
promedio ponderado y la vez más cara (para intermedios, por litro producido;
para MP, por kilo comprado). Con la capacidad de la botella (ej. 0.75 L →
litros/0.75 botellas) y las botellas por paquete (3.9), da el costo por
botella y por paquete en los 3 escenarios. Todo dinámico: se ajustan las
cantidades para ver hasta dónde el producto nuevo es rentable. Es solo
lectura (no toca stock ni dinero): un servicio de consulta + una pantalla.

**Estado: implementado (jul 2026).** `servicios/simulacion.py` +
`rutas/simulacion.py` (`POST /simulacion`, `GET /simulacion/referencia`) y la
pantalla **Simulación** (grupo *Producción*, antes de Prod. Intermedia: la
pregunta "¿conviene?" va antes de producir). Sin migración ni tablas nuevas:
lee `Compra` y `Produccion_Intermedio`. Es `POST` aunque no escriba nada,
porque la receta hipotética es una lista que no entra cómoda en la query
string (mismo criterio que `/ventas/preview-reparto`).

**Decisión de negocio 1 — ventana de tiempo configurable (12 meses por
defecto), no todo el histórico.** Al medirlo contra los datos reales, la
diferencia era decisiva: en el insumo más comprado, todo el histórico da un
rango de 1,00 a 17,33 (17x) mientras que los últimos 12 meses dan 16,00 a
17,33 (1,1x). Con el histórico completo, el "escenario más barato" quedaba
anclado a un precio de hace 5 años que ya no se consigue, y hacía ver
rentable un producto por un costo imposible. Se eligió **configurable en
pantalla** (y no fijo en 12) porque además sirve para detectar datos
sospechosos: si al ampliar la ventana aparece un precio muy por debajo del
actual, es candidato a revisar (ver 5.2). `0 = todo el historial`.

Un insumo **sin movimiento en la ventana** cae a su último precio conocido y
se marca con un aviso en su fila, en vez de quedar en cero: un cero
silencioso haría ver el producto más barato de lo que es. Si nunca se compró,
la fila queda en "—" y la respuesta trae `incompleto: true`, que la pantalla
muestra como advertencia de que el total se queda corto.

**Decisión de negocio 2 — promedio ponderado por cantidad** (Bs totales ÷
cantidad total), no promedio simple de precios unitarios: una compra de 1 kg
no puede pesar lo mismo que una de 100 kg. Es el mismo criterio del costo
promedio del stock consolidado, así que los números son comparables entre
pantallas.

**Decisión de negocio 3 — los escenarios son SOLO insumos**, igual que las
recetas de 3.6: las horas de un producto que todavía no existe no se saben, e
inventarlas ensuciaría la comparación entre escenarios. Pero como el costo de
insumos solo no alcanza para decidir un precio, la pantalla muestra además
tres indicadores de referencia **no editables** en Bs/botella —**mano de
obra**, **absorción** (1.4) y **gastos extra** (1.1)— sacados del histórico
real de la misma ventana, y una tabla final con los 3 escenarios ya sumados a
esa carga fija.

Los tres indicadores se calculan como **total Bs ÷ total botellas del
período**, no como promedio de los ratios mensuales. Con el promedio de
ratios, un mes de poca producción pesa igual que uno de mucha, y como los
meses flacos tienen ratios altísimos (el rango mensual real va de 0,11 a 2,40
Bs/botella, 22x) el resultado sale ~17% inflado. El total sobre total
responde de verdad "cuánto carga una botella".

Dato que salió de los datos reales al construirlo: la mano de obra por
botella de los últimos 12 meses casi **duplica** la del histórico completo.
Es otra razón para que la ventana sea explícita y visible en pantalla.

Verificado contra la BD real: aritmética cruzada a mano (30 L ÷ 0,75 = 40
botellas; costo total ÷ botellas × paquete; + carga fija), los bordes
(rendimiento 0, receta vacía, sin litros por botella, ventana sin compras que
dispara el fallback) y el recorrido completo en la pantalla en vivo, incluido
el re-cálculo automático al mover la ventana.

---

## 2. LÓGICA FINANCIERA DE REPARTO POR PRIORIDAD DE CUENTAS

(Ya documentada en detalle en DECISIONES_DISENO.md como pendiente.)

Reparto de gastos/compras/pagos con aportes + prioridad:
1. Aportes explícitos primero (cónyuge, banco ponen montos fijos, registrados
   como fuente externa; si es de fuera no descuenta de cuentas internas).
2. El faltante se cubre por orden de prioridad según el tipo:
   - Gastos familiares: primero Billetera Casa, luego Billetera Fábrica.
   - Compras de MP y pagos a trabajadores: primero Fábrica, luego Casa.
   - Ventas (ingreso): reparto 70/30 (Fábrica/Casa) una vez recuperado lo invertido.
3. Regla: sumatoria de fuentes seleccionadas >= sumatoria de gastos.

Se construye como capa de orquestación por encima de las operaciones base (que ya
existen). Probablemente requiere endpoints nuevos que reciban el reparto completo
y ejecuten varias operaciones coordinadas. Corresponde a las pantallas del Excel
con columnas FUENTE / DISPONIBLE / UTILIZADO / ESPECIFICACIÓN / GRUPO.

**Detalle del 70/30 según el Excel (jul 2026):** el reparto de una venta no
es un 70/30 plano. Cada producto terminado lleva un acumulado de todos los
tiempos (ventas, entradas, salidas, gastos extra prorrateados → saldo):
- Si su saldo es <= 0 (el producto aún no devolvió a la fábrica lo invertido
  en producirlo), el 100% del ingreso va a Billetera Fábrica hasta llegar a
  0; si una venta cruza el cero, solo el remanente se reparte 70/30.
- Si su saldo ya es positivo, se aplica el 70/30 directo.

La "inversión de la fábrica" en un producto es todo lo gastado en
producirlo (se deriva de las producciones). El porcentaje (70) es
configurable — en el Excel era una celda global; candidato a
`app/config.py`. Este acumulado por producto además responde "¿este
producto ya rentó la fábrica?"; hoy es de todos los tiempos — evaluar
verlo también por mes (Power BI, 8.1).

**Estado (jul 2026): 2A + 2B implementados; 2C pendiente.**
- **2A — Rol de cuenta** (migración 019): columna `Rol_Cuenta`
  (FABRICA/CASA/OTRA), editable en el catálogo de Cuentas (el `Catalogo`
  genérico ahora soporta campos tipo *select*). Las reglas de prioridad se
  apoyan en el rol, no en el nombre.
- **2B — Reparto de gasto por prioridad** (`app/servicios/reparto.py`):
  pantalla **Gasto por prioridad** (grupo *Finanzas*). Das el total + tipo
  (familiar → Casa→Fábrica; de fábrica → Fábrica→Casa) y el sistema **propone**
  de qué cuentas sacar (drena por prioridad de rol, respetando saldos y
  partiendo entre cuentas), el usuario ajusta, y se registra como **varios
  movimientos SALIDA coordinados** (atómico). Orden de prioridad en
  `PRIORIDAD_CUENTAS` (`app/config.py`). Verificado con prueba de integración
  (orden por prioridad, split, atomicidad, cobertura).
- **Deferido de 2B — actualizado (jul 2026).** La nota original decía que
  compras y pagos por prioridad quedaban fuera. Revisado contra el código,
  eso ya no es exacto: **compras y gastos SÍ se reparten por prioridad**
  (`servicios/compras_lote.py` y `gastos_lote.py`, con `compras-lote` y su
  `preview`, drenando Fábrica→Casa). Lo que sigue pendiente es:
  - **Pagos a trabajadores por prioridad** (`servicios/pagos.py` no usa
    `PRIORIDAD_CUENTAS`). Acá sí aplica la limitación original: `Pago_Trabajador`
    enlaza **un solo** `Id_Movimiento`, así que partir el pago entre cuentas
    rompe ese enlace y el cálculo del balance — requiere cambio de modelo, no
    es trabajo de pantalla.
  - Los **aportes externos** integrados al reparto (hoy se cargan con
    `INGRESO_EXTERNO` y el gasto sale de esa cuenta).
- **2C — Reparto 70/30 de ventas (en progreso, por tajadas):**
  - ✅ **Tajada 1 — Acumulador de inversión/ingresos por producto**
    (`app/servicios/saldo_producto.py`, `GET /saldo-productos`, de solo
    lectura). `saldo = ingresos acumulados de sus ventas − inversión
    acumulada en producirlo` (todos los tiempos, **por producto**, no por
    lote). Se calcula al vuelo (no se guarda en columna): es una suma sobre
    `Produccion` + `Detalle_Venta` que ya existen, el volumen es chico, y
    evita que un total corriente se desincronice del dato real. Incluye
    `saldo_hace_dias` (default 30) como señal rápida de tendencia reciente
    en pantalla, sin sustituir el análisis mensual completo (que sigue en
    Power BI, 8.1) — esto es solo un indicador de recuperación de capital,
    no de rentabilidad del período. Verificado con curl contra la BD real y
    cruzado a mano contra las tablas crudas (coincide exacto).
  - ✅ **Tajada 2 — Integrar el 70/30 en la venta.** Al registrar una venta
    (`reparto=True` por defecto), el ingreso de cada línea se reparte entre la
    cuenta **FABRICA** y la **CASA** (únicas de su rol) según la recuperación de
    inversión del producto: mientras el saldo sea < 0, 100% a Fábrica hasta
    llegar a 0; el excedente (y todo si ya recuperó) se reparte
    `REPARTO_VENTA_FABRICA` (0.70, `app/config.py`) / resto a Casa. El saldo se
    acumula línea por línea (dos líneas del mismo producto respetan el cruce del
    cero). Cada línea genera una `ENTRADA` por destino con monto > 0.
    `reparto=False` vuelve al modo clásico (cuenta explícita por línea).
    Frontend: la pantalla de Ventas **ya no pide cuenta por línea** y muestra la
    vista previa del reparto (Fábrica/Casa) vía `POST /ventas/preview-reparto`.
    Verificado con la función de división (recuperado, sin cruzar, cruzando y
    justo en cero) e integración con snapshot/restauración de las cuentas
    reales. **2C completo.**

---

## 3. INVENTARIO Y PRODUCCIÓN

### 3.1 FIFO automático (primero en entrar, primero en salir)
En vez de que el usuario elija lote a lote qué consumir, el sistema descontaría
automáticamente de los lotes más antiguos primero. El usuario diría "usé 5 kg de
azúcar" y el sistema resuelve de qué lotes. Simplifica mucho la experiencia.
Cambio de lógica en el backend (los servicios hoy reciben el lote explícito).

**Ampliación (jul 2026):** FIFO es además la base de las pre-recetas (3.6),
del cierre semanal (3.7) y de la venta con lotes automáticos (6.12). El
patrón preferido: el sistema **propone** los lotes del más antiguo al más
nuevo (respetando restos) y el usuario puede editar antes de confirmar —
sugerencia FIFO, no imposición.

**Estado: implementado.** Servicio `servicios/fifo.py` (`resolver_fifo`) +
endpoint `GET /fifo/{origen}/{id}?cantidad=X` (origen: MP / INTERMEDIO /
TERMINADO). Ordena los lotes con stock por (fecha, id) y reparte la cantidad
del más antiguo al más nuevo respetando restos; devuelve las asignaciones y
un `faltante` si no hay stock suficiente (no toca la BD, solo propone).
Componente `SelectorFifo` (botón "Resolver FIFO" = elegir producto +
cantidad → pre-llena la lista), conectado a Producción Intermedia y
Terminada (secciones de MP e intermedio); el picker manual por lote sigue
ahí para casos puntuales. La venta con lotes FIFO se conecta al reconstruir
esa pantalla en 6.12. Verificado con curl (orden por fecha real, faltante).
Nota: FIFO calcula sobre el restante actual de cada lote, sin descontar lo
ya agregado a la lista en curso; como es una sugerencia editable, el usuario
revisa antes de confirmar y el backend valida igual el stock.

### 3.2 Redondeo a cero bajo umbral
Si un lote queda con un resto minúsculo legítimo, considerarlo agotado bajo cierto
umbral. Nota: el uso de `numeric`/`Decimal` ya evita la basurita de punto flotante
(el 1.4e-17), así que esto solo aplicaría a restos reales pequeños. Actualmente se
maneja vía el módulo de mermas.

**Estado: implementado.** Constante `UMBRAL_STOCK_MINIMO` en `app/config.py`
(0.0001), aplicada en los 13 filtros de "lotes con stock disponible" (listas,
desplegables y cálculo de balance). Solo afecta visibilidad/cálculo: un lote
bajo el umbral deja de contar como disponible, pero la fila con su resto
sigue existiendo en la BD (ver 3.5).

### 3.3 Mermas de producto terminado e intermedio en cadena / reproceso
El backend soporta reproceso (dos registros enlazados por Ref_Reproceso). La
pantalla de mermas cubre merma/ajuste/devolución sobre los tres orígenes, pero el
reproceso completo no tiene interfaz aún.

**Ampliación (jul 2026):** verificado en el código — hoy una DEVOLUCION solo
suma stock al lote, no mueve dinero. Falta el caso real completo: el cliente
devuelve producto echado a perder, se le devuelve su dinero (SALIDA de una
cuenta, idealmente vinculada a la venta original) y el producto devuelto o
se desecha (merma cuyo costo absorben las producciones futuras, ver 1.4) o
se reprocesa (ej. reciclar solo la botella). La edición actual sirve para
errores de tipeo (puse 15 y eran 16), no para este flujo.

**Decisión de alcance (jul 2026) — antes de implementar:**
- **Devolución = flujo completo**, dos partes en un solo acto:
  1. **SALIDA de dinero** de una cuenta (idealmente vinculada a la venta
     original) por lo que se le devuelve al cliente.
  2. **Destino del producto devuelto**, a elegir: (a) **vuelve al stock**
     (comportamiento actual: suma stock al lote); (b) **se desecha como
     merma**, que absorbe su costo hacia producciones futuras (ver 1.4, ya
     conectado a Cierre→Mermas); o (c) **se reprocesa**.
- **Reproceso = una producción marcada como reproceso** que consume una
  cantidad **PARCIAL** de un lote (no necesariamente todo — ej. de 60
  botellas, reprocesar solo 10 porque se rompió la tapa) y genera un **lote
  nuevo**, enlazado con el de origen por `Ref_Reproceso` (columna que ya
  existe en `Movimiento_Inventario`, aún sin usar).

**Estado: implementado.** Alcance decidido (jul 2026): devolución con vínculo
**opcional** a la venta, y reproceso **terminado→mismo producto** con insumos
nuevos. Nueva pantalla **Devoluciones** (grupo *Cierre*).
- Servicio `devoluciones.py` (`registrar_devolucion`): una operación atómica
  que hace el **reembolso** (SALIDA de una cuenta, puede ser 0) y **siempre**
  devuelve el producto al stock del lote original (`DEVOLUCION` ENTRADA), y
  según el destino: **STOCK** (se queda), **MERMA** (lo desecha con `MERMA`
  SALIDA + absorción del costo, ver 1.4) o **REPROCESO**. El "entra y después
  sale" deja el rastro real en inventario. Con `id_venta` valida que el lote
  se vendió ahí y que no se devuelva más de lo vendido.
- Servicio `reproceso.py` (`reprocesar`): SALIDA parcial del lote origen
  (marcada `REPROCESO`, `Ref_Reproceso` = lote nuevo) + crea un lote nuevo del
  mismo producto cuyo costo = *(costo del origen × cantidad)* + insumos nuevos
  (tapas=MP + trabajo), **sin re-absorción** (esas botellas ya absorbieron).
  Se expone también suelto (`POST /reprocesos`) para roturas en depósito.
- Se refactorizó `inventario.py` a un core sin commit (`_aplicar_movimiento_
  inventario`) para componer dinero + stock + merma/reproceso en una sola
  transacción. Rutas: `POST /devoluciones`, `POST /reprocesos`, y
  `GET /ventas/{id}` (detalle para el vínculo). Verificado con una prueba de
  integración de los 4 caminos sobre la BD real (datos `__TEST`, borrados) y
  `vite build`.

### 3.4 Corrección de jornadas mal registradas
Caso: registré 8 horas a Juan pero eran de Pedro, o Juan no vino ese día. Necesita
poder editar/anular una jornada (operación de edición, distinta de una merma de
inventario). Relacionado con la falta general de "editar" (ver 6.1).

**Estado: implementado.** `PATCH /jornadas/{id}` (corrige horas y/o trabajador)
y `DELETE /jornadas/{id}` (anula, borrado real). Solo permitido si la jornada
está **intacta**: nada de sus horas se usó en una producción y no está pagada
— si cualquiera ya pasó, se bloquea (backend y frontend), para no dejar
inconsistente un costo o un pago ya hechos. En la tabla de Jornadas, los
botones Editar/Eliminar aparecen al pasar el mouse, solo en filas intactas.
Se agregó también la columna "Horas restantes".

### 3.5 Merma automática de residuos bajo el umbral
El redondeo a cero (3.2) solo esconde de las listas los lotes con resto bajo
`UMBRAL_STOCK_MINIMO`; la fila en la BD sigue con su resto positivo (no afecta
el balance porque las mismas consultas ya excluyen esos lotes). Si se quiere
"cerrar" esos lotes de verdad y no solo ocultarlos, se necesitaría generar una
merma automática (evento de inventario, no borrar la fila — ver el principio
de inmutabilidad del histórico) cuando un consumo deja el resto bajo el
umbral. Falta decidir el disparador: ¿en cada consumo?, ¿una acción manual
"limpiar residuos"? No es urgente: sin impacto financiero ni visual hoy.

**Estado: implementado (jul 2026).** `servicios/residuos.py`,
`GET /residuos` + `POST /residuos/limpiar`, y una sección nueva en la pantalla
de **Mermas**, arriba de las tablas de stock.

**Decisión del disparador: manual y en dos pasos, nunca automático.** Primero
"Buscar residuos" lista exactamente qué lotes se pondrían en cero, con un
checkbox por fila (todos tildados; se destilda el que se quiera dejar), y
recién al confirmar se aplican las mermas, solo sobre lo tildado. La otra
opción anotada —mermar solo en cada consumo— generaría movimientos de
inventario que nadie pidió ni vio.

Detalles que importan:
- **No borra la fila**: cierra el lote con una `MERMA` por el resto exacto,
  respetando la inmutabilidad del histórico.
- **No absorben costo** (1.4). Una merma normal reparte su costo entre las
  botellas futuras; estos restos valen fracciones de centavo y crear un ítem
  de absorción por cada uno sería ruido en la pantalla de Absorción.
- **El filtro es `0 < restante <= umbral`**. El límite inferior es
  deliberado: los restantes **negativos** (los 5 que quedaron de la migración
  del excel, ver 8.4) quedan fuera — no son residuos, y "limpiarlos" con una
  merma agregaría una salida sobre un lote que ya está en rojo.
- **Se re-lee el resto de la BD al confirmar**, no se confía en el que vino
  del navegador: si el lote cambió entre la vista previa y la confirmación,
  esa fila se omite con aviso en vez de mermar algo que ya tiene stock útil.
- El umbral se muestra en pantalla pero **viene del endpoint**, para no
  duplicar la constante de `config.py` en el frontend.
- De paso, las tres tablas de stock de esa pantalla (163 + 16 + 97 lotes
  apilados) pasaron a `TablaFiltrable` plegable con buscador.

Verificado con una prueba dentro de una transacción **revertida al final**
(la BD quedó intacta): detecta el residuo, ignora el lote sano y el negativo,
lo deja en cero, deja de listarlo, y una segunda limpieza del mismo lote se
omite sin romper.

### 3.6 Pre-recetas (producción intermedia pre-llenada) — del Excel
Plantilla por producto intermedio ("Jarabe Base 1 = 5 kg de azúcar + 3 L de
alcohol"): al elegirla, el formulario de producción se pre-llena resolviendo
los lotes por FIFO (3.1) y respetando restos (si al lote más viejo le quedan
2 kg, propone 2 de ese y 3 del siguiente). Siempre editable y no
restrictivo: las horas de trabajadores cambian cada día, y un lote puede
llevar algo extra o de menos. Requiere tablas nuevas de receta (cabecera +
detalle de insumos).

**Estado: implementado.** Migración 015 crea `Receta` (produce un intermedio,
con `Rendimiento_Receta` base) y `Receta_Detalle` (insumos MP/intermedio +
cantidad; el trabajo NO va en la receta). Servicio `recetas.py` con
`aplicar_receta`: escala cada insumo por `cantidad / rendimiento` (decisión
de negocio jul 2026: la receta **se escala** a lo que se produce, no es
cantidad fija) y resuelve los lotes por FIFO (3.1), devolviendo los insumos
pre-resueltos + los `faltantes` si no hay stock. CRUD en `rutas/recetas.py`
(crear/editar/habilitar/borrar; editar reemplaza cabecera+detalles, borrar es
seguro porque la receta es solo plantilla, no la referencia ninguna
producción). Nueva pantalla **Recetas** (grupo *Producción*) y un control
"Aplicar receta" en Producción Intermedia que pre-llena producto, cantidad e
insumos (editable; el trabajo se agrega a mano). Verificado con curl (crear,
escalar 5+3 con rendimiento 10 a producir 30 → 15+9 resueltos por FIFO,
faltantes, editar rendimiento, borrar) y build de frontend; datos de prueba
limpiados.

**Ampliación (jul 2026) — recetas también para producto terminado + fixes.**
Migración 016: `Receta` gana `Tipo_Receta` (INTERMEDIO/TERMINADO) e
`Id_Producto_Terminado`, así que una receta puede producir un terminado, no
solo un intermedio. La pantalla Recetas separa las dos clases en secciones
plegables (colapsadas al inicio) y "Aplicar receta" está también en
Producción Terminada (filtrando por tipo). Dos correcciones de raíz al probar:
- **Insumos repetidos en la receta** (la misma materia dos veces) se **suman**
  antes de resolver FIFO (`aplicar_receta`); antes cada fila se resolvía por
  separado desde el stock completo y tomaba el mismo lote dos veces. Además,
  al **definir/guardar** una receta el mismo insumo se fusiona en una sola
  fila: en el editor (frontend) y de forma defensiva al guardar (backend).
  Migración 017 limpió las recetas ya guardadas con insumos duplicados
  (suma las cantidades en una fila por insumo; totales idénticos).
- **Lotes repetidos en una producción** (5+5 del mismo lote) ahora se agrupan
  en el backend antes de validar/descontar (`servicios/agrupar.py`), en
  Producción Intermedia/Terminada y en Ventas; antes cada línea pasaba la
  validación por separado y al descontar dejaba el lote en **negativo**. En
  el frontend, `insumos.js` (`fusionar`) une líneas del mismo lote en una
  sola (FIFO, receta y agregado manual), para que no se vean filas
  duplicadas. Verificado: 5+5 de un lote con 5 ahora se rechaza; 3+2 deja el
  lote en 0, no negativo.

### 3.7 Cierre semanal de producción con prorrateo de horas standby — del Excel
Cómo se asignan hoy las horas directas en la práctica (no hay capataz que
mida qué produjo cada quien, y una producción puede quedar a medias hasta el
día siguiente): las jornadas de la semana se acumulan en standby y el
sábado, al cerrar, se reparten entre los productos producidos esa semana en
proporción a sus botellas equivalentes. Ej: 32 botellas totales (20 de A, 7
de B, 5 de C) → PROD A se lleva 20/32 de las horas de **cada** jornada de la
semana. Cada producto conserva sus insumos reales (MP e intermedios se
registran por producción); solo las horas se prorratean. Hoy este cálculo se
hace a mano fuera del sistema; falta una pantalla de "cierre semanal" que
tome las jornadas en standby + las producciones de la semana y genere el
detalle de trabajo de cada una. Alimenta directamente las horas acumuladas
de 1.1.

**Estado: implementado.** Nueva pantalla **Cierre producción** (grupo
*Cierre*), con **vista previa + confirmar** sobre un **rango libre de dos
fechas** (no una semana fija). Flujo: durante la semana se producen los
terminados solo con MP+intermedios (sin trabajo) y las jornadas quedan en
standby; al cerrar, el servicio `cierre_semanal.py` reparte cada jornada
standby del rango **entera** entre los terminados del rango, por
`Cantidad_Producida` (botellas producidas, no restante), crea los
`Detalle_Prod_Trabajador` y **suma** el costo de trabajo al costo unitario de
cada lote (sin recalcular MP/intermedios/absorción). Decisiones: **solo
terminados** (los intermedios del rango no reciben horas — su mano de obra la
absorben las botellas; el modelo de horas heredadas es 1.1); **solo lotes sin
trabajo asignado** (los que ya lo tienen se saltan, no se duplica); la
**última línea de cada jornada absorbe el redondeo** para que su standby quede
en 0 exacto. Re-correr es seguro: al consumir el standby, un segundo cierre no
encuentra nada. `GET /cierre-semanal/preview` y `POST /cierre-semanal`.
Verificado con una prueba de integración del ejemplo exacto (20/7/5 con Juan
10h@20 y Pedro 6h@15 → A=181.25 Bs de trabajo, 19.0625 Bs/botella; suma de
trabajo = 290 sin fugas; re-cierre sin duplicar) y `vite build`.

### 3.8 Compra dividida en proporción (pliegos de etiquetas) — del Excel
Un pliego doble oficio cuesta 100 Bs y salen 5 etiquetas de A, 3 de B y 4 de
C, de tamaños distintos: el costo se reparte por **área** (área de cada
etiqueta × cantidad / área total del pliego) y cada tipo de etiqueta entra
como materia prima con su costo proporcional. Hoy se calcula a mano y se
ingresan como compras separadas. Pantalla auxiliar: una compra "madre" que
se despieza en N materias primas con reparto proporcional por área (o por
un factor genérico).

**Estado: implementado.** No fue necesaria una tabla nueva: la "compra madre"
es una sección de la pantalla **Compras** que reparte un `precio_total` entre
N líneas y registra **una `Compra` normal por línea**, todas del mismo
proveedor y cuenta, en **una sola transacción atómica** (o se registran todas
o ninguna). Cada línea lleva un **factor genérico** (no solo área: cualquier
número proporcional — peso, volumen...); el reparto es **solo por factor**
(`factor_línea / factor_total`) — la **cantidad NO pesa en el reparto**,
solo sirve para registrar el lote y calcular el precio unitario resultante
(así se ingresan bien los datos aunque cantidad y factor no guarden relación,
ej. 500 unidades chicas vs. 3 unidades grandes reparten por su factor, no por
cuántas hay). La **última línea absorbe el redondeo** para que la suma cierre
exacto con el total (no queda un resto de centavos suelto). El proveedor
elegible es la **intersección** de los proveedores activos de todas las
materias primas de las líneas (debe vender todas). Reutiliza crédito parcial
y pedido pendiente (5.1) repartidos con el mismo factor: si se paga solo una
parte, el faltante también se reparte y genera deuda al proveedor por línea
(la suma da la deuda total correcta). Se refactorizó `compras.py` igual que
`inventario.py` en 3.3: un core sin commit (`_aplicar_compra`) reutilizable
para componer varias compras en una transacción. Verificado con pruebas de
integración sobre la BD real (reparto exacto, crédito parcial, cantidad
desproporcionada al factor sin distorsionar el %, y que un fallo en una línea
no deja compras a medias) y `vite build`.

### 3.9 Botellas por paquete en Producto_Terminado — del Excel
Columna nueva `Botellas_Por_Paquete` (6, 8 o 1 según el producto, migración
simple). Habilita: resúmenes en paquetes equivalentes (4.7), el costo por
paquete en la simulación (1.5), y registrar producción/venta por paquete
con conversión automática a botellas.

**Estado: implementado (columna) + datos cargados (jul 2026).** La columna la
creó la migración 009 (default 1, `CHECK >= 1`) y el catálogo de Productos
Terminados ya la exponía editable vía el componente genérico `Catalogo`, con
su validación en `rutas/catalogos.py`. Lo único que faltaba eran **los
valores reales**, que estaban todos en el default 1.

**Decisión (jul 2026): los valores NO se versionan.** Cargarlos como una
migración `.sql` en el repo habría metido la estructura de packaging del
negocio (qué producto va en paquete de cuántas) en un repo que va a ser
público — exactamente lo que prohíbe la regla de no versionar datos de la
empresa. Y no es un cambio de esquema: la columna ya existía. Se cargaron con
un script de un solo uso **fuera del repo** (idempotente, con `--dry-run`
previo y verificación cruzada de ids contra la BD antes de escribir). Los
datos viven en PostgreSQL y los protege el respaldo de 8.3, no Git. El mismo
criterio aplica a futuras cargas de datos de negocio: script efímero, no
migración.

Efecto inmediato: la columna "paquetes equivalentes" de 4.7 dejó de ser una
copia de las botellas (todo estaba en 1) y ahora dice algo real.

**Derivado ya construido:** helper `fmtBotellasYPaquetes(botellas, bpp)` en
`frontend/src/formato.js`, que expresa una cantidad de botellas también en
paquetes ("56 botellas o 7 paquetes"). Omite los paquetes cuando `bpp <= 1`
o es nulo: en un producto suelto el paquete **es** la botella, y repetir el
mismo número con otro nombre confunde en vez de ayudar. Usado en el selector
"Aplicar receta" de Producción Terminada y en la tabla de Recetas (solo en
las de tipo TERMINADO — el intermedio rinde en su propia unidad y no se
empaqueta, ver la decisión de unidades más abajo). `rutas/recetas.py` agrega
`botellas_por_paquete` al payload, no nulo solo para recetas de terminado.

Pendiente de esta línea: los campos duales paquetes/botellas en Venta y
Producción Terminada (ver 6.13).

---

## 4. BALANCE

### 4.1 Separar compras de gastos de la semana
En el balance, compras y gastos son ambos movimientos de SALIDA y no se
distinguen bien. Falta separarlos usando el grupo del movimiento o el vínculo a
Compra. (TODO marcado en el servicio de balance.)

**Estado: implementado.** El bug real era más grande: los pagos a
trabajadores también generan un movimiento SALIDA, y antes se sumaban **todos**
(compras + gastos + pagos) como "compras_semana", con "gastos_semana" fijo en
cero. Ahora se separan los tres usando el vínculo real (`Compra.Id_Movimiento`,
`Pago_Trabajador.Id_Movimiento`); lo que sobra de las SALIDA sin esos vínculos
es, por descarte, el gasto. Migración 005 agrega `Pagos_Semana` a `Balance`
para que quede simétrico con Ventas/Compras/Gastos.

Además, nuevo endpoint `GET /balance-resumen-semana`: resumen día a día desde
la última foto guardada hasta hoy (ventas, compras, gastos, pagos + un
detalle tipo "Compra de: Azúcar 5 kg a 60 Bs" por evento), **sin necesidad de
tomar una foto nueva** — pensado para revisar el avance diario y notar si
algo no se registró. En Balance, 4 filas nuevas en la tabla comparativa y un
desplegable con el detalle día a día (colapsado por defecto).

### 4.2 Clasificación de activos fijos
La clasificación inmuebles/equipos/otros se hace buscando palabras en el nombre
del tipo de bien. Refinar con una clasificación explícita.

**Estado: implementado.** Migración 006 agrega `Categoria_Tipo_Bien` a
`Tipo_Bien` (INMUEBLE/EQUIPO/OTRO, constante `CATEGORIAS_TIPO_BIEN` en
`app/config.py` — ligada a las 3 columnas que ya existían en `Balance`:
`Total_Inmuebles`/`Total_Equipos`/`Total_Otros_Activos`, agregar una 4ta
categoría requeriría también una columna nueva ahí). Se elige al crear el
tipo de bien (no por activo individual); nuevo `PATCH /tipos-bien/{id}`
para corregirla después. El backfill de los 2 tipos que ya existían
reprodujo el criterio anterior por texto una sola vez (los que no
matchearon quedaron en OTRO por defecto, corregibles a mano). `balance.py`
(tanto la foto guardada como la vista previa en vivo `/balance-actual`)
ahora filtra por la columna explícita en vez de `ilike`. En **Activos**,
el formulario "Tipo de bien" pide la categoría al crear, y una tabla nueva
lista los tipos con su categoría y botón para editarla. En **Balance**, 3
filas nuevas (Inmuebles/Equipos/Otros) bajo "Activos fijos" en la tabla
comparativa, en ambas columnas (última foto y estado actual).

### 4.3 Patrimonio contable puro
Actualmente Patrimonio = Escenario A. Se podría distinguir un patrimonio contable
(activos a valor real) de los escenarios de liquidez.

**Estado: implementado.** Migración 007 agrega
`Valor_Stock_Producto_Terminado_Conservador` a `Balance`. Patrimonio dejó de
ser un alias de Escenario A: ahora valoriza el stock de producto terminado a
**costo o mercado, el menor** (criterio contable conservador: no reconoce la
ganancia de lo que todavía no se vendió), usando el costo real de cada lote
(`Produccion.Precio_Unitario_Producto_Terminado`) contra el precio de venta
recomendado. Escenario A/B/C no cambiaron — siguen siendo la vista de
liquidez ("cuánto tendría si liquido todo hoy"), con el stock terminado a
precio de venta. Las fotos ya guardadas antes de esta mejora conservan su
Patrimonio calculado con la fórmula vieja (inmutabilidad del histórico); solo
las fotos nuevas usan la fórmula conservadora. En **Balance**, nueva fila
"Stock producto terminado (costo o mercado, el menor)" en la tabla
comparativa, y las etiquetas de Escenario A / Patrimonio aclaran la
diferencia.

### 4.4 Informe comparativo entre balances
Generar automáticamente un reporte que compare dos fotos de balance semanales y
resalte qué cambió (costos, patrimonio, stock). Relevante dado que se eligió
Filosofía B para el costo de materia prima.

**Estado: implementado.** Sin migración: cada foto de `Balance` ya guarda todo
lo comparable (efectivo, stocks, escenarios, patrimonio, movimientos de su
semana). Solo hizo falta exponer el histórico y compararlo. En backend se
extrajo `serializar_balance()` en `servicios/balance.py` (antes la lógica
estaba incrustada en `/balance-ultimo`; ahora la reusan la última foto y el
listado, sin divergir) y se agregó `GET /balances`, que devuelve **todas** las
fotos ya serializadas, de la más reciente a la más antigua. En frontend, nueva
pantalla **Comparar cierres** (`/comparar-balances`, grupo *Cierre*) con dos
selectores (Foto A / Foto B) que listan el histórico por `#id — fecha` (el id
distingue fotos con la misma fecha); la tabla usa los mismos conceptos y
movimientos que Balance, con columna Diferencia (B − A) coloreada. Se distingue
a propósito de la pantalla de Balance: aquella compara "estado actual vs último
cierre" (mira al *ahora*), ésta compara "cierre X vs cierre Y" (mira al
*pasado*). Un campo que a una de las dos fotos le falta (columna agregada
después) se muestra "—" en vez de restar contra cero. **Impresión/PDF**: botón
"Imprimir / PDF" que dispara `window.print()`, tanto en la comparativa como en
la pantalla de Balance existente (pedido para llevar el reporte físico a la
fábrica); un bloque `@media print` en `App.css` oculta el menú y los controles
marcados con `.no-imprimir` y deja solo la tabla en negro sobre blanco.

### 4.5 Enriquecer la vista de balance en el frontend
La pantalla muestra patrimonio y escenarios. Ampliar para ver efectivo, stocks,
deudas por separado, y el detalle por producto.

**Estado: implementado.** Efectivo/stocks/deudas ya estaban separados en la
tabla de comparación. Se agregó el detalle por producto (terminado, intermedio,
materia prima) en tablas plegables (colapsadas por defecto) con buscador y
orden alfabético — reutiliza los endpoints `/stock-*-general` ya existentes, en
totales consolidados, no por lote. Solo cubre el **estado actual**; el detalle
histórico de la "última foto" queda pendiente, ver 4.6.

### 4.6 Detalle histórico por producto en la última foto
El detalle por producto de 4.5 solo cubre el estado actual (reutiliza
endpoints ya existentes, sin tocar el backend salvo por materia prima). La
tabla `Balance_Detalle_Producto` sí guarda un detalle histórico por cada foto
guardada, pero **solo de producto terminado** (no de intermedio ni materia
prima), y hoy no hay ningún endpoint que lo exponga.

Para mostrarlo también en la columna "Última foto" haría falta:
- Un endpoint nuevo, ej. `GET /balances/{id}/detalle`, que lea
  `Balance_Detalle_Producto`.
- Decidir si se amplía el modelo para capturar también intermedio y materia
  prima en cada foto (cambio de esquema, migración nueva), o si se deja el
  detalle histórico solo para terminado.

**Estado: implementado (jul 2026), con el modelo ampliado.** Se eligió la
opción completa (los cuatro bloques) y no la mínima, por una razón de
oportunidad: solo existía **una** foto y el sistema todavía no estaba en uso
real, así que ampliar el modelo no costaba histórico. Ese dato solo se puede
capturar hacia adelante — cuanto antes se amplía, antes empieza a servir.

**Migración 024:** tabla `Balance_Detalle` (`Tipo_Detalle` MP / INTERMEDIO /
TERMINADO / ACTIVO + id del item, descripción, cantidad, valor), que
reemplaza a `Balance_Detalle_Producto`. La migración **copia** las filas
existentes antes de hacer `DROP` de la vieja, así que no se perdió nada.
De paso, los **activos** ahora tienen detalle: la foto guardaba solo los tres
totales (inmuebles/equipos/otros), no qué activos los componían.

**Decisión de diseño — la descripción se guarda copiada, no por relación.**
Una foto tiene que poder leerse tal como era: si un producto se renombra (o
se borra porque nunca se usó), la foto de hace un año debe seguir diciendo
cómo se llamaba entonces. Por lo mismo `Id_Item_Balance_Detalle` **no lleva
foreign key** — apunta al catálogo que corresponda según el tipo, y no debe
bloquear el borrado de un item.

**Frontend:** componente `DetalleFoto.jsx` (un desplegable que adentro tiene
los cuatro bloques, cada uno plegable con buscador), usado dos veces en
**Comparar cierres**: "Detalle Foto A" y "Detalle Foto B", debajo de la tabla
comparativa. Se piden al desplegar, no al cargar la pantalla: son dos fotos y
cada una puede traer cientos de filas que casi nunca se miran. Van marcados
`no-imprimir` (el PDF del cierre es la tabla comparativa, no el listado
completo de items).

**Código de color por foto.** Cada foto tiene su color en toda la pantalla
—etiqueta del selector, cabecera de su columna en la tabla comparativa, y el
título y borde de su bloque de detalle— para no perder de vista cuál es cuál
al ir y venir entre las dos. El título de la foto manda visualmente sobre sus
sub-bloques (más grande, en negrita y con fondo tintado; los sub-bloques van
en gris neutro), que era la jerarquía pedida.

Tres decisiones: los colores son **variables CSS** (`--foto-a` / `--foto-b` en
`index.css`) con **variante propia para modo oscuro** —el azul y el ámbar del
tema claro no tienen contraste suficiente sobre el fondo oscuro—; se eligió
**azul vs ámbar y no rojo/verde**, porque ese par se distingue también con
daltonismo; y el color **nunca es la única pista**, siempre acompaña al texto
"Foto A"/"Foto B". Las cabeceras de columna necesitan
`.tabla-balance th.col-foto-a` y no solo `.col-foto-a`: la regla
`.tabla-balance th { color: var(--text-h) }` tiene más especificidad y le
ganaba al selector de clase suelto.

**Un bloque vacío se muestra igual, dicho con todas las letras** ("sin detalle
guardado en esta foto"). Ocultarlo era la primera versión y estaba mal: al
comparar una foto vieja —que solo guardaba producto terminado— contra una
nueva, los bloques faltantes se leían como "no tenía stock de eso" en vez de
"no se guardaba". Un hueco de datos y un cero significan cosas distintas.

**Bug latente encontrado de paso:** `tomar_balance` no tenía default de fecha,
así que `POST /balances` sin `fecha_balance` fallaba con un "Error de base de
datos" genérico. No se notaba porque la pantalla siempre manda la fecha. Ahora
usa `fecha or date.today()`, la convención del resto del backend (6.10).

Verificado contra la BD real: los cuatro bloques de la foto nueva cruzan
**exacto** contra los totales que la misma foto guarda por separado (materia
prima, intermedio, terminado y activos), la foto vieja conserva sus 58 filas
copiadas por la migración, y el recorrido completo en pantalla (abrir las dos
fotos, sus sub-bloques y el contenido de una tabla). Respaldo `pg_dump` previo
al `DROP`.

### 4.7 Paquetes equivalentes y redondeo a 2 decimales — del Excel
En el detalle de producto terminado del balance (y donde aplique), además de
botellas mostrar una columna "paquetes equivalentes" (botellas /
`Botellas_Por_Paquete`, ver 3.9). Y redondear la **presentación** de los
números no enteros a 2 decimales en todas las tablas (solo presentación: los
cálculos internos siguen en `Decimal` completo).

**Estado: implementado.** `stock-terminado-general` agrega
`botellas_por_paquete` y `paquetes_equivalentes` (stock / botellas por
paquete); nueva columna en la tabla de Producto Terminado del detalle de
Balance. Para el redondeo, se generalizó el uso de `fmtNumero`/`fmtMoneda`
(`formato.js`, ya existían pero solo se usaban en Balance/Activos desde la
mejora 7.2) a las tablas de Compras, Producción Intermedia/Terminada,
Ventas, Mermas, Jornadas, Proveedores, Deudas, Absorción y el componente
genérico `Catalogo` (columnas numéricas). Verificado con curl y build de
frontend.

### 4.8 Utensilios sin absorber + orden y lectura de la tabla de balance

**Estado: implementado (jul 2026).** Dos cosas que salieron de usar el
balance con los datos reales ya migrados.

**a) Los utensilios sin absorber no estaban en ninguna línea.** Un ítem de
absorción (utensilio, feriado) se compra por un costo y se reparte entre N
botellas estimadas. Mientras queden botellas por absorber, esa fracción ya
se pagó pero todavía no está en el costo de ninguna botella: no aparecía ni
en efectivo, ni en stock, ni en activos fijos. Se perdía (un par de
utensilios recientes y unos feriados que aún no terminaban de absorber).
Migración 021 (columna `Valor_Utensilios_Sin_Absorber` en `Balance`), helper
`valor_utensilios_sin_absorber` en `servicios/balance.py`
(`costo * botellas_restantes / botellas_estimadas`), suma al Escenario B y
por arrastre al A y al patrimonio. Devuelve `Decimal`, no `float`:
`tomar_balance` suma con montos que vienen de la BD como `Numeric` y
`Decimal + float` es un TypeError (ver sección 6 de DECISIONES_DISENO.md).
Las fotos anteriores quedan en NULL, no en 0 — no valían cero, es que no se
medían.

**b) La tabla no se entendía por el orden.** Los componentes estaban
mezclados con los subtotales, así que no se veía de dónde salía cada
escenario. Ahora sigue la convención contable —componentes, línea,
subtotal— y se lee sola:

```
  + Efectivo · − Deudas ............................ = Escenario C
  + los cuatro stocks .............................. = Escenario B
  + Activos fijos (total de los * de arriba) ....... = Escenario A
```

Las filas se movieron a `frontend/src/filasBalance.js`, compartido por
Balance y Comparativa: antes estaba duplicado en las dos páginas con un
comentario pidiendo mantenerlas iguales a mano. Cada fila declara su `tipo`
(componente / subtotal / subcomponente / grupo / nota / separador) y el
`signo` con el que entra al subtotal; el CSS (`.tabla-balance` en App.css)
le da indentación, línea de cierre y fondo. Importes a la derecha con
`tabular-nums` (si no, los miles no alinean entre filas y no se pueden
comparar de un vistazo) y subtotales negativos en rojo. Se agregó una regla
`@media print` propia: la regla general pone borde a toda celda, lo que
convertía el balance en una grilla y borraba la jerarquía.

Verificado contra el frontend en vivo: orden de filas, CSS computado en
claro y oscuro, y cero errores de consola.

### 4.9 Depreciación de activos fijos (pendiente)
Un `Activo` queda a valor pleno para siempre: un vehículo vale lo mismo en
el balance el día que se compró y cinco años después. Con la
decisión de jul 2026 de cargar el equipo durable como Activo (ver
DECISIONES_DISENO.md 8.2), el parque de equipos va a crecer y el Escenario A
se va a ir separando de la realidad.

Hoy no molesta: los activos son pocos y grandes (casa, vagoneta, un lote de
bienes), y su valor está puesto a mano, así que se puede corregir editándolo
cuando haga falta. Revisar cuando haya varios equipos cargados uno por uno.
Si se hace, decidir primero el método (lineal es lo más simple: valor / años
de vida útil) y si la depreciación debe tocar el costo de la botella o solo
el balance — que es la misma tensión de 8.2.

---

## 5. PROVEEDORES

### 5.1 Base de datos de proveedores
Agregar tabla `Proveedor` y un `Id_Proveedor` en `Compra`, para comparar precios
de la misma materia prima entre proveedores y decidir cuál conviene.

**Estado: implementado (base).** Migración 011 agrega:
- `Proveedor` (nombre, celular, latitud/longitud para el futuro ruteo con
  Maps —mismo patrón que `Cliente`—, `Habilitado_Proveedor`).
- `Proveedor_Materia_Prima`: tabla puente "qué proveedor vende qué", con su
  propio `Habilitado_*` y UNIQUE por par. Permite deshabilitar "Juan-azúcar"
  sin tocar "Juan-alcohol", sin perder el historial de compras a Juan.
- `Compra.Id_Proveedor` (nullable: las compras históricas no tienen
  proveedor; el flujo nuevo lo exige).

CRUD completo en `rutas/proveedores.py` (editar/habilitar/borrar con el
guardrail de 6.1: solo se borra si no tiene compras), gestión de las
materias que vende cada proveedor, y `GET /proveedores-por-materia/{id}`
que alimenta el **desplegable inteligente** de Compras: 0 proveedores
activos → se bloquea la compra pidiendo registrar uno (así el catálogo se
llena y nadie queda "solo en la cabeza"); 1 → autoselección sin desplegable;
>1 → se elige. La regla vive en el servicio `compras.py` (fuente única de
verdad), el frontend solo la refleja. Nueva pantalla **Proveedores** (grupo
*Configurar*) y `GET /comparacion-precios-proveedor` (precio unitario
mín/promedio/máx/último por materia y proveedor, desde el historial de
compras) mostrado como tabla. Verificado con curl (los 4 caminos de
validación de compra, toggle de vínculo, comparación) y build de frontend;
datos de prueba limpiados.

**Decisión de negocio (jul 2026):** toda compra queda atada a un proveedor
(se eligió obligar, no solo sugerir), para forzar que el catálogo de
proveedores se complete. Si en la práctica molesta, se puede relajar a
opcional en el servicio (un solo punto).

**Ampliación: implementado (jul 2026) — compras a crédito y pedidos pendientes.**
Migración 013 agrega `Compra.Recibida_Compra` y `Deuda.Id_Proveedor`.
`registrar_compra` ganó dos parámetros retrocompatibles:
- **Crédito parcial (`monto_pagado`):** el lote guarda siempre el precio
  COMPLETO (costo real del producto); se paga solo `monto_pagado` de la
  cuenta y el faltante se vuelve deuda al proveedor. La deuda se agrupa
  **por proveedor** (una deuda que acumula, `deuda_de_proveedor` con
  `Id_Proveedor`), decisión de negocio de jul 2026, y aparece/paga desde la
  pantalla de Deudas.
- **Pedido pendiente (`recibida=False`):** el lote nace con
  `Cantidad_Restante = 0` (invisible como stock, sin tocar las ~13 consultas
  que ya filtran por restante > 0) hasta `recibir_compra`, que pone el
  restante en la cantidad y hace aparecer el stock. Endpoints
  `GET /pedidos-pendientes` y `POST /compras/{id}/recibir`.

En el frontend, Compras tiene checkboxes "a crédito" (con aviso "se creará
deuda de X a [proveedor]") y "pedido pendiente", más la sección de pedidos
por recibir. Verificado contra el balance en vivo: compra full (patrimonio
estable), crédito (efectivo −pagado, stock +completo, deuda +faltante,
patrimonio estable), pendiente (patrimonio baja temporalmente hasta recibir).

**Limitación conocida:** un pedido pendiente ya pagado en parte baja el
efectivo y sube la deuda, pero como el stock aún no llegó, el balance no lo
cuenta como activo hasta recibirlo (no se modela "anticipo a proveedores").
Para pedidos de pocos días es despreciable.

### 5.2 Detección y corrección de precios sospechosos en compras (pendiente)
Salió al construir la simulación (1.5): hay materias primas cuyo precio
unitario mínimo histórico es varias veces más barato que cualquier compra
reciente (en un caso, 17x). Parte será inflación real de 5 años, pero parte
son probablemente **errores de carga** arrastrados desde el Excel (una
cantidad o un precio mal tipeado en su momento).

Hoy la simulación los deja ver —ampliando la ventana aparecen como un mínimo
muy por debajo del resto— pero **no hay forma de corregirlos**: `Compra` no
tiene `PATCH`, a diferencia de las jornadas (3.4). Faltaría:
- Un reporte de outliers: por materia prima, las compras cuyo precio unitario
  se aleja mucho de la mediana de su año (ej. más de 3 desviaciones, o un
  factor configurable).
- Decidir **si una compra vieja se puede editar**, que no es obvio: su lote ya
  alimentó producciones cuyo costo se calculó con ese precio, y corregirlo
  hacia atrás cambiaría costos ya cerrados. Probablemente la respuesta sea
  marcar la compra como "dato dudoso" y excluirla de las estadísticas, sin
  tocar el histórico (mismo principio de inmutabilidad del resto del sistema).

No es urgente: la ventana de 12 meses de la simulación ya evita que estos
precios contaminen la decisión del día a día.

---

## 6. UX / UI (todas para después de completar la funcionalidad)

### 6.1 Operaciones de edición (PUT/PATCH) y borrado
El sistema actual solo tiene crear (POST) y leer (GET). Falta poder editar y
borrar registros (clientes, catálogos, jornadas, etc.). Es lo que en una API REST
completa serían los métodos PUT/PATCH/DELETE.

**Estado: implementado** (generalizado a todos los catálogos y clientes).
Antes había 4 precedentes puntuales (habilitado de trabajador 6.5, jornadas
3.4, activos 7.2, categoría de tipo de bien 4.2); ahora las 9 entidades que
solo tenían POST/GET tienen el juego completo: **editar**, **habilitar/
deshabilitar** y **borrar**. Las entidades: Materia_Prima, Trabajador,
Producto_Terminado, Producto_Intermedio, Grupo_Movimiento, Gasto_Extra,
Cuenta (solo nombre), Cliente y Sector.

Tres reglas de negocio (ver la decisión ampliada en DECISIONES_DISENO.md):
- **Editar** los campos descriptivos es siempre seguro y no lleva guardrail:
  como las relaciones son por Id (no por texto), renombrar no corrompe el
  historial. Cambiar la tarifa de un trabajador solo afecta producciones
  futuras (Camino 1). El saldo de una Cuenta NO se edita a mano (se deriva de
  los movimientos): de Cuenta solo se edita el nombre.
- **Deshabilitar** (nuevo `Habilitado_*` en los 8 catálogos que no lo tenían,
  migración 008 — extiende el patrón de Trabajador de la 6.5) saca el item de
  los desplegables de operaciones nuevas sin borrarlo; su historial queda
  intacto. Es la vía recomendada para dar de baja algo que ya se usó.
- **Borrar** es real y SOLO si el item no tiene historial (`en_uso == false`,
  que cada GET ahora calcula); si lo tiene, se bloquea (400) y se sugiere
  deshabilitar. Respeta la inmutabilidad del histórico.

Implementación: endpoints `PATCH /{recurso}/{id}` (editar),
`PATCH /{recurso}/{id}/habilitado` (toggle) y `DELETE /{recurso}/{id}` en
`rutas/catalogos.py` y `rutas/clientes.py`, con helpers compartidos
(`_ids_referenciados`, `_toggle_habilitado`, `_borrar`). En el frontend, el
componente genérico `Catalogo` (movido a `componentes/`) trae edición
in-line + toggle + borrado guardado, reutilizado por los 6 catálogos, Cuenta
y Sectores; la página de Clientes pasó de lista a tabla con las mismas
acciones. Los desplegables de operaciones (Compras, Gastos, Pagos, Ventas,
Producción) filtran por `habilitado` (excepto el de trabajadores en Pagos,
que a propósito muestra todos — regla de 6.5). Verificado con curl (ciclo
completo crear/editar/deshabilitar/borrar y los guardrails de borrado con
historial) y build de frontend.

### 6.2 Buscadores en desplegables largos
Cuando haya muchas materias primas / productos / clientes, los desplegables
necesitan un campo de búsqueda para filtrar escribiendo, en vez de scrollear.

**Estado: implementado.** Componente reutilizable `SelectorBuscable`, aplicado
en 17 desplegables de catálogos/lotes/clientes en 8 páginas. Los `<select>` de
categorías fijas de negocio (tipo/sentido/origen en Mermas) se dejaron nativos
a propósito, no son catálogos que crecen.

### 6.3 Filtros dinámicos en tablas
Tablas largas (catálogos, jornadas) necesitan filtros. Ejemplos concretos:
- Jornadas: filtrar por "No pagadas" por defecto, para ver las activas de la semana.
- Catálogos: buscar/filtrar productos.
- Ocultar/colapsar tablas que no se están usando.

**Estado: implementado** para los dos primeros puntos (Jornadas: checkbox
"solo no pagadas" marcado por defecto; Catálogos: buscador de texto por
tabla). El tercer punto se resolvió con 6.4. El mismo patrón de buscador +
orden alfabético se generalizó en el componente `TablaFiltrable`, reutilizado
también en el detalle de Balance (ver 4.5).

**Ampliación (jul 2026) — los tres consolidados de stock + Deudas.** Con los
datos reales migrados, las tablas "stock general por producto (consolidado)"
de Compras (materia prima), Producción Intermedia y Producción Terminada
quedaron largas: no había forma de responder "¿cuánto tengo de X?" sin
scrollear. Lo mismo en **Deudas**, donde además la mayoría de las filas ya
están saldadas y ahogaban a las pocas con saldo vivo.

Las cuatro pasaron a `TablaFiltrable` (buscador + orden alfabético + plegable
con contador), que ya existía y ya se usaba en Balance — no hizo falta
componente nuevo. Se pasan con `abiertoInicial={true}` para conservar el
comportamiento previo (estaban siempre visibles). De paso, dos columnas que
el endpoint ya devolvía y la pantalla no mostraba: `costo_promedio` en el
consolidado de materia prima (existía desde 1.3) y `paquetes_equivalentes`
en el de producto terminado (existía desde 4.7).

`TablaFiltrable` ganó un prop opcional **`estiloFila(fila) => estilo`**: la
tabla de Deudas atenúa las de saldo 0, y migrarla sin eso habría borrado esa
señal (justo la que separa las deudas vivas de las saldadas). Los demás
llamadores lo omiten y no cambian.

**Deudas también se reordenó:** los tres formularios (deuda simple, préstamo,
pago) estaban **debajo** de la tabla, al revés que todas las demás pantallas.
Ahora van arriba y la tabla queda al final — primero se registra, después se
consulta el resultado. El mensaje de feedback se movió con ellos, junto a los
botones que lo disparan.

### 6.4 Secciones colapsables en Catálogos
La página de catálogos tiene 6 tablas apiladas; scrollear hasta la última es
molesto. Hacer secciones plegables o sub-pantallas con mini-menú.

**Estado: implementado.** Cada tabla es una sección plegable (título
clickeable con indicador ▾/▸ y contador de registros). Materia Prima abierta
por defecto, el resto colapsadas. El mismo patrón se reutilizó en el detalle
de Balance (4.5), ahí las tres tablas arrancan colapsadas.

### 6.5 Campo "habilitado" en trabajadores
Agregar a la BD si un trabajador está activo, para mostrar solo los habilitados en
los desplegables. Mini-migración simple.

**Estado: implementado.** Migración 004 (`Habilitado_Trabajador boolean DEFAULT
TRUE`, existentes quedan habilitados sin tocarlos). Nuevo endpoint
`PATCH /trabajadores/{id}/habilitado` — primer PATCH de la API, ver nota en
DECISIONES_DISENO.md. En Catálogos, la tabla de Trabajador tiene un botón por
fila para alternar el estado. El desplegable de **Jornadas** solo muestra
habilitados; el de **Pagos** a propósito muestra todos (si deshabilitas a
alguien con jornadas pendientes, necesitas poder pagarle igual para cerrar la
cuenta).

### 6.6 Alerta de venta bajo costo
En la pantalla de ventas, avisar visualmente (rojo / mensaje) si el precio de
venta que se pone es menor al costo del lote, para no vender a pérdida.

**Estado: implementado.** Aviso visual no bloqueante: mientras se arma la
línea, y también en cada línea ya agregada que quede bajo costo. El registro
de la venta nunca se bloquea.

### 6.7 Autocompletado y ayudas de formulario
Ya se implementó autocompletar el precio recomendado en ventas y el sugerido en
pagos. Extender este tipo de ayudas donde aplique.

**Estado: implementado (jul 2026).** Se buscaron los formularios donde el
dato a cargar es predecible desde el historial, y salieron tres:

- **Compras** → cantidad y precio de la **última compra de esa materia**.
  Ya existía un autocompletado con `/ultima-compra/{materia}/{proveedor}`,
  pero exigía **ambos**, y como las 2454 compras migradas del excel tienen
  `Id_Proveedor` en NULL, no disparaba nunca para esas materias. Ahora se
  dispara con la materia sola (nuevo `GET /ultimo-precio-materia/{id}`) y se
  afina al par materia+proveedor si hay proveedor elegido.
- **Jornadas** → horas de la **última jornada de ese trabajador**. La mayoría
  trabaja la misma cantidad de horas casi todos los días. Se resuelve en el
  frontend con las jornadas ya cargadas, sin pedirle nada al backend.
- **Cierre de mes** → monto **realmente pagado el mes anterior**, en vez del
  estimado fijo del catálogo (que era lo que sugería antes). La factura de
  luz del mes pasado predice mucho mejor la de este mes que un número cargado
  una vez al crear el gasto y nunca actualizado. Si no hay mes anterior, cae
  al estimado del catálogo.

Los tres muestran **de dónde salió** la sugerencia ("sugerido según la última
compra (fecha) — editable"): un número que aparece solo, sin decir por qué, se
registra sin mirar. Ninguno bloquea la edición.

Verificado en las tres pantallas en vivo contra datos reales.

### 6.8 Menú de navegación mejorado
El menú superior ya está largo (12+ pestañas). Agrupar por categorías (Catálogos,
Operaciones, Finanzas, Cierre) con submenús o secciones.

**Estado: implementado.** Componente `MenuCategoria`: 5 categorías
(Configurar, Producción, Ventas, Finanzas, Cierre) que despliegan sus páginas
al pasar el mouse (clic como respaldo para teclado/táctil). Se resalta la
categoría y el link activos.

### 6.9 Mejora general de estilos (CSS)
El MVP usa estilos por defecto (tablas con border=1, modo oscuro de Vite). Diseñar
una identidad visual propia: colores, tipografía, espaciado, tablas con mejor
formato.

### 6.10 Fecha única de registro (global) — del Excel
Campo de fecha junto al título de la app: si tiene valor, todos los
registros que se hagan usan esa fecha; si está vacío, hoy (comportamiento
actual). Caso real: una semana sin poder pasar datos, se anota en papel y el
fin de semana se registra todo cronológicamente con su fecha verdadera —
hoy habría que cambiar la fecha formulario por formulario. Implementación:
estado global en el frontend (contexto de React) que los formularios leen
como valor por defecto; el backend ya acepta fecha explícita en todo
(`fecha or date.today()`), no necesita cambios.

**Estado: implementado.** `componentes/FechaGlobal.jsx` (contexto +
`useFechaGlobal()`) con un input de fecha junto al título "Fábrica V2"
(vacío = hoy, como siempre). Las 11 pantallas que crean registros con fecha
(Compras, Jornadas, Producción Intermedia/Terminada, Ventas, Pagos, Gastos,
Transferencias, Deudas, Mermas, Absorción) mandan `fecha: fechaParaEnviar`
en su POST. Verificado con curl: una fecha explícita (`2020-01-15`) se
guardó exacta en `Movimiento.Fecha_Movimiento`, confirmando el mecanismo que
usan las 11 pantallas.

### 6.11 Indicadores en vivo al armar una producción — del Excel
En producción intermedia y terminada, junto al botón de confirmar, dos
etiquetas que se recalculan al agregar/quitar insumos: costo unitario
parcial (por litro o botella) y horas hombre invertidas hasta el momento.
Para tener esos números frescos día a día sin esperar al cierre.

**Estado: implementado.** En ambas pantallas de producción, un indicador
recalculado en cada render a partir de las listas de insumos ya agregadas
(sin tocar backend): costo unitario parcial = (MP + intermedios + trabajo)
÷ cantidad a producir, y horas hombre = suma de horas de los insumos de
trabajo agregados. **Limitación reconocida:** las horas mostradas son solo
las **directas** de esta producción, no las heredadas de los intermedios
que consume (eso depende de 1.1, no construido aún) — cuando 1.1 exista,
este indicador se puede enriquecer sumando las horas heredadas del
intermedio consumido.

### 6.12 Venta mejorada (tabla, precio sugerido, taxi/delivery, ganancia) — del Excel
Mejoras de la hoja de ventas del Excel sobre la pantalla actual:
- Las líneas agregadas como **tabla** (no lista), con columnas: costo
  unitario del lote, precio recomendado, ganancia por línea y % de ganancia.
- **Precio sugerido con margen mínimo:** margen configurable (35% en el
  Excel, celda global → candidato a `app/config.py`); sugerir el **mayor**
  entre el precio recomendado del catálogo y costo × (1/(1−margen)),
  redondeado a 2 decimales por botella.
- **Taxi/delivery:** campo con el costo del transporte de la venta,
  prorrateado entre todas las botellas, para ver el ingreso neto real por
  línea (permite "jugar": hasta dónde descontar, quién paga el taxi, qué
  combinación de productos conviene pushear).
- Totales de la venta: ganancia neta y % de ganancia ponderado.
- Lotes automáticos por FIFO (3.1) en vez de elegir lote por lote.

**Decisión de alcance (jul 2026) — antes de implementar:**
- **Líneas como tabla** con columnas: costo unitario del lote, precio
  recomendado, ganancia por línea y % de ganancia por línea.
- **Precio sugerido:** `mayor(precio recomendado del catálogo, costo ×
  1/(1−margen))`. El `margen` es configurable en `app/config.py`
  (`MARGEN_VENTA_MINIMO`, 0.35 por defecto). Resultado redondeado a 2
  decimales por botella.
- **Taxi/delivery = SOLO cálculo en pantalla.** Prorratea el costo del
  transporte entre todas las botellas de la venta para ver el neto real por
  línea/producto ("qué me costó vender esto"). **NO mueve caja, NO crea un
  `Movimiento`.** Si el taxi se pagó de verdad, se registra aparte como un
  Gasto normal. Motivo: el taxi es un dato de análisis para decidir precios y
  descuentos, no un hecho contable atado a la venta.
- **FIFO automático:** reutilizar el `SelectorFifo` ya existente
  (`frontend/src/componentes/SelectorFifo.jsx`) para resolver los lotes por
  producto, en vez de elegir lote por lote.

**Estado: implementado.** Backend: el endpoint `/lotes-producto-terminado`
entrega por lote `costo_unitario` y `precio_recomendado`; el precio sugerido se
calcula en el frontend. El servicio `ventas.py` y la tabla `Venta` **no
cambiaron** (el taxi es solo pantalla). Frontend (`PaginaVentas.jsx`):
- **Caja de margen editable** (default 35%) arriba de la pantalla: manda sobre
  el precio sugerido (`max(recomendado, costo/(1−margen))`, 2 decimales) que se
  usa al autocompletar una línea y al resolver por FIFO. Se puso en el frontend
  (no en `config.py`) porque cambia seguido y no debería requerir tocar código.
- **Líneas como tabla** con costo unitario, precio, ganancia por línea y %; el
  **precio de cada línea es editable en la tabla** (sin quitar y re-agregar).
- **Taxi/delivery** que prorratea entre todas las botellas y agrega las
  columnas *Taxi* y *Neto* más el taxi por botella; totales con ganancia (neta
  si hay taxi) y % ponderado. El "% de ganancia" = `ganancia / ingreso`.
- **`SelectorFifo` conectado** (origen `TERMINADO`): agrega una línea por lote
  sugerido con la cuenta destino elegida, **descontando lo ya comprometido** en
  las líneas actuales (no re-mete lotes agotados ni pasa del stock).

Verificado con `curl` (endpoint) y `vite build` (compila).

### 6.13 Cargar cantidades en paquetes + botellas (Venta y Producción) — del Excel
Hoy toda cantidad de producto terminado se carga en botellas, pero en la
práctica se piensa y se vende en paquetes ("5 paquetes y 1 suelta"), y hacer
la multiplicación mental en cada línea es donde se cuelan los errores.

Alcance decidido (jul 2026), en **Venta** y en **Producción Terminada**: dos
campos editables (*cantidad paquetes* y *cantidad botellas*) más un tercero
**no editable** con la suma —
`total = paquetes × Botellas_Por_Paquete + botellas` — que es el único valor
que viaja al backend. En Venta aplica tanto a la línea manual como a la
resuelta por FIFO.

**Sin cambio de BD ni de servicios:** `Detalle_Venta` y `Produccion` ya
guardan botellas, y deben seguir guardando botellas (es la unidad en que
están todo el histórico, el costeo por lote, el stock y la absorción de 1.4).
Esto es exclusivamente una ayuda de carga en el frontend.

**Decisión (jul 2026): en productos sueltos** (`Botellas_Por_Paquete = 1`) **se
oculta el campo de paquetes** y no se muestra la sumatoria. Con paquete de 1
los dos campos significan lo mismo y la suma se vuelve engañosa (5 paquetes +
1 botella = 6 no se lee como nada útil). Mismo criterio que ya usa
`fmtBotellasYPaquetes` (ver 3.9).

**Cuidado al implementar (no es tan trivial como parece):** en Ventas ese
total ya alimenta el precio sugerido, la ganancia por línea, el prorrateo del
taxi y el descuento de stock comprometido del `SelectorFifo` (todo de 6.12).
El total tiene que ser un **valor derivado en render**, nunca estado propio
duplicado: si se desincroniza, los cálculos de ganancia se rompen en silencio,
sin error visible.

**Estado: implementado (jul 2026).** Componente
`componentes/CantidadPaquetes.jsx` + el helper puro `totalBotellas(paquetes,
botellas, bpp)` que exporta. Sin migración ni cambios de servicio, como estaba
previsto: lo único que se agregó al backend es `botellas_por_paquete` en
`GET /lotes-producto-terminado`, que la pantalla de Ventas necesitaba para
saber el tamaño de paquete de cada lote.

- **Dónde:** la línea manual de **Ventas**, el **`SelectorFifo`** (prop nuevo
  y opcional `obtenerBotellasPorPaquete`; MP e intermedio lo omiten y siguen
  con un solo campo) y la cantidad a producir de **Producción Terminada**.
- **El total nunca es estado.** Se deriva con `totalBotellas()` en cada
  render, y es lo único que viaja al backend. En Producción Terminada además
  reemplaza a `parseFloat(cantidad)` en el indicador de costo unitario parcial
  (6.11), que si no habría seguido dividiendo por las botellas sueltas e
  informado un costo por botella inflado.
- **Cambiar de producto limpia la cantidad**, en las tres puntas. Un valor en
  paquetes pertenece al tamaño de paquete del producto anterior: arrastrarlo a
  otro producto daría un total distinto del que se tecleó, sin aviso.
- **Productos sueltos** (`bpp = 1`): un solo campo, sin sumatoria (decisión de
  arriba). `totalBotellas` además **ignora** un valor de paquetes cuando el
  producto es suelto — el campo está oculto, así que el usuario no podría ni
  verlo ni corregirlo, y no debe sumar en silencio.
- En la tabla de líneas de la venta, la cantidad muestra el equivalente en
  paquetes al lado de las botellas, para revisar la venta en la unidad en que
  se piensa.

Verificado: `totalBotellas` extraído del archivo real y probado en 8 casos
(incluido el del pedido — 5 paquetes + 1 botella con paquete de 6 = 31 —, los
sueltos con paquetes colgados, vacíos y fracciones) y `vite build`.

### 6.15 Que un error no deje la app entera en blanco
**Estado: implementado (jul 2026).** Salió de un bug real: un `ReferenceError`
en la pantalla de Ventas (ver 6.13) no dejaba solo esa pantalla rota — React,
sin ningún error boundary, desmontaba **todo** el árbol, así que se perdía
hasta el menú y no había forma de navegar a otro lado. La app quedaba muda,
sin decir qué pasó.

Al revisarlo aparecieron **tres** causas distintas de pantalla en blanco, que
es fácil confundir entre sí:

1. **Error de render** → nuevo `componentes/LimiteError.jsx`, el único
   componente de clase del proyecto (React no expone los hooks de error
   boundary a los componentes de función). Muestra un cartel en el lugar de la
   pantalla rota, aclara que el resto de la app sigue viva y que los datos no
   se perdieron, e incluye el detalle técnico para poder reportarlo. Recibe
   `clave={location.pathname}`: al navegar a otra pantalla se resetea, así una
   rota no deja el cartel pegado sobre las demás.
2. **Ruta `/` inexistente** → entrar a la raíz no matcheaba nada y dejaba el
   contenido vacío (se veía en consola: `No routes matched location "/"`).
   Ahora redirige a `/balance`, que es la vista de conjunto.
3. **Sin catch-all** → una URL mal tecleada o un link viejo caían en blanco
   igual. Ahora hay una ruta `*` que lo dice y remite al menú.

Las rutas se movieron a un componente `Contenido()` dentro del `BrowserRouter`,
porque el boundary necesita `useLocation` y ese hook solo existe adentro del
Router.

**Nota de verificación (importante):** `vite build` compiló sin quejarse con
el bug que originó todo esto adentro. Esbuild no analiza zonas muertas
temporales, así que **compilar no prueba que una pantalla monte** — hay que
abrirla. Ver la nota en DECISIONES_DISENO.md.

### 6.14 Unidad de producto intermedio (etiqueta)
`Producto_Intermedio` no dice en qué unidad está medido: se ve un "30" en las
tablas sin saber si son litros, unidades o botellas. Falta una columna
`Unidad_Producto_Intermedio` (LITRO / UNIDAD / KG), editable en el catálogo y
mostrada al lado del número en tablas y desplegables.

**Decisión de alcance (jul 2026): es SOLO una etiqueta, sin conversión.** El
sistema nunca convierte unidades de intermedios — se produce X y se consume X
en la misma unidad, siempre, y el costo por unidad se deriva de ahí. Agregar
conversión (cargar en una unidad distinta a la de producción) tocaría el
costeo y el stock por lote, y es un trabajo de otra magnitud; se descartó por
ahora. El campo existente `Litros_Botella_Final` es otra cosa (dato de la
botella final) y no cumple esta función.

**Estado: implementado (jul 2026).** Migración 023: columna
`Unidad_Producto_Intermedio` con `CHECK IN ('LITRO','UNIDAD','KG')` y default
**LITRO**, más la lista `UNIDADES_PRODUCTO_INTERMEDIO` en `app/config.py`
(mismo patrón que `CATEGORIAS_TIPO_BIEN` de 4.2; ampliarla exige ampliar
también el CHECK).

**Sin backfill inteligente, a propósito.** A diferencia de la migración 006
—que reprodujo un criterio por texto que el código ya venía usando— acá no hay
ningún criterio previo que replicar: adivinar la unidad por el nombre del
producto clasificaría mal en silencio. Todos quedan en LITRO (la unidad de la
mayoría, que son líquidos) y los que no lo sean se corrigen desde el catálogo.

La unidad se elige con un *select* en el catálogo de Producto Intermedio
(reutilizando el tipo `select` que el componente `Catalogo` ya soportaba desde
2A) y se muestra al lado del número en: el consolidado de stock intermedio, la
tabla de lotes de producción intermedia, y los dos desplegables de lote de
intermedio (Producción Intermedia y Terminada). El backend la expone en
`/productos-intermedios`, `/stock-intermedio-general` y
`/producciones-intermedias`.

Verificado contra la BD real: migración aplicada (los intermedios existentes
quedaron en LITRO), ciclo completo crear→editar→borrar de un intermedio
`__TEST` con unidad, y el rechazo de una unidad fuera de la lista con su
mensaje de error. Datos de prueba limpiados.

---

## 7. MÓDULOS CON BACKEND PERO SIN PANTALLA (o parciales)

### 7.0 Deudas y amortización
El sistema tiene tablas de Deuda y Movimiento_Deuda en el diseño, pero no hay
pantalla para gestionarlas. Falta: registrar deudas, amortizarlas (con la lógica
de reparto por prioridad de cuentas, ver sección 2), y verlas reflejadas en el
balance. Es parte del flujo financiero completo.

**Estado: implementado** (con 7.3). Servicio `deudas.py` con tres
operaciones atómicas y pantalla **Deudas** (grupo *Finanzas*):
- **Deuda simple sin ingreso:** sube el pasivo sin mover caja (interés del
  banco, o un gasto que un tercero pagó por nosotros).
- **Préstamo con ingreso:** sube la deuda **y** entra dinero a una cuenta en
  un solo acto. El lado de caja usa un `Movimiento` tipo `INGRESO_EXTERNO`
  (ya excluido de las ventas de la semana), no `ENTRADA`, para no contarlo
  como venta.
- El saldo de la `Deuda` se mantiene como el de una `Cuenta` (campo cacheado
  + un `Movimiento_Deuda` AUMENTO/PAGO por cada operación). El balance ya
  resta `Total_Deudas`, así que se refleja solo: una deuda simple baja el
  patrimonio, un préstamo lo deja igual (activo + pasivo se cancelan) —
  verificado con curl contra `/balance-actual`.

Verificado: deuda simple, préstamo, pago, los guardrails (pago > saldo de
deuda, saldo de cuenta insuficiente) y la deduplicación por descripción.
Datos de prueba limpiados.

~~**Pendiente:** la deuda a proveedor nacida de una compra a crédito parcial se
conecta cuando se implemente ese caso.~~ **Ya resuelto** por la ampliación de
5.1 (jul 2026): la compra a crédito parcial crea la deuda agrupada por
proveedor (`deuda_de_proveedor` con `Id_Proveedor`) y se paga desde esta misma
pantalla. Esta nota quedó desactualizada.

### 7.1 Códigos QR para etiquetas físicas
Generar códigos QR (en el backend, no se guardan en BD) para etiquetar físicamente
los sacos/lotes de materia prima y productos. Escaneas el QR de un saco y el
sistema te dice qué es y de qué lote. Útil para trazabilidad física en la fábrica.


### 7.2 Activos fijos (patrimonio)
Registrar activos como casa, vehículo, equipos, para que sumen al patrimonio en
el balance (escenario A). La tabla Activo y Tipo_Bien existen en el diseño. Falta
backend (crear activo con su tipo y valor) y pantalla. El balance ya tiene el
espacio para sumarlos (total_activos_fijos).

**Estado: implementado.** CRUD completo de activos y tipos de bien
(`rutas/activos.py`), página nueva **Activos** bajo Cierre (crear/editar/dar
de baja). De paso se corrigió un bug real: la vista previa (`/balance-actual`)
tenía `escenario_a = escenario_b` fijo, ignorando los activos por completo,
mientras la foto guardada sí los sumaba — inconsistentes entre sí. Ahora
ambas calculan igual: A = B + activos fijos. El Escenario A suma **todos**
los activos sin importar el tipo (sin depender del match de texto frágil que
usa la foto guardada para inmuebles/equipos/otros — eso sigue igual, ver
4.2). Balance ganó una fila "Activos fijos" y una tabla-resumen plegable con
el detalle. De paso se agregó `formato.js` (separador de miles, locale
es-BO) aplicado en Balance y Activos.

### 7.3 Pago/amortización de deudas
Complementa el módulo de deudas (7.0): pagar una deuda eligiendo de qué cuenta
sale el dinero, bajando el saldo de la deuda y descontando la cuenta. Usa la
lógica de reparto por prioridad (sección 2). El balance ya resta las deudas.

**Estado: implementado (base).** `pagar_deuda` en `deudas.py` +
`POST /deudas/pago`: baja el saldo de la deuda y descuenta de **una** cuenta
elegida. El lado de caja usa un `Movimiento` tipo `PAGO_DEUDA` (migración
012 amplía el CHECK), a propósito distinto de `SALIDA` para que el balance
no lo cuente como gasto de la semana (mismo principio de categorizar-sin-
adivinar de 4.1). Pagar una deuda no cambia el patrimonio (baja efectivo y
pasivo por igual) — verificado.

**Pendiente:** el reparto por prioridad de cuentas (sección 2) — hoy se paga
desde una sola cuenta a mano. Cuando exista esa capa, `pagar_deuda` será una
de las operaciones base que orqueste.

### 7.4 Columnas de balance para fotos históricas
Ya se agregaron Valor_Stock_Intermedio y Valor_Horas_Standby al balance (migración
003). Si se agregan más conceptos al balance en el futuro, recordar: agregarlos
como columnas para que las fotos históricas los guarden y la comparación temporal
sea completa.

### 7.5 Transferencias entre cuentas e ingresos externos — del Excel
Hoy no existe forma de mover dinero entre cuentas/billeteras ni de registrar
un ingreso que no sea una venta (ej. "ingresan 500 Bs externos a Billetera
Fábrica", con descripción de dónde viene). En el Excel había una hoja de
transacciones que hacía ambas cosas. La tabla `Movimiento` ya está
preparada: tiene `Id_Cuenta_Origen` e `Id_Cuenta_Destino` — una
transferencia llena ambas (resta de una, suma a la otra), un ingreso externo
solo el destino. Con el reparto por prioridad (sección 2) las transferencias
manuales deberían volverse raras, pero el ingreso externo sigue siendo
necesario siempre.

**Estado: implementado.** (El doc se había quedado sin registrarlo; se
verificó contra el código en jul 2026.) Servicio
`servicios/transferencias.py`, rutas `POST /transferencias` y
`POST /ingresos-externos`, y la pantalla **Transferencias** (grupo
*Finanzas*). La transferencia llena origen y destino en un solo `Movimiento`;
el ingreso externo usa el tipo `INGRESO_EXTERNO` (migración 010), a propósito
distinto de `ENTRADA` para que el balance no lo cuente como venta de la
semana — mismo principio de categorizar-sin-adivinar de 4.1.

---

## 8. INTEGRACIONES Y DESPLIEGUE

### 8.1 Power BI conectado a PostgreSQL
Para reportería avanzada sin construir todo el frontend de reportes. Conectar
Power BI directamente a la base para dashboards.

**Ampliación (jul 2026) — qué dashboards van ahí (no en el frontend):**
- Pareto 80/20 de rentabilidad: qué 20% de los productos deja el 80% de la
  ganancia.
- Producto más vendido y producto con más margen, por período.
- Mejor cliente / mejor zona (ya hay sector y lat/long).
- Evolución mensual de patrimonio y escenarios (las fotos de Balance).
- Rentabilidad real por producto con el acumulado de la sección 2 ("¿este
  producto ya devolvió la inversión a la fábrica?"), cortado por mes.
- Análisis de precios por proveedor (cuando exista 5.1).

Criterio de reparto: el frontend web se queda con lo **operativo** del día a
día (registrar, validar, balance, resumen diario); el análisis exploratorio
e histórico va a Power BI (Desktop es gratis; conexión con usuario de solo
lectura a PostgreSQL).

**Estado: en progreso (jul 2026) — conexión lista + 9 dashboards
documentados.** Todo en `reportes-powerbi/README.md`. "Documentado" =
tablas + relaciones + medidas DAX + armado del visual + consulta SQL de
verificación; **armarlos en Power BI Desktop es manual** (es una app de
escritorio Windows), así que el README es la receta, no una prueba de que el
visual ya se montó.

- **Rol `powerbi_lectura`**: usuario de PostgreSQL con `SELECT` y nada más
  (mínimo privilegio: si el reporte falla, no puede tocar un dato).
  `ALTER DEFAULT PRIVILEGES` para que las tablas de migraciones futuras
  también le queden visibles sin repetir el `GRANT`. Verificado conectándose
  con ese usuario: lee bien, y el `UPDATE` de prueba falla con "permiso
  denegado". La contraseña **no** se versiona (mismo criterio que `.env`,
  porque el repo va a GitHub — 8.5).
- **`*.pbix` en `.gitignore`**: en modo Importar el archivo lleva una copia
  completa de los datos adentro; versionarlo sería meter ventas/clientes/
  deudas reales en un blob binario, para siempre en el historial. Se versiona
  el README (conexión + DAX + cómo armar cada visual): con eso se reconstruye.
  Alternativa futura si se quiere versionar el diseño: formato `.pbip`
  (carpeta de JSON, sin datos embebidos).
- **Dashboards documentados (9):**
  1. **Pareto 80/20 de rentabilidad** (margen bruto/neto con selector).
  2. **Producto más vendido / con más margen por período** (+ comparación
     año contra año).
  3. **Mejor cliente / mejor zona** (+ mapa por lat/long).
  4. **Evolución de patrimonio y escenarios** (fotos de `Balance`).
  5. **Ingreso externo mes a mes, año contra año.**
  6. **Rentabilidad acumulada por producto** (recuperación de inversión, el
     `saldo` de 2.C — distinto del Pareto; verificado contra la BD real).
  7. **Evolución de precio por materia prima + detección de outliers** (cara
     visual de 5.2; `ALCOHOL CAIMAN` va de 1,00 a 17,33 en el histórico).
  8. **Mano de obra por trabajador y mes** (horas, costo derivado de la tarifa
     de 10.1, y botellas/hora a nivel fábrica).
  9. **Deudas: saldo vivo + pagos en el tiempo** (no es aging clásico: `Deuda`
     no tiene vencimiento y `Movimiento_Deuda` sólo guarda `PAGO`, así que el
     saldo histórico no se reconstruye — sí la foto de hoy y los pagos).
- **Pendiente (1):** análisis de precios **por proveedor** — bloqueado por
  datos, no por código: 5.1 ya creó las tablas pero `Proveedor` está vacía y
  las compras migradas tienen `Id_Proveedor` en NULL.

**Definición de "ganancia" (importante, se decidió acá):** el Pareto NO usa el
`saldo` de la mejora 2.C. Son métricas distintas y está bien que no coincidan:
el saldo resta el costo de **todo lo producido** (incluido el stock sin vender)
y responde "¿ya recuperó la inversión?"; el Pareto resta el costo de **solo lo
vendido** y responde "¿cuánto gané con lo que vendí?". Este documento ya las
listaba como dos dashboards separados. El costo de lo vendido es exacto (no un
promedio) porque cada línea de venta apunta a su lote de producción — la
trazabilidad que conservó la migración (8.4).

Se implementaron las dos variantes con un selector: **margen bruto** (ingresos −
costo de lo vendido) y **margen neto** (− gastos extra prorrateados). Los gastos
extra NO están dentro del costo del lote (`ejecutar_prorrateo` solo escribe en
`Prorrateo_Mensual`, nunca toca `Precio_Unitario_Producto_Terminado`), así que
restarlos no es doble conteo; la absorción de utensilios (1.4) **sí** está
dentro, y por eso no se resta aparte. Con los datos actuales el reparto sale
cercano a un 80/20 clásico. Cambiar de métrica mueve el ranking (un producto de
mucho volumen consume muchas horas de fábrica, así que carga más gastos extra y
puede caer varios puestos en el neto) — no es cosmético.

Limitación anotada: el prorrateo asigna por horas **producidas**, así que el
margen neto carga gastos de botellas aún no vendidas. Pesa poco en el histórico
(~7%), puede distorsionar al cortar por mes.

### 8.2 Google Maps API
Para los sectores/zonas de clientes: mostrar clientes en un mapa, análisis de
ventas por zona. Ya se guardan latitud/longitud (con extracción desde link de Maps).

**Ampliación (jul 2026) — ruteo de venta:** elegir los sectores a visitar y
trazar la ruta entre los clientes de esa zona (vecino más cercano iterado, o
el optimizador de la API de rutas de Google, que ya considera tráfico,
sentidos de vía y calles cerradas — antes se aproximaba con Pitágoras sin
API). Para el final, después de lo funcional.

### 8.3 Respaldos automáticos (pg_dump)
Los datos viven en PostgreSQL, NO en Git. Git no los protege. Configurar respaldos
periódicos con `pg_dump` antes de manejar datos reales del negocio, para no
perderlos ante una falla de disco.

**Estado: implementado (versión manual).** Scripts en `backend/scripts/`:
- `backup_db.ps1`: corre `pg_dump -F c` (formato custom, comprimido) contra
  la BD definida en `backend/.env`, y guarda el archivo con fecha/hora en el
  nombre (`fabrica_V2_AAAAMMDD_HHMMSS.dump`) en **D:\Backups_BD_Fabrica**
  (disco físico distinto al E: donde vive el repo, para que una falla de
  disco no se lleve el repo y los respaldos juntos). No es parte de Git —
  vive fuera del repo por completo.
- `restore_db.ps1 -Archivo <ruta>`: restaura un respaldo puntual con
  `pg_restore --clean --if-exists` (equivalente a "volver a ese punto"),
  pidiendo confirmación explícita antes de tocar la base porque es
  destructivo (reemplaza el contenido actual).
- `respaldar.bat` / `restaurar.bat`: envoltorios doble-cliqueables de los
  dos scripts de arriba. Windows no deja correr un `.ps1` con doble clic por
  defecto (aunque la política de ejecución lo permita) — el `.bat` llama a
  PowerShell con `-ExecutionPolicy Bypass` solo para esa ejecución puntual,
  sin cambiar ninguna configuración del sistema.
- `reset_db.ps1` / `vaciar_prueba.bat`: vacía TODAS las tablas (TRUNCATE
  ... CASCADE + reinicio de ids), pidiendo confirmación escrita del nombre
  de la base antes de tocar nada. Se agregó para poder probar el ciclo
  completo respaldo → vaciar → restaurar mientras la BD solo tiene datos
  de prueba (jul 2026, ningún dato real todavía). **No es el script de
  limpieza final de 8.4** — ese deberá decidir qué catálogos conservar o
  recrear desde el Excel; este vacía sin distinción, por eso solo es seguro
  usarlo ahora, antes de que exista un dato real mezclado con los de
  prueba.

Por qué no es incremental como Git: `pg_dump` no versiona diffs, cada corrida
es una foto completa e independiente. Para tener "puntos de restauración"
hay que correrlo varias veces y quedarse con varios archivos fechados — cada
uno se restaura de forma independiente, no se combinan entre sí.

Decisiones tomadas (jul 2026): destino D:\ (disco separado, ~1TB libres);
por ahora se conservan **todos** los respaldos sin borrado automático — un
respaldo de prueba pesó 0.11 MB, así que el espacio no es un problema
mientras el proyecto sea chico; revisar la política de retención (ej.
quedarse con los últimos N) cuando el tamaño real lo justifique. Ejecución
**manual** por ahora (no se configuró Windows Task Scheduler): se decidirá
si conviene automatizarlo y con qué frecuencia (diario/semanal) una vez que
se sepa cuánto pesan los respaldos con datos reales de uso.

### 8.4 Migración de datos reales del Excel (incluye limpieza previa)
Antes de migrar: **borrar todos los datos de prueba** acumulados durante el
desarrollo y dejar la BD limpia (script de reset: TRUNCATE de las tablas de
datos con reinicio de secuencias/ids; decidir si los catálogos de prueba se
conservan o también se recrean desde el Excel). Con respaldo previo (8.3)
por si acaso.
Al final, cuando el sistema esté probado, migrar los 3 archivos de Excel con los
datos históricos reales, con pruebas de paridad contra el Excel.

**Estado: implementado (jul 2026).** Script: `backend/scripts/migrar_excel_v2.py`.
El excel consolidado (los 3 archivos unidos en una sola hoja con ~22 bloques
de tablas lado a lado) vive en `datos_reales/` (carpeta gitignoreada — el
script se versiona, los datos no). Secuencia ejecutada:

1. Tag git `pre-migracion-excel` + respaldo pg_dump + TRUNCATE total
   (mismo SQL de `reset_db.ps1`).
2. `migrar_excel_v2.py --dry-run`: corre TODO y hace ROLLBACK — sirvió para
   ver conteos y anomalías sin riesgo antes de la corrida real.
3. Corrida real: **una sola transacción** (si algo falla a mitad no queda
   nada a medias). Carga todos los catálogos (materias primas, trabajadores,
   intermedios, terminados, sectores, gastos extra, deudas, cuentas, ítems
   de absorción), y toda la historia: compras, jornadas, producciones
   intermedias y terminadas **con su detalle completo de insumos** (qué
   compra/jornada/PI alimentó cada lote — decenas de miles de filas de
   detalle), ventas (agrupadas por cliente+fecha), el prorrateo mensual
   completo y los movimientos de dinero (gastos familiares con grupo, pagos
   de deuda, transferencias, ingresos externos).
4. Verificación de paridad: totales producido/vendido/Bs por producto
   sumados desde la BD == sumas crudas del excel (la "TABLA PRODUCTOS
   HISTORICO" del excel estaba desactualizada — el control se hizo contra
   las tablas crudas); PU de lotes al azar idéntico dígito a dígito; cero
   detalles huérfanos. La app corriendo sirvió los datos sin tocar código.
5. Respaldo post-migración + tag `post-migracion-excel`.

Anomalías del excel manejadas por el script (quedan logueadas al correrlo):
7 fechas imposibles tipo `F31062022` (clampeadas al último día del mes),
2 códigos MP con hueco en el catálogo (la MP se crea desde la propia
compra), 1 deuda duplicada fusionada, 1 cliente que solo existía en ventas,
2 sectores que solo existían en clientes. Las decisiones de mapeo están en
DECISIONES_DISENO.md (sección 8).

**Correcciones posteriores (jul 2026), al revisar los datos ya cargados:**

1. **Bug del script: activos duplicados.** La tabla del excel se llama
   "TABLA ANTERIOR ESTE SE DIVIDE AHORA" y era el balance viejo todo junto;
   en V2 se reparte en tres lugares y solo uno es `Activo`. El filtro solo
   excluía `BILLETERA`, así que entraron como activos las dos filas
   `CAJA DE AHORROS` (los bancos, ya cargados como `Cuenta` → efectivo
   contado dos veces) y la fila `INVENTARIOS` (el stock, que el balance ya
   calcula desde compras/producciones → contado dos veces). Se corrigieron a
   mano en la BD y se arregló el filtro del script (`TIPOS_QUE_NO_SON_ACTIVO`)
   para que un re-run sea correcto.

2. **Lote de producto terminado en stock negativo** (migración 020 +
   bloque 5b del script). El excel no validaba stock: su macro descontaba
   ventas de un lote agotado. Un producto quedó con un lote en negativo y el
   siguiente inflado con botellas que físicamente no existían; la diferencia
   son las mismas botellas. Se reasignan las ventas de exceso,
   cronológicamente, al siguiente lote del mismo producto con stock.
   **Importa**: el balance ignora los restantes negativos (filtra
   `> UMBRAL_STOCK_MINIMO`) pero **sí valorizaba las botellas fantasma** que
   no existen — el fix bajó el stock terminado en ese monto. El total
   vendido no cambia: la venta es un hecho, lo que estaba mal era el lote al
   que se le atribuía.

3. **Negativos que se dejan como están** (5: 1 compra, 3 intermedios, 1
   jornada). El balance los ignora y, a diferencia del caso de producto
   terminado, no inflan ninguna otra fila. Se dejan porque son la evidencia
   de que la macro del excel sobre-consumió esos lotes; limpiarlos borraría
   el rastro sin cambiar ningún número.

4. **El "desface" contra el escenario B del excel no es un dato faltante:
   era doble conteo del excel.** Ver DECISIONES_DISENO.md 8.2.

5. **Jornadas migradas marcadas como pagadas** (migración 022). El excel no
   tenía tabla de pagos a trabajadores, pero en la realidad ya se habían
   pagado todas (semanal, cada sábado). Sin este fix, `Id_Pago_Trabajador`
   quedaba `NULL` en todas las jornadas migradas y el endpoint
   `/trabajadores/{id}/pago-sugerido` las sumaba todas: años de sueldo
   "sugeridos" de golpe para un solo trabajador antes del fix. Se creó un
   `Pago_Trabajador` por (trabajador, semana), agrupando por el sábado que
   cierra cada semana, con monto = horas × tarifa pactada. **Sin
   `Id_Movimiento`** — mismo criterio que compras/ventas: esa plata salió de
   la caja hace años y el saldo actual (último snapshot del excel) ya está
   descontado; crear un movimiento nuevo la restaría dos veces. Verificado:
   cruce horas×tarifa crudo vs total agrupado exacto por trabajador, cero
   jornadas sin vincular, cero movimientos de caja creados.

### 8.5 Subir el repositorio a GitHub
Actualmente el versionado es local. Subir a GitHub cuando haya una beta, con el
README y la documentación, para que el repositorio sea visible (útil para CV).

### 8.6 Empaquetar con Docker para que otra persona lo pruebe
Idea surgida al trabajar en 8.3 (jul 2026): hoy el proyecto solo corre en esta
PC (Python + Node + PostgreSQL instalados a mano). Un `docker-compose.yml`
que arma 3 contenedores (PostgreSQL + backend FastAPI + frontend ya
compilado) permite que otra persona lo pruebe con un solo comando
(`docker compose up`), sin instalar Python/Node/PostgreSQL por separado.

Decisión (jul 2026): de las dos opciones evaluadas (Docker vs. hosting
temporal tipo Render/Railway con datos ficticios), se elige **Docker** —
sirve además para aprender la tecnología y suma al CV, y no depende de que
la otra persona tenga que entrar a un link (evita el costo/límites del free
tier de hosting). El camino de hosting temporal para demo queda descartado
por ahora, no como pendiente.

Para el final (etapa E), después de que el sistema esté probado en el uso
diario real.

**Estado: escrito y parcialmente verificado (jul 2026). Falta correrlo.**

Archivos: `docker-compose.yml` (demo), `docker-compose.real.yml` (override),
`docker/` (Dockerfiles de backend y frontend, `nginx.conf`, `init/00_init.sh`,
`seed_demo.sql`, `README.md`) y `.dockerignore`.

**Dos variantes, decisión de negocio (jul 2026):**
- **Demo con datos ficticios** — para mostrar el sistema (CV, terceros). Todo
  el contenido de `seed_demo.sql` es inventado; no hay un solo dato del
  negocio, porque el repo es público (regla de DECISIONES_DISENO.md §8).
- **Real desde un respaldo** — para que alguien evalúe el sistema con la
  información verdadera. El `.dump` se **monta al ejecutar** desde una carpeta
  de la máquina; nunca se copia a la imagen ni al repositorio (`*.dump` está
  en `.gitignore` y en `.dockerignore`). Si se comparte la imagen construida,
  los datos no viajan adentro.

**Power BI no puede ir en un contenedor**: es una app de escritorio Windows,
sin versión Linux. Lo que sí se resolvió es dejar la base accesible desde
afuera (puerto 5433) y crear el rol `powerbi_lectura` en el arranque, para
que Power BI Desktop del anfitrión se conecte igual que hoy se conecta a la
base local.

**Huecos que aparecieron al empaquetar (y se taparon):**
- **No existía `requirements.txt`.** El backend no declaraba sus dependencias
  en ningún lado: nadie —ni el propio autor en otra PC— podía reproducir el
  entorno. Se generó desde los imports reales, con las versiones instaladas y
  fijadas con `==`.
- **No existía `.env.example`**, así que no había forma de saber qué
  variables hacen falta sin abrir el `.env` real.
- **CORS y la URL del backend estaban fijas en el código.** Ahora salen de
  `CORS_ORIGINS` (backend) y `VITE_API_URL` (frontend, resuelta al compilar).
  Los valores por defecto son los de siempre: **el entorno local no cambió**.
- **Choque de puertos:** el compose publica el backend en **8001** y la base
  en **5433**, no en 8000/5432, porque el entorno de desarrollo ya los ocupa
  y los contenedores no arrancarían con el entorno local prendido.

**Qué está verificado y qué no.** Docker no está instalado en la máquina de
desarrollo, así que **`docker compose up` nunca se ejecutó**. Sí se verificó,
contra PostgreSQL real y sobre una base descartable (creada y borrada):
- El esquema base + las **24 migraciones** aplican limpio sobre una base
  vacía. Es un camino que nunca se había probado: la base real creció
  migración por migración, no de cero.
- El esquema resultante es **idéntico** al de producción: 226 columnas contra
  226, cero diferencias en ambos sentidos.
- El `seed_demo.sql` carga sin errores sobre ese esquema.
- **La API real responde bien contra esa base** (se levantó uvicorn en el
  puerto 8001 apuntando a la base de prueba y se consultaron 9 endpoints).
  Los números del seed son coherentes: 120 botellas producidas − 24 vendidas
  = 96 en stock, 16 paquetes equivalentes, y el balance calcula.
- Los `docker-compose.yml` son YAML válido, el `00_init.sh` pasa `bash -n`, y
  los tres puertos cuadran entre sí (el frontend llama al puerto que el
  backend publica, y ese origen está en la lista de CORS).

Queda sin probar el plumbing de Docker: construcción de las imágenes, red
entre contenedores y orden de arranque. Al instalar Docker, el primer
`docker compose up --build` es la prueba pendiente.

### 8.7 Self-hosting real (mediano plazo, con túnel)
Distinto de 8.6: esto es para uso productivo real, no solo demo. Unas 3
personas necesitarán conectarse, casi siempre en el horario de trabajo (la
PC ya estaría encendida por otras razones en ese horario), así que no hace
falta un hosting pago — la propia PC alcanza como servidor:

- El stack es liviano (FastAPI + PostgreSQL + React compilado); con el
  volumen de datos actual (~0.1 MB la base completa) y 3 usuarios
  concurrentes, no hace falta hardware potente, solo que la PC esté
  encendida y estable durante el horario de uso.
- Para que las 3 personas se conecten desde afuera sin abrir puertos en el
  router (evita exponer la PC directamente a internet, que es el riesgo
  real): usar un túnel tipo **Cloudflare Tunnel** (gratis, da HTTPS,
  la PC se conecta hacia afuera en vez de aceptar conexiones entrantes).
  Nunca exponer el puerto de PostgreSQL directamente, solo el del backend.
- Evaluado y descartado por ahora: hosting pago en la nube (Render/Railway,
  ~7-15 USD/mes) — no se justifica con solo 3 usuarios y la PC ya disponible
  en el horario necesario.

Pendiente de definir cuando se implemente: manejo de usuarios/roles (quién
ve qué), que hasta ahora se dejó fuera de esta conversación a propósito.

---

## 9. TIPOS Y VALIDACIONES

### 9.1 Conversión Decimal automática en Pydantic (antes numerada 8.1)

**Estado: implementado.** Todos los campos monetarios/de cantidad en los
esquemas Pydantic de entrada (`rutas/*.py`) pasaron de `float` a `Decimal`
(incluyendo las tuplas `list[tuple[int, Decimal]]` de insumos en
producción). Pydantic v2 internamente hace `Decimal(str(valor))` al
convertir un float entrante, el mismo criterio que ya se usaba a mano — se
verificó (`Decimal(19.99)` directo arrastra el error de punto flotante,
`M(x=19.99).x` con el campo tipado `Decimal` da `Decimal('19.99')` limpio).
Se eliminaron las ~20 conversiones manuales `Decimal(str(datos.campo))` en
los endpoints; ahora `datos.campo` ya llega como `Decimal` desde la
frontera. Verificado con curl (POST/PATCH `/activos` con `1234.57` y
`999.99`, sin arrastrar basura de punto flotante) y build de frontend sin
cambios necesarios ahí (el frontend sigue mandando JSON números normales).

### 9.2 Validación en frontend (comodidad, antes numerada 8.2)
El backend valida todo (seguridad). Agregar validaciones en el frontend como
comodidad: avisar antes de enviar (ej. horas pedidas > horas disponibles) sin
esperar el viaje al servidor.

**Estado: implementado.** Saldo insuficiente en Compras/Gastos/Pagos; stock u
horas insuficientes al agregar un insumo en Producción Intermedia/Terminada y
Ventas (sumando lo ya agregado del mismo lote en la lista actual, no solo la
última cantidad); y en Mermas, solo cuando el movimiento resta stock. Todas
bloquean la acción local — a diferencia del aviso no bloqueante de 6.6, aquí
el backend igual las rechazaría. El backend sigue siendo la única fuente de
verdad; esto es puramente comodidad.

## 10. PULIDO POST-PRUEBAS (ajustes durante el uso real)

Lote de ajustes menores detectados probando la app con datos reales (jul 2026).
Triaje por modelo: Sonnet para las mecánicas de frontend con precedente claro,
Opus para las que tocan lógica de precios/costeo en varias capas.

### 10.1 Pago por sueldo semanal (bug: tarifa como Bs/hora) — Opus
El pago se cargaba como Bs/hora y se multiplicaba directo por las horas, así que
un sueldo semanal (ej. S Bs por H horas/semana) daba S×8 por 8 h en vez de
(S/H)×8. Se pensaba el pago en términos semanales.

**Estado: implementado.** Sin migración (los campos `Pago_Trabajador` y
`Horas_Base_Trabajador` ya existían). Nueva semántica: `Pago_Trabajador` = sueldo
semanal, `Horas_Base_Trabajador` = horas por semana, y la tarifa/hora se deriva
en un único helper `servicios/trabajadores.tarifa_hora()` (= sueldo / horas
base). Se reemplazaron los 7 sitios que usaban `Pago_Trabajador` como Bs/hora
(pago sugerido, cierre semanal, producción intermedia/terminada, reproceso y las
dos valorizaciones de horas standby en balance). Catálogo: relabel a "Sueldo
semanal" + "Horas por semana" (obligatorio) y columna calculada "Bs/hora"; el
API `/trabajadores` devuelve la `tarifa`. Verificado con un trabajador de
prueba: sueldo/horas → tarifa correcta. Ver DECISIONES_DISENO 3.2. (Los
trabajadores viejos cargados en
Bs/hora quedan con tarifa baja hasta reingresar su sueldo semanal; eran datos de
prueba.)

### 10.2 Prorrateo de Junio 2026 marcaba "ya prorrateado" sin haberlo hecho
Al abrir el cierre de mes, Junio 2026 salía como ya prorrateado.

**Estado: resuelto (limpieza de datos, no era bug de código).** Había 2 filas
huérfanas en `Prorrateo_Mensual` de un prorrateo de prueba temprano, con montos
que ya no coincidían con los gastos actuales del mes. Se borraron esas 2 filas;
Junio quedó libre (`puede: true`).

### 10.3 Compras — predeterminar última cantidad+precio por proveedor — Opus
Al elegir materia prima + proveedor en Compras, autocompletar la cantidad y el
precio total con los de la última compra de ese par (si existe).

**Estado: implementado.** Endpoint `GET /ultima-compra/{id_materia}/{id_prov}`
(última compra por fecha+id, o `hay=false` si no hay historial). El frontend
predetermina `cantidad` y `precio_total` al quedar elegidos ambos, tanto en el
formulario simple como en la línea de la tabla de compras múltiples. Son valores
por defecto editables. Verificado: par 21/6 → 50 u / 223.88 Bs.

### 10.4 Venta — precio sugerido aparte y precio = último a ese cliente — Opus
Separar en la tabla de venta el "precio sugerido" (columna nueva, informativa)
del precio real editable; y que el precio real venga por defecto con el último
precio que se le vendió ese producto a ese cliente (fallback = sugerido).

**Estado: implementado.** Endpoint `GET /ultimo-precio-cliente/{id_cliente}`
devuelve el mapa `{id_producto: precio}` del último precio por producto (por
producto, no por lote; el anterior pudo salir de otro lote). Frontend: nueva
columna **"Precio sugerido"** entre Costo u. y Precio (muestra lo que calculaba
`precioSugerido`); el precio real de cada línea se predetermina con
`precioDefault(lote)` = último del cliente ?? sugerido, tanto al elegir un lote
como al resolver por FIFO. Se carga el mapa al elegir el cliente. Verificado:
cliente 1 → {1: 25, 2: 60}; cliente sin ventas → {} (cae al sugerido).

### 10.5 Menú — "Cierre producción" movido a Producción, con separador — Sonnet
"Cierre producción" vivía en el menú Cierre, junto al cierre de MES (prorrateo,
balance), aunque conceptualmente cierra la producción de la semana, no el mes.

**Estado: implementado.** Movido al menú **Producción**, como último item de un
segundo subgrupo (Absorción, Mermas, Cierre producción) separado visualmente
del flujo de producir (Compras…Prod. Terminada) con un `<hr>` entre ambos.
`MenuCategoria` soporta un flag `separador: true` en cualquier link del array
para dibujar la línea antes de él ([App.jsx](frontend/src/App.jsx),
[MenuCategoria.jsx](frontend/src/componentes/MenuCategoria.jsx)). El menú
Cierre quedó con solo Cierre de mes, Balance y Comparar cierres. Verificado en
el navegador: los 8 links de Producción en orden, `<hr>` antes de Absorción, y
Cierre producción ya no aparece en el menú Cierre.

### 10.6 Venta — buscar cliente por celular y/o licorería — Sonnet
Con el nombre solo no alcanza para elegir cliente en una venta: puede haber
varios "Pedro" y no saber cuál es, pero sí reconocer su licorería o celular.

**Estado: implementado.** Sin cambios de backend (`Celular_Cliente` y
`Licoreria_Cliente` ya se exponían en `/clientes`). El selector de cliente en
Ventas ahora usa `textoCliente(c)` = `nombre apellido (licorería · celular)`
tanto para mostrar como para filtrar — `SelectorBuscable` ya filtraba sobre el
texto mostrado (`obtenerTexto`), así que incluir esos campos ahí alcanzó para
poder buscar por cualquiera de los tres. Placeholder actualizado para que se
note. Verificado en el navegador: buscar "79797979" encuentra a Juan Perez por
celular; buscar "esquina" encuentra 2 clientes por su licorería (con el celular
al lado para distinguirlos); clientes deshabilitados siguen sin aparecer.

### 10.7 Jornadas — filtro de horas en standby — Sonnet
El checkbox "solo no pagadas" no dejaba ver las jornadas en standby (horas
registradas que aún no se consumieron en una producción — las que el cierre de
producción va a repartir), que es un concepto distinto de "pagada".

**Estado: implementado.** Sin cambios de backend (`horas_restantes` ya venía en
`/jornadas`). El checkbox se reemplazó por 3 radios mutuamente excluyentes:
**Solo no pagadas** (default, igual que antes), **Solo standby** (filtra
`horas_restantes > 0`) y **Todas**. Verificado en el navegador con datos
reales: standby mostró exactamente las 4 jornadas con horas restantes
(coincide con la consulta directa al backend); Todas mostró las 11.

### 10.8 Compra dividida (pliego) — el proveedor no se veía — Sonnet
Con una materia prima vendida por más de un proveedor (ej. Etiqueta E, con 2:
"adgf" y "Etiquetas"), el desplegable de proveedor aparecía sin ninguna
etiqueta que dijera para qué era — se confundía con cualquier otro campo del
formulario y parecía que la app "no decía" de qué proveedor se compraba.

**Estado: implementado (2 rondas).** No era un bug de datos
(`/proveedores-por-materia` ya devolvía los proveedores correctos) sino de
presentación. Ronda 1: el bloque no tenía rótulo — se agregó **"Proveedor del
pliego:"**. Ronda 2: el usuario probó con Etiqueta A + Etiqueta E y, aunque el
rótulo ya aparecía correctamente (verificado: el único proveedor que vende
AMBAS es "Etiquetas"), el texto plano se perdía entre la tabla y los
checkboxes y seguía pasando desapercibido. Se le puso una caja con fondo de
color (`#eef7ee`, mismo patrón que "Reparto del ingreso" en Ventas) para que
sea imposible no verlo, en los 3 casos (1 proveedor, varios, o ninguno — este
último en rojo `#fdeaea`). Verificado en el navegador reproduciendo el caso
exacto del usuario: caja verde con "Proveedor del pliego: Etiquetas".

### 10.9 Jornadas — pase de lista en tabla (registro múltiple) — Sonnet
Registrar la jornada de cada trabajador uno por uno con el formulario simple
era repetitivo. Se pidió una tabla con todos los trabajadores habilitados,
donde una fila en 0 o vacía significa que esa persona no vino ese día (se
omite, no es un error).

**Estado: implementado.** Nuevo endpoint `POST /jornadas-lote` (mismo patrón
que `compras-lote`/`gastos-lote`: se compone todo en una sola transacción y se
hace un único commit — todo o nada). Se refactorizó `registrar_jornada` en
`trabajadores.py` separando la validación/armado sin commit (`_aplicar_jornada`)
del wrapper que sí comitea, igual que `_aplicar_gasto` en `gastos.py`, para que
el servicio de lote (`jornadas_lote.py`) pueda componer varias jornadas
atómicamente. Frontend: tabla nueva "Registrar jornadas del día" con una fila
por trabajador habilitado (nombre, tarifa, horas del día); el botón arma las
líneas y envía solo las que tienen horas > 0.

Verificado por API: línea con horas=0 y con horas=null se omiten sin error
(solo se creó la jornada con horas>0); atomicidad confirmada (una línea con
horas>24 hizo fallar TODO el lote, sin dejar la línea válida a medias
registrada); mensaje de error claro si ninguna fila tiene horas. Verificado en
el navegador de punta a punta: se cargó 4h para un trabajador dejando el resto
vacío, se registró solo esa jornada ("1 jornada(s) registrada(s)") y apareció
en la tabla de abajo. Los registros de prueba se borraron después de verificar.

### 10.10 No había forma de crear una Cuenta desde la app — Sonnet
Detectado al revisar qué pasa si se vacía la base con `vaciar_prueba.bat`
(`TRUNCATE ... CASCADE` sobre TODAS las tablas): el catálogo de Cuenta tenía
`permitirCrear={false}` a propósito y el backend no exponía `POST /cuentas` —
ningún catálogo más tenía esta restricción. Si la base quedaba sin cuentas
(vaciado real, o simplemente arrancando todo de cero), no había manera de
volver a cargarlas desde la interfaz; la única salida era restaurar un backup
o insertar por SQL directo.

**Estado: implementado.** Nuevo `POST /cuentas` (`catalogos.py`): crea la
cuenta siempre con **saldo 0** — el saldo real se carga aparte con
*Transferencias > Ingreso externo* (movimiento `INGRESO_EXTERNO` ya existente),
para que el saldo siga derivándose *siempre* de movimientos, sin una excepción
nueva para el alta. Los roles **FABRICA** y **CASA** siguen siendo únicos: el
backend bloquea crear una segunda cuenta habilitada con ese rol si ya existe
una (mismo requisito que ya exigía `cuenta_unica_de_rol` en `reparto.py` para
el reparto 70/30 y el reparto por prioridad), con el rol o nombre de la
existente en el mensaje de error. Frontend: se sacó `permitirCrear={false}` del
catálogo de Cuenta (`PaginaCatalogos.jsx`) — ya usa el formulario genérico de
`Catalogo.jsx`, sin cambios ahí. Nota aparte, no relacionada con esto: los
**roles** (`FABRICA`/`CASA`/`OTRA`, en `ROLES_CUENTA`) y las **categorías de
Tipo de Bien** (`INMUEBLE`/`EQUIPO`/`OTRO`, en `CATEGORIAS_TIPO_BIEN`) son
constantes de código en `config.py`, no filas de tabla — un truncate nunca los
toca, a diferencia de los `Tipo_Bien` concretos que sí son filas y sí se
pierden (pero esos ya se podían recrear por UI, `POST /tipos-bien` siempre
existió).

Verificado por API: alta válida con rol OTRA (saldo queda en 0); bloqueo
correcto al intentar una segunda cuenta FABRICA (mensaje cita la existente,
"Billetera Fabrica"); nombre duplicado y rol inválido también rechazados.
Verificado en el navegador: el formulario "Agregar" ya aparece en el catálogo
Cuenta con Nombre + Rol, y la cuenta creada apareció en la tabla con saldo 0 y
botón Eliminar habilitado. La cuenta de prueba se borró después de verificar.
