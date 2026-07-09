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
    (libro de movimientos único); de Cuenta solo se edita el nombre.
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
trabajador (`Pago_Trabajador`), no con el pago real semanal.

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

---

## 4. FLUJO DE OPERACIONES (patrón de los servicios)

Cada servicio de negocio sigue el patrón: **validar TODO antes de tocar nada** →
ejecutar de forma atómica (try/commit) → rollback si algo falla. Esto garantiza
que operaciones que afectan varias tablas (dinero + inventario) pasen completas o
no pasen (integridad).

Operaciones construidas (con backend, API y pantalla):
- Compra de materia prima (valida saldo, crea movimiento SALIDA, descuenta cuenta).
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

**Categorizar una SALIDA sin adivinar:** para separar compras / pagos a
trabajadores / gastos dentro de los movimientos de dinero (todos
`Tipo_Movimiento = "SALIDA"`), se usa el vínculo real que cada tabla ya tiene
con `Movimiento` (`Compra.Id_Movimiento`, `Pago_Trabajador.Id_Movimiento`) en
vez de adivinar por texto o grupo. Lo que no está vinculado a ninguna de las
dos es, por descarte, un gasto.

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

---

## 6. MANEJO DE TIPOS EN LA FRONTERA WEB↔BD

El frontend envía números como `float` (JSON), pero la BD usa `Decimal` (numeric).
Los campos monetarios/de cantidad en los esquemas Pydantic de entrada están
tipados directo como `Decimal` (no `float`); Pydantic v2 hace la conversión
`Decimal(str(valor))` internamente al validar, el mismo criterio que evita
arrastrar el error de punto flotante, sin necesidad de convertir a mano en
cada endpoint (mejora 8.1/9 de `MEJORAS_FUTURAS.md`).

Además, los endpoints que crean registros con fecha usan `fecha or date.today()`:
si el frontend no envía fecha, se usa la de hoy (evita el error de NOT NULL en las
columnas de fecha).

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
