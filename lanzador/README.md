# Lanzador local (Windows)

Para **usar** el sistema en el día a día, sin abrir terminales a mano.

Hay **dos**, y pueden estar abiertos a la vez:

| Doble clic en | Qué levanta | Puerto | Datos |
|---|---|---|---|
| `Fabrica V2.bat` | la app de trabajo | 8010 | la base **real** |
| `Fabrica V2 (demo).bat` | para mostrar a terceros | 8011 | **ficticios**, se resetean en cada apertura |

Cada uno abre el navegador solo y, al cerrar la ventana, apaga su servidor.

Para tenerlos a mano: clic derecho sobre el `.bat` → **Enviar a** →
**Escritorio (crear acceso directo)**. El acceso directo se puede renombrar
("Fábrica V2", con acento) y se le puede cambiar el icono; el nombre del
`.bat` no importa.

**Por qué dos íconos y no un menú adentro de uno solo:** el momento de usar
el demo suele ser con alguien mirando. Un menú agrega un paso donde
equivocarse de tecla significa mostrar los datos reales del negocio. Con dos
íconos de nombre distinto no hay tecla que apretar mal.

---

## Este modo NO es el de desarrollo

Son dos modos distintos y **conviven**:

| | Desarrollo | Lanzador (uso diario) |
|---|---|---|
| Cómo se arranca | dos terminales a mano | doble clic |
| Procesos | uvicorn `--reload` + Vite | **uno solo** |
| Puertos | 8000 (API) + 5173 (interfaz) | **8010** / **8011** (las dos cosas) |
| Interfaz | Vite, recarga en caliente | compilada (`dist/`) |
| CORS | hace falta (dos orígenes) | no hace falta (uno solo) |
| Node corriendo | sí | no |

Los puertos son 8010 y 8011, no el 8000, **a propósito** — mismo criterio que
los 8001/5433 del `docker-compose.yml`: el entorno de desarrollo ya ocupa el
8000. Así se puede estar usando la app, mostrando el demo y programando al
mismo tiempo, sin que uno mate al otro ni haya que adivinar cuál de los tres
está respondiendo.

---

## Qué hace, paso por paso

1. **Arma un grupo de procesos** (`Job Object`) para poder apagar todo al
   cerrar. Ver más abajo.
2. **Verifica PostgreSQL.** Si el servicio está detenido intenta arrancarlo
   (puede pedir permisos de administrador). También chequea que exista
   `backend\.env`.
3. **Libera el puerto** si quedó un servidor de una corrida anterior.
4. **Recompila la interfaz solo si hace falta** (ver abajo).
5. *(solo el demo)* **Resetea su base de datos** a datos ficticios limpios.
6. **Levanta un único proceso**: uvicorn sin `--reload`, escuchando en
   `127.0.0.1` (solo esta máquina).
7. **Espera a que responda** y abre el navegador.
8. **Se queda esperando.** Al cerrarse, apaga el servidor.

La mecánica común vive en `_comun.ps1`; `iniciar.ps1` e `iniciar-demo.ps1`
solo dicen en qué puerto, con qué base y si hay que resetear antes.

Si algo falla, el detalle queda en `registro-errores.log` y
`registro.log` (esta carpeta). No se versionan.

---

## Por qué un solo proceso

Para *usar* la app, `--reload` y la recarga en caliente de Vite no aportan
nada: son para cuando se está escribiendo código. Compilando la interfaz una
vez y sirviéndola desde el propio backend queda **un proceso y un puerto**, y
desaparece toda la conciliación entre dos orígenes (CORS, la URL del backend
dentro del frontend, Node corriendo al lado).

El backend sirve la interfaz solo si encuentra `frontend/dist`
(`backend/app/main.py`). Si no está — el caso de desarrollo — se comporta
exactamente como siempre y solo responde la API.

### El choque de nombres entre pantallas y endpoints

Las rutas de la app se llaman **igual** que los endpoints: la pantalla de
ventas es `/ventas` y la API de ventas también. Con el frontend en su propio
puerto no hay conflicto (son dos orígenes distintos); en un solo puerto sí.

Se resuelve mirando **qué tipo de pedido es**, no la dirección: si el
navegador está *abriendo* una dirección (`Sec-Fetch-Mode: navigate` — link,
F5, marcador) recibe la interfaz; si es el `fetch()` de esa interfaz pidiendo
`/ventas`, recibe los datos. Las dos cosas conviven en la misma dirección.

Sin eso, entrar directo a `/ventas` o apretar F5 ahí devolvería el JSON crudo
de la API en vez de la pantalla.

---

## Recompilación automática

El lanzador sirve la interfaz **compilada**, así que un cambio de código no se
ve hasta recompilar. Compilar en cada arranque costaría ~20 segundos siempre;
no compilar nunca haría que un día se mire una versión vieja sin saberlo. El
criterio es: **compilar solo si hay algo nuevo.**

Se recompila si:

- no hay `frontend/dist` (primera vez),
- hay archivos en `frontend/src` (o `index.html`, `package.json`,
  `vite.config.js`) más nuevos que el compilado, **o**
- el compilado lo generó otra cosa (ver abajo).

Arranque normal: unos segundos. Después de un cambio: ~20 segundos, una sola
vez.

### Por qué la fecha no alcanza

La fecha no dice **con qué URL de backend** se compiló. Un `npm run build` a
mano —o el de Docker, que fija `localhost:8001`— deja un `dist` más nuevo que
las fuentes pero apuntando a otro puerto. El lanzador lo serviría tal cual: la
app cargaría y **ninguna pantalla traería datos**.

Por eso el lanzador deja una marca (`.compilado`) al compilar. Si la marca
falta, o si el `dist` es más nuevo que ella, recompila. La marca va **afuera**
de `dist` porque Vite lo vacía en cada build.

El valor que usa el lanzador es `VITE_API_URL=MISMO_ORIGEN`, que deja la base
de las llamadas vacía: salen relativas y pegan contra quien sirvió la página
(ver `frontend/src/api.js`).

---

## Que al cerrar la ventana se apague el servidor

En Windows, cerrar la consola **no** mata a los procesos que esa consola
lanzó. Quedarían corriendo huérfanos, invisibles, ocupando el puerto para la
próxima vez.

La solución del propio Windows es un **Job Object** con la marca
`KILL_ON_JOB_CLOSE`: un grupo de procesos que el sistema operativo termina
cuando se cierra el último handle del grupo. Como el handle lo tiene el
lanzador, muera como muera (la X, `Ctrl+C`, o hasta un `taskkill`), Windows se
encarga de matar lo que quede adentro. **No depende de que el script alcance a
ejecutar código de limpieza**, que es justamente lo que no pasa cuando se
cierra con la X.

El detalle fino: en vez de meter cada proceso hijo al grupo de a uno (dejando
una ventana de milisegundos entre lanzarlo y meterlo, donde podría quedar
huérfano), se mete **al propio lanzador**. La pertenencia al grupo se hereda,
así que todo lo que se lance después ya nace adentro. Cero carrera.

Como red de seguridad, al arrancar también se cierra lo que haya quedado
escuchando en el 8010. Es un puerto exclusivo del lanzador, así que lo que
esté ahí es de una corrida propia y nunca del entorno de desarrollo.

### El navegador queda afuera del grupo

Se abre con `explorer.exe <url>` y no lanzándolo directo. Si se lanzara
directo sería hijo del lanzador, estaría en el grupo, y al cerrar el lanzador
**se cerraría el navegador con todas las pestañas del usuario**. `explorer.exe`
ya está corriendo: recibe la URL y abre el navegador desde su propio árbol de
procesos, afuera del grupo.

---

## El lanzador de demo

Existe para **mostrar el sistema sin exponer un solo dato del negocio**: a un
cliente, en una entrevista, o para dejarlo accesible un rato por un túnel.

**No reusa `fabrica_V2_pruebas`**, aunque el nombre lo sugiera. Esa base es
una *copia de la real* (se verificó: mismos clientes, mismas ventas), no
datos ficticios — mostrarla filtraría nombres y números verdaderos. El demo
usa una base propia, `fabrica_V2_demo`, con los mismos datos inventados que
el modo demo de Docker (`docker/seed_demo.sql`): "Cliente Uno Demo",
productos de fantasía, unas compras y una venta.

### Se resetea en cada apertura

Cada doble clic borra `fabrica_V2_demo` y la reconstruye de cero: esquema +
migraciones + datos ficticios. Lo que haya tocado (o roto) quien vio la demo
anterior no se arrastra a la siguiente, sin que haya que acordarse de
limpiar nada.

El reseteo corre **antes** de levantar el servidor. Si falla, el servidor no
arranca — no queda un demo a medias.

Se puede correr suelto, para dejarlo listo de antemano sin abrir el
navegador:

```
powershell -File lanzador\resetear-demo.ps1
```

### Un usuario de base de datos aparte, sin acceso a lo real

La app normalmente se conecta como `postgres`, el **superusuario** de todo
el servidor PostgreSQL. Para el demo eso sería demasiado: si el demo queda
expuesto por un túnel, quien entre estaría operando con el usuario más
poderoso de la instalación.

El demo se conecta con `fabrica_demo_local`, un rol que solo tiene permisos
sobre `fabrica_V2_demo`. Comprobado con esas credenciales contra la base
real: no puede leer un solo dato (`permiso denegado a la tabla ...`) y
`information_schema` no le muestra ni un nombre de tabla, porque esa vista
filtra por privilegios.

> **Matiz, para no prometer de más:** ese rol *sí puede abrir una conexión* a
> la base real — PostgreSQL le da `CONNECT` a `PUBLIC` por defecto en toda
> base, y no existe un "denegar" por rol. Cortarlo requeriría
> `REVOKE CONNECT ON DATABASE "fabrica_V2" FROM PUBLIC`, que afecta a **todos**
> los roles (incluido `powerbi_lectura`) y por eso no se hace automáticamente:
> es una decisión sobre la base real, no sobre el demo. La protección efectiva
> es la de tablas — conecta, pero no ve absolutamente nada.

La contraseña del rol se genera sola la primera vez y queda en
`backend/.env.demo`, que **no se versiona**.

### Sobre exponerlo por un túnel

El túnel de Cloudflare apunta a **un puerto**. Mientras el túnel apunte al
8010 (el real), el demo del 8011 no está expuesto en absoluto. Si en cambio
se quiere mostrar el demo por internet, se arma un túnel al 8011 — y ahí sí
conviene decidir si lleva Cloudflare Access o no, sabiendo que sin Access
cualquiera con el link entra (pero solo a datos ficticios que se borran en la
próxima apertura).

## Limitaciones

- **Solo Windows.** Es un `.bat` + PowerShell, y el Job Object es una API de
  Windows. Para otras máquinas está Docker (`docker/README.md`).
- **Solo esta máquina.** uvicorn escucha en `127.0.0.1`. Para que entren
  otras personas hace falta el túnel de la mejora 8.7 — no abrir el puerto.
- **Sin usuarios ni contraseñas.** Igual que el entorno de desarrollo: quien
  tiene acceso a la máquina tiene acceso al sistema.
