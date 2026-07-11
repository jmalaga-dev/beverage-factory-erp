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

### Estado del prorrateo (oculto en MVP)
La pantalla PaginaProrrateo.jsx existe pero está oculta (sin enlace ni ruta en
App.jsx) porque depende de la lógica de horas heredadas (1.1), no construida aún.
Lo que le falta para ser funcional:
- Registro de gastos extra POR MES con su monto variable y su FECHA DE PAGO
  (la factura de luz cambia cada mes; el pago se hace el último día del mes).
- Control visual de qué gastos del mes ya se pagaron (en Excel se hacía por color).
- El prorrateo se dispara cuando todos los gastos del mes están pagados.
- Cálculo de horas reales por producto en el período mensual (depende de 1.1).
- Reparto proporcional de los gastos solo entre los productos que usaron la
  fábrica ese mes, según sus horas (directas + heredadas).

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

### 3.6 Pre-recetas (producción intermedia pre-llenada) — del Excel
Plantilla por producto intermedio ("Jarabe Base 1 = 5 kg de azúcar + 3 L de
alcohol"): al elegirla, el formulario de producción se pre-llena resolviendo
los lotes por FIFO (3.1) y respetando restos (si al lote más viejo le quedan
2 kg, propone 2 de ese y 3 del siguiente). Siempre editable y no
restrictivo: las horas de trabajadores cambian cada día, y un lote puede
llevar algo extra o de menos. Requiere tablas nuevas de receta (cabecera +
detalle de insumos).

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

### 3.8 Compra dividida en proporción (pliegos de etiquetas) — del Excel
Un pliego doble oficio cuesta 100 Bs y salen 5 etiquetas de A, 3 de B y 4 de
C, de tamaños distintos: el costo se reparte por **área** (área de cada
etiqueta × cantidad / área total del pliego) y cada tipo de etiqueta entra
como materia prima con su costo proporcional. Hoy se calcula a mano y se
ingresan como compras separadas. Pantalla auxiliar: una compra "madre" que
se despieza en N materias primas con reparto proporcional por área (o por
un factor genérico).

### 3.9 Botellas por paquete en Producto_Terminado — del Excel
Columna nueva `Botellas_Por_Paquete` (6, 8 o 1 según el producto, migración
simple). Habilita: resúmenes en paquetes equivalentes (4.7), el costo por
paquete en la simulación (1.5), y registrar producción/venta por paquete
con conversión automática a botellas.

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

**Pendiente:** la **deuda a proveedor** nacida de una compra a crédito
parcial (ver la ampliación de 5.1) se conecta cuando se implemente ese caso.

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
solo el destino. Falta servicio + endpoint + pantalla. Con el reparto por
prioridad (sección 2) las transferencias manuales deberían volverse raras,
pero el ingreso externo sigue siendo necesario siempre.

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

### 8.4 Migración de datos reales del Excel (incluye limpieza previa)
Antes de migrar: **borrar todos los datos de prueba** acumulados durante el
desarrollo y dejar la BD limpia (script de reset: TRUNCATE de las tablas de
datos con reinicio de secuencias/ids; decidir si los catálogos de prueba se
conservan o también se recrean desde el Excel). Con respaldo previo (8.3)
por si acaso.
Al final, cuando el sistema esté probado, migrar los 3 archivos de Excel con los
datos históricos reales, con pruebas de paridad contra el Excel.

### 8.5 Subir el repositorio a GitHub
Actualmente el versionado es local. Subir a GitHub cuando haya una beta, con el
README y la documentación, para que el repositorio sea visible (útil para CV).

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
