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

---

## 3. INVENTARIO Y PRODUCCIÓN

### 3.1 FIFO automático (primero en entrar, primero en salir)
En vez de que el usuario elija lote a lote qué consumir, el sistema descontaría
automáticamente de los lotes más antiguos primero. El usuario diría "usé 5 kg de
azúcar" y el sistema resuelve de qué lotes. Simplifica mucho la experiencia.
Cambio de lógica en el backend (los servicios hoy reciben el lote explícito).

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

### 4.3 Patrimonio contable puro
Actualmente Patrimonio = Escenario A. Se podría distinguir un patrimonio contable
(activos a valor real) de los escenarios de liquidez.

### 4.4 Informe comparativo entre balances
Generar automáticamente un reporte que compare dos fotos de balance semanales y
resalte qué cambió (costos, patrimonio, stock). Relevante dado que se eligió
Filosofía B para el costo de materia prima.

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

---

## 5. PROVEEDORES

### 5.1 Base de datos de proveedores
Agregar tabla `Proveedor` y un `Id_Proveedor` en `Compra`, para comparar precios
de la misma materia prima entre proveedores y decidir cuál conviene.

---

## 6. UX / UI (todas para después de completar la funcionalidad)

### 6.1 Operaciones de edición (PUT/PATCH) y borrado
El sistema actual solo tiene crear (POST) y leer (GET). Falta poder editar y
borrar registros (clientes, catálogos, jornadas, etc.). Es lo que en una API REST
completa serían los métodos PUT/PATCH/DELETE.

**Nota (aún no implementado en general):** ya hay 3 precedentes puntuales de
PATCH/DELETE, cada uno acotado a su caso, no una solución genérica:
`PATCH /trabajadores/{id}/habilitado` (6.5), `PATCH`/`DELETE /jornadas/{id}`
con guardrail de "intacta" (3.4), y `PATCH`/`DELETE /activos/{id}` (7.2). Ver
la decisión "PATCH acotado, no edición genérica" en DECISIONES_DISENO.md.
Sirven de referencia de patrón si se ataca esto en general.

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

---

## 7. MÓDULOS CON BACKEND PERO SIN PANTALLA (o parciales)

### 7.0 Deudas y amortización
El sistema tiene tablas de Deuda y Movimiento_Deuda en el diseño, pero no hay
pantalla para gestionarlas. Falta: registrar deudas, amortizarlas (con la lógica
de reparto por prioridad de cuentas, ver sección 2), y verlas reflejadas en el
balance. Es parte del flujo financiero completo.

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

### 7.4 Columnas de balance para fotos históricas
Ya se agregaron Valor_Stock_Intermedio y Valor_Horas_Standby al balance (migración
003). Si se agregan más conceptos al balance en el futuro, recordar: agregarlos
como columnas para que las fotos históricas los guarden y la comparación temporal
sea completa.

---

## 8. INTEGRACIONES Y DESPLIEGUE

### 7.1 Power BI conectado a PostgreSQL
Para reportería avanzada sin construir todo el frontend de reportes. Conectar
Power BI directamente a la base para dashboards.

### 7.2 Google Maps API
Para los sectores/zonas de clientes: mostrar clientes en un mapa, análisis de
ventas por zona. Ya se guardan latitud/longitud (con extracción desde link de Maps).

### 7.3 Respaldos automáticos (pg_dump)
Los datos viven en PostgreSQL, NO en Git. Git no los protege. Configurar respaldos
periódicos con `pg_dump` antes de manejar datos reales del negocio, para no
perderlos ante una falla de disco.

### 7.4 Migración de datos reales del Excel
Al final, cuando el sistema esté probado, migrar los 3 archivos de Excel con los
datos históricos reales, con pruebas de paridad contra el Excel.

### 7.5 Subir el repositorio a GitHub
Actualmente el versionado es local. Subir a GitHub cuando haya una beta, con el
README y la documentación, para que el repositorio sea visible (útil para CV).

---

## 9. TIPOS Y VALIDACIONES

### 8.1 Conversión Decimal automática en Pydantic
Actualmente cada endpoint convierte float→Decimal a mano con `Decimal(str(...))`.
Se podría configurar Pydantic para que los campos monetarios sean Decimal
automáticamente, evitando repetir la conversión en cada endpoint.

### 8.2 Validación en frontend (comodidad)
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
