# Decisiones de diseño — Fábrica V2 (MVP)

Este documento registra las decisiones de diseño y arquitectura del MVP: qué se
construyó y por qué. Las mejoras y funcionalidades pospuestas para versiones
futuras están en un documento aparte: `MEJORAS_FUTURAS.md`.

---

## 1. STACK Y ARQUITECTURA

- **Base de datos:** PostgreSQL. Elegido sobre Access por escalabilidad,
  integridad referencial y valor profesional.
- **Backend:** Python con SQLAlchemy (ORM) + FastAPI (API REST).
- **Frontend:** React con Vite (JavaScript, no TypeScript, para el MVP).
- **Reportería (futuro):** Power BI conectado a PostgreSQL.
- Arquitectura por capas: Frontend (React) → API (FastAPI) → Servicios (lógica de
  negocio) → Base de datos. Los servicios son el corazón estable; hoy los llaman
  los endpoints, y son reutilizables entre distintos clientes (web, móvil, BI).
- **Rutas por dominio:** los endpoints se organizan en `app/rutas/` (un router
  por área: clientes, compras, ventas, etc.), espejando `app/servicios/`;
  `main.py` solo los ensambla. Mismo principio de capas aplicado a la API:
  fácil de navegar y sin endpoints duplicados.
- **Acceso centralizado al backend en el frontend:** el frontend solo llama a
  la API a través de `src/api.js` (URL base única + helpers `apiGet`/
  `apiPost`/`apiPatch` con manejo de errores). Evita repetir la URL y el
  parseo de errores en cada pantalla; si cambia el puerto o el dominio al
  desplegar, se edita un solo lugar.
- **Editar, deshabilitar y borrar en catálogos (mejora 6.1):** los 9
  catálogos que solo tenían POST/GET ganaron el juego completo. Tres reglas,
  cada una derivada de un principio ya existente:
  - **Editar es seguro y sin guardrail.** Como las relaciones son por Id (no
    por texto), renombrar un catálogo no corrompe el historial que lo
    referencia. Editar la tarifa de un trabajador solo afecta producciones
    futuras (el costo de las hechas quedó congelado, Camino 1). Excepción: el
    `Saldo_Actual_Cuenta` no se edita a mano — se deriva de los movimientos
    (libro de movimientos único); de Cuenta solo se edita el nombre y el rol.
    Por el mismo principio, crear una Cuenta (mejora 10.10) siempre la deja en
    saldo 0 — el saldo real se carga aparte con *Transferencias > Ingreso
    externo*, nunca como valor inicial del alta. FABRICA y CASA son roles
    únicos: crear una segunda cuenta habilitada con ese rol se bloquea (mismo
    requisito que ya exigía `cuenta_unica_de_rol` para el reparto).
  - **Deshabilitar en vez de borrar.** Se extendió el `Habilitado_*` de
    Trabajador (6.5) a los otros 8 catálogos (migración 008). Un item
    deshabilitado desaparece de los desplegables de operaciones nuevas pero
    sigue existiendo; su historial queda intacto. El frontend filtra por
    `habilitado` en el punto del desplegable (no en el estado global), para
    que las tablas de historial sigan resolviendo el nombre de un item
    deshabilitado. Único que muestra deshabilitados a propósito: el
    desplegable de trabajadores en Pagos (para cerrar cuentas pendientes, ya
    decidido en 6.5).
  - **Borrar solo si no hay historial.** El DELETE es un borrado real y se
    permite únicamente si nada referencia al item (`en_uso == false`, que
    cada GET calcula recorriendo las FK que lo apuntan); si tiene historial,
    se bloquea con 400 y se sugiere deshabilitar. Mismo guardrail "intacta"
    de jornadas (3.4), generalizado. Así se respeta la inmutabilidad del
    histórico.

  El primer PATCH de la API (`/trabajadores/{id}/habilitado`) inauguró el
  criterio de "un endpoint por campo/acción" en vez de un PUT de objeto
  completo; 6.1 lo mantiene: por entidad hay un PATCH de edición de campos
  descriptivos, un PATCH `.../habilitado` y un DELETE, no un PUT genérico.
- **Constantes de negocio centralizadas:** valores ajustables como
  `UMBRAL_STOCK_MINIMO` viven en `app/config.py`, no repartidos por el
  código, para poder ajustarlos en un solo lugar sin buscar cada uso.
- Migración desde una herramienta previa en Excel/VBA que se volvió lenta e
  inescalable por mezclar frontend, lógica y datos en hojas de cálculo.

---

## 2. DISEÑO DE BASE DE DATOS

Principios aplicados en las 31 tablas:

- **Trazabilidad por lote** en toda la cadena: compra → producto intermedio →
  producto terminado → venta. Permite rastrear qué se produjo y vendió con cada
  lote de insumo (clave en alimentos/bebidas).
- **Libro de movimientos único** para el flujo de caja: los saldos se derivan de
  los movimientos registrados, no se guardan sueltos. Garantiza consistencia y
  auditabilidad (como funciona un banco).
- **Inmutabilidad del histórico:** mermas, ajustes, devoluciones y reprocesos se
  registran como eventos nuevos, nunca se borra ni sobrescribe.
- **Deshabilitar en vez de borrar:** los catálogos que ya tienen historial
  encima (ej. `Trabajador`, con jornadas y pagos vinculados) no se borran —
  se marcan `Habilitado_*` en `false`. Extiende el mismo principio de
  inmutabilidad: nunca se pierde a quién le pagaste o qué produjo, solo deja
  de ofrecerse para trabajo nuevo.
- **Sin datos duplicados:** los datos derivados (totales, márgenes) se calculan
  vía JOIN o al vuelo, no se almacenan.
- **Eventos vs. stock — qué se recalcula y qué se congela:** los movimientos
  con fecha (compras, ventas, pagos, gastos) son inmutables una vez ocurridos,
  así que sus totales por período se calculan siempre al vuelo con una query
  (nunca se guardan aparte, excepto dentro de una foto de Balance). El stock,
  en cambio, cambia con el tiempo — se vende, se consume — así que su
  composición en un momento dado solo se puede conocer si se congela en ese
  momento (ver Balance y Balance_Detalle_Producto); después ya no se puede
  reconstruir con una query.
- **Relaciones por Id**, no por código.
- **Tipos `numeric`** para cantidades y dinero (precisión exacta; evita el error
  de punto flotante como el 1.4e-17). SQLAlchemy los maneja como `Decimal`.
- **Celulares como varchar** (texto), no número.
- Códigos QR se generan en el backend cuando se necesiten, no se guardan en BD.

---

## 3. COSTEO

### 3.1 Materia prima — Filosofía B (costo real del lote)
El costo de la materia prima se toma al **precio real del lote** de compra
(`Precio_Compra / Cantidad_Compra`). Si se corrige un lote, se recalcula, porque
el dato es directo y conocido al producir.

### 3.2 Trabajo — tarifa pactada al producir (Camino 1)
El costo del trabajo en una producción se calcula con la **tarifa pactada** del
trabajador, no con el pago real semanal.

**Tarifa/hora derivada del sueldo (mejora: pago semanal).** El sueldo NO se
carga como Bs/hora sino como **sueldo del periodo** (`Pago_Trabajador` = sueldo
semanal) sobre las **horas de ese periodo** (`Horas_Base_Trabajador` = horas por
semana). La tarifa/hora es `Pago_Trabajador / Horas_Base_Trabajador`: ej. 280 Bs
por 48 h → 5.8333 Bs/h, y 8 h valen 46.66 Bs (no 280×8). El motivo: el usuario
piensa el pago en términos semanales, no por hora, y calcular la tarifa a mano
era fuente de errores. Toda la app deriva la tarifa por un único helper,
`servicios/trabajadores.tarifa_hora(trabajador)`, para que ningún cálculo
(pago sugerido, costo de producción, valorización de horas standby en balance)
use el sueldo semanal como si fuera Bs/hora. Si no hay horas base cargadas, el
helper devuelve 0 (no inventa costo); por eso el catálogo obliga a cargar las
horas por semana.

Razones:
- La tarifa pactada existe y es conocida al momento de producir.
- El pago real ocurre después (semanalmente) y puede diferir.
- Da un costo unitario inmediato y completo al producir, sin esperar al pago.
- Las diferencias entre estimado y real se tratan como ajuste a nivel de flujo de
  caja general, NO se reparten producto por producto.

Consecuencia: el costo de producción es un estimado estable, suficiente para
decidir rentabilidad entre productos, que es el objetivo principal.

(El recálculo fiel — "Camino 2" — está documentado en MEJORAS_FUTURAS.md.)

### 3.3 Costeo en cadena
El costo se propaga a lo largo de la cadena: un producto intermedio guarda su
`Costo_Unitario`, y cuando otro intermedio o un terminado lo consume, hereda ese
costo (cantidad × costo unitario). Así el costo del terminado refleja todos sus
insumos: materia prima (precio de lote) + trabajo (tarifa pactada) + intermedios
(su costo unitario).

### 3.4 Valoración de stock — promedio ponderado
Cuando hay varios lotes del mismo producto con distinto costo, el stock
consolidado se valora con **promedio ponderado** (suma de cantidad×costo de cada
lote, dividido entre el total). Refleja el costo real mezclado, no un promedio
simple.

### 3.5 Umbral de stock mínimo
Un lote con menos de `UMBRAL_STOCK_MINIMO` (0.0001, en `app/config.py`) se
considera agotado: deja de listarse como disponible y de contar en el
balance, aunque la fila siga con su resto positivo en la BD. No es basura de
punto flotante (`Decimal` ya la evita) sino un remanente real demasiado chico
para usarse. Limpiar esas filas de verdad (con una merma automática) queda
pendiente, ver 3.5 en MEJORAS_FUTURAS.md.

### 3.6 Patrimonio contable — costo o mercado, el menor (mejora 4.3)
`Patrimonio` en `Balance` era un alias de Escenario A (efectivo + stocks
valorizados + activos fijos - deudas), y ahí el stock de producto terminado
se valoraba a `Precio_Venta_Recomendado_Producto_Terminado`, es decir,
reconociendo la ganancia de lo que todavía no se vendió — correcto para una
vista de liquidez ("cuánto tendría si liquido hoy"), pero no para un
patrimonio contable.

Se separaron los dos conceptos: los Escenarios A/B/C siguen siendo la vista
de liquidez sin cambios; Patrimonio ahora valoriza el producto terminado al
**menor entre costo de producción y precio de venta** (criterio "costo o
mercado, el menor"), usando el costo real que ya guarda cada lote
(`Produccion.Precio_Unitario_Producto_Terminado`, pese al nombre es el costo
unitario de producción, no un precio de venta). Migración 007 agrega
`Valor_Stock_Producto_Terminado_Conservador` a `Balance` para que la foto
histórica deje ver por qué Patrimonio difiere de Escenario A (mismo
principio de transparencia que 4.2 con Inmuebles/Equipos/Otros). Como el
histórico es inmutable, las fotos tomadas antes de esta mejora conservan su
Patrimonio calculado con la fórmula vieja.

### 3.7 Comparar dos fotos de balance del pasado (mejora 4.4)
La pantalla de Balance ya compara "estado actual (en vivo) vs. última foto
guardada" — siempre contra el *ahora*, y solo contra la foto más reciente. Como
las fotos son inmutables y se acumulan, faltaba poder comparar **dos cierres del
pasado** entre sí (p. ej. junio vs. julio) para ver la evolución. No requirió
migración: la foto ya guarda todo lo comparable. Solo se expuso el histórico
(`GET /balances`, todas las fotos serializadas) y se compara en el cliente. Para
no duplicar la forma de los datos, la lógica que arma el dict de una foto se
extrajo a `serializar_balance()` y la reusan la última foto y el listado. La
comparativa vive en pantalla aparte (`Comparar cierres`) a propósito: mezclar
"vs. ahora" con "cierre vs. cierre" confunde qué se está mirando. Las fotos se
identifican por `#id — fecha` porque varias pueden compartir fecha (se pueden
tomar varias el mismo día). Un campo ausente en una de las dos fotos (columna
agregada después, histórico inmutable) se muestra "—", no se resta contra cero.

**Impresión física (PDF):** el informe comparativo y el reporte de Balance se
imprimen con `window.print()` del navegador (sin librerías) + un bloque
`@media print` en `App.css` que oculta el menú y los controles `.no-imprimir`
(selectores, botones) y deja solo la tabla en negro sobre blanco. Se eligió la
impresión nativa del navegador (que ya ofrece "Guardar como PDF") en vez de
generar el PDF en el backend: cero dependencias nuevas y el usuario controla
formato/márgenes desde el diálogo del sistema.

### 3.8 Absorción de costos indirectos por botella (mejora 1.4)
Costos que no son insumo directo (utensilios/equipos, feriados, mermas) se
reparten entre las botellas producidas después, como una línea de costo más
en cada producción, hasta saldar el ítem (`Item_Absorcion`, con botellas
estimadas y restantes). Dos decisiones:
- **Un solo camino por compra:** un utensilio va SOLO a absorción, nunca
  también a Activo fijo — si fuera ambos, su costo se contaría dos veces
  (una en el patrimonio como activo, otra capitalizado en el stock vía
  absorción). Se descartó la alternativa "activo con depreciación" por
  complejidad.
- **La absorción capitaliza el costo en el stock terminado:** al sumarse al
  `Precio_Unitario_Producto_Terminado`, el costo indirecto entra al valor
  del stock. Es intencional (que el precio de venta cubra estos gastos, como
  en el Excel). Efecto en el balance: el costo pendiente de absorber baja el
  patrimonio al comprarse (el utensilio no es activo), y se recupera a
  medida que las producciones lo trasladan al stock. Es costeo gerencial,
  no una merma de patrimonio permanente.

### 3.9 Precio sugerido y taxi en la venta (mejora 6.12)
- **Precio sugerido de un lote** = el mayor entre el precio recomendado del
  catálogo y `costo_del_lote / (1 − margen)`, redondeado a 2 decimales. El
  **margen es una caja editable en la propia pantalla de venta** (default
  35%), no una constante del backend: puede cambiar seguido y el usuario no
  debería tocar código para ajustarlo. Por eso el cálculo se hace en el
  frontend (el backend solo entrega costo y recomendado por lote); al cambiar
  la caja, el precio sugerido se recalcula en vivo para el autocompletado y el
  FIFO. El margen se define **sobre el precio de venta** (no sobre el costo)
  para que coincida con el "% de ganancia" que muestra la pantalla:
  `ganancia / ingreso`. Es solo una sugerencia: el precio de cada línea es
  **editable en la tabla** (sin quitar y re-agregar), y un aviso rojo marca si
  queda bajo el costo del lote, pero no bloquea.
- **FIFO reconciliado con lo ya cargado:** al resolver un producto por FIFO se
  descuenta lo que ya está comprometido en las líneas actuales, así resolver
  el mismo producto dos veces no vuelve a meter lotes agotados ni pasa del
  stock. El backend igual lo valida al registrar (suma por lote), pero se
  evita en pantalla para no descubrir el error recién al confirmar.
- **Taxi/delivery = solo cálculo en pantalla.** Se prorratea de forma uniforme
  entre todas las botellas de la venta (`taxi / total_botellas`) para ver el
  neto real por línea y el % ponderado. **No mueve caja ni crea un
  `Movimiento`**, y no se envía al backend al registrar la venta. Motivo: el
  taxi es un dato de análisis para decidir precios/descuentos, no un hecho
  contable atado a la venta; si se pagó de verdad, se registra aparte como un
  Gasto normal. Por eso `ventas.py` y la tabla `Venta` no cambiaron.

### 3.10 Devolución y reproceso (mejora 3.3)
- **La devolución es una sola operación atómica que compone tres cosas:** el
  reembolso (SALIDA de dinero de una cuenta), la vuelta del producto al stock
  del lote original (`DEVOLUCION` ENTRADA), y —según el destino elegido— nada
  más (STOCK), una merma (`MERMA` SALIDA + absorción del costo, 1.4) o un
  reproceso. Decisión clave: **el producto SIEMPRE vuelve primero al stock y
  luego, si corresponde, se merma o reprocesa** (entra y sale). No es un rodeo:
  deja en inventario el rastro real de lo que pasó (volvió, y después se
  desechó/reprocesó), en vez de un salto contable sin traza.
- **El reembolso y el costo van por caminos separados.** El dinero que se
  devuelve es el PRECIO que pagó el cliente (lo elige el usuario, o se
  autocompleta desde la venta vinculada); el efecto en inventario/costo usa el
  COSTO del lote. Son magnitudes distintas y no se mezclan.
- **Vínculo con la venta = opcional.** Si se indica `id_venta`, se valida que
  ese lote se haya vendido en esa venta y que no se devuelva más de lo vendido,
  y el frontend autocompleta el reembolso (precio real × cantidad). Sin
  vínculo, se elige el lote y el monto a mano (devoluciones viejas, negociadas,
  o cuando no importa rastrear la venta exacta).
- **Reproceso = terminado → mismo producto, arrastrando su costo.** Consume una
  cantidad PARCIAL de un lote y crea un lote NUEVO del mismo producto; su costo
  = *(costo unitario del origen × cantidad)* + insumos nuevos (tapas=MP +
  trabajo). Se enlazan por `Ref_Reproceso` (el movimiento de SALIDA del origen
  apunta al lote nuevo). **No corre absorción de indirectos (1.4):** esas
  botellas ya absorbieron su parte al producirse; volver a absorber las cobraría
  doble. La `cantidad_producida` puede ser ≤ a la consumida (algunas se rompen
  del todo); nunca mayor (no se crea producto de la nada). Se puede reprocesar
  también sin devolución (rotura en depósito), misma lógica.
- **Un core de inventario sin commit para poder componer.** Se separó
  `_aplicar_movimiento_inventario` (valida, mueve stock, absorbe; sin commit)
  de `registrar_movimiento_inventario` (lo envuelve y hace commit). Así la
  devolución encadena reembolso + entrada + merma/reproceso en UNA transacción
  (todo o nada), reutilizando la lógica de merma/absorción ya probada.

### 3.11 Compra dividida por proporción (mejora 3.8)
- **No hay tabla "compra madre".** El pliego se reparte y el resultado son N
  filas `Compra` normales (una por materia prima), indistinguibles de una
  compra suelta salvo por haberse creado en el mismo lote de la transacción.
  No hacía falta modelar el vínculo entre ellas: nada en el negocio necesita
  "deshacer el pliego completo" después, cada materia prima vive su vida como
  cualquier otro lote (FIFO, mermas, etc. no necesitan saber que vino de un
  reparto).
- **Factor genérico, no "área" a secas — y el reparto es SOLO por factor.**
  Cada línea tiene un `factor` cualquiera (área total que ocupa esa materia en
  el pliego es el caso típico del Excel, pero puede ser peso, volumen, o
  cualquier número proporcional); la parte del precio de una línea es
  `factor_línea / factor_total`. **La cantidad NO participa del reparto** —
  solo se usa para registrar `Cantidad_Compra` del lote y calcular el precio
  unitario resultante (`precio_asignado / cantidad`). Se probó explícitamente
  que una cantidad grande (500) junto a un factor chico no infla el % de esa
  línea: el peso de mezclar ambos en el reparto rompía casos reales donde
  cantidad y factor no son proporcionales entre sí.
- **La última línea absorbe el redondeo.** Repartir con `round(..., 2)` línea
  por línea puede dejar un resto de centavos que no cierra contra el total; en
  vez de eso, todas las líneas salvo la última usan la proporción redondeada,
  y la última toma "lo que falta" (`precio_total − suma_de_las_anteriores`).
  Así la suma siempre cierra exacto.
- **Proveedor = intersección, no elección libre.** El pliego se compra a UN
  proveedor que vende TODAS las materias primas de las líneas; el frontend
  calcula la intersección de proveedores activos por cada materia (vía
  `/proveedores-por-materia/{id}`) y solo ofrece esos. Si la intersección es
  vacía, se bloquea y se pide registrar el proveedor para las que falten.
- **Reutiliza crédito parcial y pedido pendiente (5.1) sin reinventarlos.**
  `monto_pagado` y `recibida` de la compra madre se reparten con el mismo
  factor que el precio; cada línea corre exactamente la misma lógica que una
  compra suelta (deuda al proveedor por el faltante, stock invisible hasta
  recibir), porque literalmente reutiliza `_aplicar_compra`.
- **Un core de compras sin commit, mismo patrón que 3.3.** Se separó
  `_aplicar_compra` (valida, mueve dinero/deuda, crea el lote; sin commit) de
  `registrar_compra` (lo envuelve y hace commit), para que la compra dividida
  encadene N líneas en una transacción atómica (todo o nada): si una materia
  prima no tiene el proveedor elegido, ninguna línea del pliego se registra.

### 3.14 Reparto de gasto por prioridad de cuentas (mejora 2, parte A+B)
- **Rol de cuenta, no nombre.** Se agregó `Rol_Cuenta` (FABRICA/CASA/OTRA); las
  reglas de prioridad y el reparto se apoyan en el rol explícito, no en el texto
  del nombre (que se puede cambiar). El orden por tipo de gasto vive en
  `PRIORIDAD_CUENTAS` (`app/config.py`): familiar → Casa, Fábrica, Otra; de
  fábrica → Fábrica, Casa, Otra.
- **El reparto PROPONE, el usuario dispone** (mismo patrón que FIFO). El sistema
  drena las cuentas por prioridad de rol (y a igual rol, la de más saldo
  primero) hasta cubrir el monto, respetando saldos; el usuario ajusta cuánto
  sale de cada una antes de confirmar. La regla es que la suma de fuentes iguale
  el gasto.
- **Un gasto = varios movimientos SALIDA, atómicos.** Como un gasto es un
  `Movimiento` puro (sin tabla propia), partirlo entre cuentas es natural: una
  SALIDA por fuente, todas en una transacción (o todas o ninguna). El núcleo del
  algoritmo (`asignar_por_prioridad`) es una función pura sin BD, para poder
  probarlo aislado de las cuentas reales.
- **Alcance acotado a gastos.** Compras y pagos NO entran al reparto por ahora:
  sus registros (`Compra`/`Pago_Trabajador`) enlazan un solo movimiento, y
  partir el pago entre cuentas rompería ese enlace y el cálculo del balance —
  requiere un cambio de modelo (varios movimientos de pago por registro) que se
  pospuso. Los aportes externos siguen cargándose con `INGRESO_EXTERNO` (7.5).

### 3.15 Reparto 70/30 de la venta con recuperación de inversión (mejora 2.C)
- **El saldo por producto se calcula al vuelo, no en una columna.** `saldo =
  ingresos acumulados de sus ventas − inversión acumulada en producirlo`, sobre
  `Produccion` + `Detalle_Venta` que ya existen (por PRODUCTO, no por lote). Es
  el mismo criterio de "no duplicar" del resto del proyecto: evita un total
  corriente que se desincronice, y el volumen es chico. La inversión **resta el
  costo arrastrado por reprocesos** (al reprocesar, las botellas salen de un
  lote a otro pero la `Cantidad_Producida` del origen no baja, así que su costo
  se contaría dos veces).
- **El ingreso de la venta se reparte, no va a una cuenta elegida.** Mientras el
  producto no recuperó su inversión (saldo < 0), el 100% va a Fábrica hasta
  llegar a 0; el excedente (y todo si ya recuperó) se reparte
  `REPARTO_VENTA_FABRICA` (0.70) a Fábrica y el resto a Casa. El % vive en
  `app/config.py` (en el Excel era una celda global). Por eso la pantalla de
  Ventas dejó de pedir cuenta por línea: el destino lo decide la regla.
- **El saldo se acumula línea por línea dentro de la venta.** Se arranca del
  saldo real en la BD y se suma cada línea, así dos líneas del mismo producto en
  la misma venta respetan bien el cruce del cero (la primera puede terminar de
  recuperar y la segunda ya repartir 70/30).
- **Cada línea = una `ENTRADA` por destino con monto > 0** (Fábrica y/o Casa).
  A diferencia de las compras, la venta sí puede partirse en varios movimientos
  sin romper nada: el balance suma las `ENTRADA` directo (no depende de que la
  línea enlace un único movimiento). `reparto=False` conserva el modo clásico
  (una cuenta explícita por línea) por si hiciera falta.

### 3.13 Horas-hombre acumuladas/heredadas y prorrateo mensual (mejora 1.1)
- **Una columna de horas, no un pool que se vacía.** Cada producción guarda
  `Horas_Acumuladas` (horas-hombre del lote completo). La herencia al consumir
  `q` unidades es `q × Horas_Acumuladas / Cantidad_Producida`: como la tasa por
  unidad es constante, lo que se consume se lleva su parte y lo que queda
  conserva la suya, sin necesidad de una segunda columna de "horas restantes"
  (el remanente es `Cantidad_Restante × tasa`). Es el mismo mecanismo que ya usa
  el costo unitario, aplicado a horas.
- **Solo horas, no su equivalente en dinero.** La plata del trabajo (directo e
  intermedio) ya está dentro del costo unitario; duplicarla en una columna
  aparte agregaba bookkeeping por poco valor. La dimensión NUEVA que aporta 1.1
  es las horas-hombre, que el costo no expresaba.
- **Atribución por mes de producción del terminado.** Un jarabe hecho hace
  meses, al consumirse este mes, hereda sus horas a la producción de este mes;
  por eso el prorrateo agrupa los terminados por su mes de producción y suma
  `Horas_Acumuladas`. El prorrateo dejó de ser una recursión al vuelo: es una
  suma sobre la columna.
- **El motor se llena en las cuatro rutas de producción.** `producir_intermedio`
  (directas + heredadas), `producir_terminado` (heredadas; las directas llegan
  después), el **cierre 3.7** (suma las horas directas que asigna) y el
  **reproceso** (hereda del lote origen + trabajo nuevo). El backfill de los
  datos viejos recalcula desde los detalles reales en orden de dependencia.
- **Gastos variables por mes, separados del gasto recurrente.** `Gasto_Extra` es
  el gasto recurrente (luz, agua) con su monto típico; `Gasto_Extra_Mes` es el
  monto REAL de un mes y su pago (SALIDA de una cuenta). El prorrateo usa esos
  montos y **exige que todos estén pagados** antes de correr. El prorrateo en sí
  NO mueve dinero (el dinero salió al pagar cada gasto): es una asignación
  analítica congelada (`Prorrateo_Mensual`), como el resto de las "fotos".

### 3.12 Cierre de producción con prorrateo de horas standby (mejora 3.7)
- **Se separa la mano de obra del momento de producir.** En la práctica no hay
  quien mida qué produjo cada quien, así que los terminados se producen solo
  con MP e intermedios (sin trabajo) y las jornadas quedan en standby (horas
  registradas sin consumir, que el balance ya valoriza). El trabajo se asigna
  después, en el cierre, repartiéndolo entre lo que efectivamente se produjo.
- **No hubo que cambiar el flujo de producción.** `producir_terminado` ya
  permite producir sin trabajo (exige al menos un insumo, que puede ser solo
  MP/intermedios). El cierre es una herramienta que se suma; quien quiera puede
  seguir asignando trabajo a mano en un caso puntual (esos lotes se saltan).
- **El costo se ACTUALIZA sumando, no se recalcula.** Cada lote nació con su
  costo parcial (MP+intermedios+absorción). El cierre le suma
  `trabajo_asignado / botellas_producidas` al costo unitario, sin volver a
  tocar lo anterior. Así no hay riesgo de perder la absorción ni de recomputar
  mal los insumos.
- **Reparto por botellas PRODUCIDAS, no restantes.** El peso de cada lote es su
  `Cantidad_Producida` (no lo que queda en stock): la mano de obra fue para
  hacer todo el lote, aunque ya se haya vendido parte. Y cada jornada standby
  se reparte ENTERA (queda en 0), con la última línea absorbiendo el redondeo
  para que la suma de horas cierre exacta.
- **Solo terminados (decisión de negocio 3.7).** Los intermedios del rango no
  reciben horas; su mano de obra la absorben las botellas de la semana. El
  modelo de horas heredadas en intermedios (1.1) es aparte. Esto puede
  subvalorar el stock de intermedios que se guarda para otra semana, aceptado
  como simplificación (replica el Excel).
- **Idempotente por construcción.** El cierre consume el standby de las
  jornadas; re-correrlo no encuentra horas que repartir. Y solo toma los lotes
  del rango SIN trabajo asignado, así que nunca duplica sobre uno ya cerrado.
- **Preview y ejecución comparten el mismo cálculo.** `calcular_cierre` arma el
  plan sin tocar la BD (lo usa la vista previa) y `ejecutar_cierre` lo recalcula
  desde la BD y lo aplica (no confía en números del cliente), así lo que se ve
  es exactamente lo que se confirma. Rango libre de dos fechas, no semana fija.

---

## 4. FLUJO DE OPERACIONES (patrón de los servicios)

Cada servicio de negocio sigue el patrón: **validar TODO antes de tocar nada** →
ejecutar de forma atómica (try/commit) → rollback si algo falla. Esto garantiza
que operaciones que afectan varias tablas (dinero + inventario) pasen completas o
no pasen (integridad).

Operaciones construidas (con backend, API y pantalla):
- Compra de materia prima (valida saldo, crea movimiento SALIDA, descuenta
  cuenta; exige proveedor de esa materia prima — ver mejora 5.1).
- Registro de jornada de trabajo (solo horas, no mueve dinero).
- Pago semanal a trabajador (calcula sugerido = horas pendientes × tarifa; paga
  monto real que puede diferir; marca jornadas como pagadas sin borrarlas).
- Producción intermedia y terminada (consumen listas de insumos: materia prima +
  trabajo + intermedios; validan stock de cada lote; calculan costo unitario).
- Venta (varias líneas; cada línea vende de un lote, a precio real, cobrada a una
  cuenta que puede ser distinta por producto; sube saldo, descuenta stock).
- Gasto (salida de una cuenta, con grupo validado; sin inventario).
- Movimiento de inventario (merma/ajuste/devolución sobre lote de MP, intermedio
  o terminado; sentido según tipo: merma resta, devolución suma, ajuste elige).
- Balance (foto congelada: efectivo, stocks valorizados, deudas, escenarios,
  patrimonio).
- Prorrateo mensual (reparte gastos extra entre productos según horas).
- Transferencia entre cuentas propias e ingreso externo (mejora 7.5).
- Deuda: registrar (simple o préstamo con ingreso) y pagar/amortizar
  (mejoras 7.0/7.3).
- Compra a crédito parcial y pedido pendiente (mejora 5.1 ampliación): el
  lote guarda el precio completo (costo real), el faltante se vuelve deuda
  al proveedor, y un pedido pendiente no cuenta como stock hasta recibirlo.
- Compra dividida por proporción (mejora 3.8): un pliego se reparte por
  factor entre N materias primas, cada una registrada como una Compra normal,
  todas en una sola transacción atómica.
- Cierre de producción (mejora 3.7): reparte las horas standby de un rango
  entre los terminados producidos, por botellas, y suma el trabajo al costo
  de cada lote (vista previa + confirmar, atómico).
- Horas-hombre acumuladas/heredadas (mejora 1.1): cada producción arrastra sus
  horas directas + heredadas de los intermedios; el cierre de mes reparte los
  gastos extra (pagados) entre los terminados según esas horas.
- Reparto de gasto por prioridad (mejora 2.B): un gasto se cubre con varias
  cuentas por orden de prioridad de rol; una SALIDA por fuente, atómico.
- Absorción de costos indirectos por botella (mejora 1.4): registrar
  utensilios/feriados (sale dinero + ítem a absorber) y absorber en cada
  producción.
- Resolución FIFO de lotes (mejora 3.1) y pre-recetas de producción
  intermedia y terminada (mejora 3.6): sugerencias que pre-llenan las listas
  de insumos; los servicios de producción/venta siguen recibiendo lotes
  explícitos, así que FIFO/recetas no cambian su lógica ni su validación.

**Agrupar lotes repetidos antes de descontar (correctitud):** los servicios
que consumen lotes (producción intermedia/terminada, venta) validan el stock
y descuentan por **cantidad total por lote**, no línea por línea. Sin esto,
dos líneas del mismo lote (5+5) pasaban cada una la validación (5 ≤ 5) pero
al ejecutar descontaban 10 de un lote con 5, dejándolo en negativo. Se agrupa
con `servicios/agrupar.py` (producción) o sumando por lote en la validación
(venta). En el frontend, `fusionar` (`src/insumos.js`) une las líneas del
mismo lote en la UI. El backend sigue siendo la fuente de verdad: aunque el
frontend no fusionara, el backend ya no puede dejar stock negativo.

**Categorizar una SALIDA sin adivinar:** para separar compras / pagos a
trabajadores / gastos dentro de los movimientos de dinero (todos
`Tipo_Movimiento = "SALIDA"`), se usa el vínculo real que cada tabla ya tiene
con `Movimiento` (`Compra.Id_Movimiento`, `Pago_Trabajador.Id_Movimiento`) en
vez de adivinar por texto o grupo. Lo que no está vinculado a ninguna de las
dos es, por descarte, un gasto.

**Tipos de movimiento propios en vez de forzar ENTRADA/SALIDA (mejoras 7.5,
7.0/7.3):** los movimientos de dinero que no son ni venta ni compra/pago/
gasto usan su propio `Tipo_Movimiento` para no contaminar los cálculos
semanales del balance (que definen ventas como `ENTRADA` y gastos como las
`SALIDA` sin vínculo). Se agregaron `TRANSFERENCIA` (entre cuentas propias),
`INGRESO_EXTERNO` (aporte de fuera, y el desembolso de un préstamo) y
`PAGO_DEUDA` (amortización). El esquema base ya preveía `TRANSFERENCIA` en
el CHECK; `INGRESO_EXTERNO` y `PAGO_DEUDA` se agregaron por migración (010 y
012). Es el mismo principio de "categorizar sin adivinar": el tipo hace
explícita la naturaleza del movimiento en vez de deducirla.

**Saldo de deuda derivado, igual que el de una cuenta:** `Saldo_Actual_Deuda`
es un campo cacheado que refleja la suma de sus `Movimiento_Deuda`
(AUMENTO/PAGO), mismo patrón que `Saldo_Actual_Cuenta` con los `Movimiento`.
El balance ya resta `Total_Deudas`, así que registrar/pagar una deuda se
refleja solo en patrimonio y escenarios (una deuda simple baja el
patrimonio; un préstamo lo deja igual porque el efectivo que entra y el
pasivo que sube se cancelan).

**Clasificar sin adivinar por texto (mismo principio, aplicado a activos):**
la clasificación Inmueble/Equipo/Otro de los activos fijos en el balance
usaba `ilike` buscando la palabra en el nombre del tipo de bien — frágil
(un tipo llamado "Casa" no matchea "INMUEBLE"). Se reemplazó por una
columna explícita `Categoria_Tipo_Bien` en `Tipo_Bien`, elegida al crear el
tipo (ver 4.2 en MEJORAS_FUTURAS.md). Las 3 categorías están fijas porque
están ligadas 1 a 1 con columnas ya existentes en `Balance`
(`Total_Inmuebles`/`Total_Equipos`/`Total_Otros_Activos`); agregar una
categoría nueva requeriría también una migración sobre `Balance`.

---

## 5. LISTAS VALIDADAS (catálogos)

Sectores, grupos de movimiento, materias primas, productos, etc. son listas
validadas en tablas aparte. Al registrar (un cliente, un gasto), se **elige** de
la lista existente, no se escribe libre. Esto evita duplicados por variantes
("Av. Simón" vs "AV Simon"). La creación de sectores/grupos normaliza con
`ilike` + `strip` para atrapar duplicados por mayúsculas/espacios.

**Proveedores como relación, no como texto (mejora 5.1):** qué proveedor
vende qué materia prima se modela con una tabla puente
`Proveedor_Materia_Prima` (con su propio `Habilitado_*`), no con un campo
libre ni infiriéndolo del historial. Eso permite: pre-registrar a un
proveedor antes de la primera compra, deshabilitar un par concreto
(Juan-azúcar) sin afectar los demás, y que la compra ofrezca solo
proveedores válidos de esa materia. La compra **exige** proveedor (se
decidió obligar, no sugerir) para que el catálogo se llene solo; la regla
del desplegable (0 bloquea / 1 autoselecciona / >1 elige) vive en el
servicio de compras, no en el frontend.

---

## 6. MANEJO DE TIPOS EN LA FRONTERA WEB↔BD

El frontend envía números como `float` (JSON), pero la BD usa `Decimal` (numeric).
Los campos monetarios/de cantidad en los esquemas Pydantic de entrada están
tipados directo como `Decimal` (no `float`); Pydantic v2 hace la conversión
`Decimal(str(valor))` internamente al validar, el mismo criterio que evita
arrastrar el error de punto flotante, sin necesidad de convertir a mano en
cada endpoint (mejora 9.1 de `MEJORAS_FUTURAS.md`).

Además, los endpoints que crean registros con fecha usan `fecha or date.today()`:
si el frontend no envía fecha, se usa la de hoy (evita el error de NOT NULL en las
columnas de fecha). Esto es lo que permitió construir la **fecha global**
(mejora 6.10) sin tocar el backend: un contexto de React
(`componentes/FechaGlobal.jsx`) guarda una fecha opcional y cada pantalla
la manda en su POST; si no está fijada, se manda `null` y el backend cae en
el mismo `date.today()` de siempre.

**El backend es la única fuente de verdad.** El frontend duplica algunas de
sus validaciones (saldo suficiente, stock suficiente) solo como comodidad,
para avisar sin esperar el viaje al servidor — nunca reemplaza la validación
del backend, que sigue corriendo igual y es la que de verdad protege los
datos.

---

## 7. CORS Y DOS SERVIDORES

Frontend (localhost:5173) y backend (localhost:8000) corren por separado y se
comunican por HTTP. El backend habilita CORS para aceptar peticiones del frontend.
Nota de depuración: cuando un endpoint crashea (error 500), el navegador a veces
reporta "CORS" aunque la causa real sea otra — la terminal del backend es la
fuente de verdad del error.

---

## 8. VERSIONADO Y DATOS

- Control de versiones con Git desde el inicio. Se versiona el **código**, NO los
  datos (que viven en PostgreSQL) ni `node_modules` ni `.env` (credenciales).
- El diseño de la BD se hizo primero (en dbdiagram.io) antes de codear —
  "diseñar antes de construir" fue clave para avanzar rápido.
- Los datos reales del Excel se migrarán al final, con pruebas de paridad.
- Respaldos de la BD (jul 2026, mejora 8.3): tampoco viven en Git — `pg_dump`
  guarda una foto completa (no incremental, a diferencia de un commit) en
  `D:\Backups_BD_Fabrica`, un disco físico distinto al del repo. Se conservan
  todos los respaldos por ahora (pesan ~0.1 MB cada uno con los datos
  actuales) y se corren manualmente (`backend/scripts/backup_db.ps1`);
  automatizar con Task Scheduler y definir una política de retención quedan
  pendientes para cuando el tamaño real lo justifique.

---

## 9. ESTRUCTURA DEL PROYECTO

```
Git/                          (raíz del repositorio)
├── fabrica_v2_postgres.sql   (esquema base, 31 tablas)
├── DECISIONES_DISENO.md      (este archivo)
├── MEJORAS_FUTURAS.md        (mejoras para próximas versiones)
├── backend/
│   ├── .env                  (credenciales, NO versionado)
│   ├── migraciones/          (cambios incrementales a la BD, numerados)
│   ├── scripts/              (backup_db.ps1, restore_db.ps1)
│   └── app/
│       ├── database.py, models.py, dependencias.py
│       ├── config.py         (constantes de negocio ajustables)
│       ├── main.py           (ensambla la app, CORS y los routers)
│       ├── rutas/             (endpoints de la API, un archivo por dominio)
│       └── servicios/        (lógica de negocio, un archivo por área)
└── frontend/
    ├── (config de Vite, package.json, etc.)
    └── src/
        ├── App.jsx           (coordinador + rutas de React Router)
        ├── api.js            (acceso centralizado al backend)
        ├── formato.js         (fmtMoneda/fmtNumero, separador de miles)
        ├── componentes/       (piezas reutilizables: SelectorBuscable,
        │                       MenuCategoria, TablaFiltrable...)
        └── paginas/          (una pantalla por archivo)
```
