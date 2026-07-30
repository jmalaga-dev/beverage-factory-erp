# Lanzador local (Windows)

Para **usar** el sistema en el día a día, sin abrir terminales a mano.

```
Doble clic en  Fabrica V2.bat  (en la raíz del repositorio)
```

Levanta todo, abre el navegador en `http://127.0.0.1:8010` y, al cerrar la
ventana, apaga el servidor.

Para tenerlo a mano: clic derecho sobre `Fabrica V2.bat` → **Enviar a** →
**Escritorio (crear acceso directo)**. El acceso directo se puede renombrar
("Fábrica V2", con acento) y se le puede cambiar el icono; el nombre del
`.bat` no importa.

---

## Este modo NO es el de desarrollo

Son dos modos distintos y **conviven**:

| | Desarrollo | Lanzador (uso diario) |
|---|---|---|
| Cómo se arranca | dos terminales a mano | doble clic |
| Procesos | uvicorn `--reload` + Vite | **uno solo** |
| Puertos | 8000 (API) + 5173 (interfaz) | **8010** (las dos cosas) |
| Interfaz | Vite, recarga en caliente | compilada (`dist/`) |
| CORS | hace falta (dos orígenes) | no hace falta (uno solo) |
| Node corriendo | sí | no |

El puerto es 8010 y no 8000 **a propósito**, mismo criterio que los 8001/5433
del `docker-compose.yml`: el entorno de desarrollo ya ocupa el 8000. Así se
puede estar usando la app por el lanzador y programando al mismo tiempo, sin
que uno mate al otro ni haya que adivinar cuál de los dos está respondiendo.

---

## Qué hace, paso por paso

1. **Arma un grupo de procesos** (`Job Object`) para poder apagar todo al
   cerrar. Ver más abajo.
2. **Verifica PostgreSQL.** Si el servicio está detenido intenta arrancarlo
   (puede pedir permisos de administrador). También chequea que exista
   `backend\.env`.
3. **Libera el puerto** si quedó un servidor de una corrida anterior.
4. **Recompila la interfaz solo si hace falta** (ver abajo).
5. **Levanta un único proceso**: uvicorn sin `--reload`, escuchando en
   `127.0.0.1` (solo esta máquina).
6. **Espera a que responda** y abre el navegador.
7. **Se queda esperando.** Al cerrarse, apaga el servidor.

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

## Limitaciones

- **Solo Windows.** Es un `.bat` + PowerShell, y el Job Object es una API de
  Windows. Para otras máquinas está Docker (`docker/README.md`).
- **Solo esta máquina.** uvicorn escucha en `127.0.0.1`. Para que entren
  otras personas hace falta el túnel de la mejora 8.7 — no abrir el puerto.
- **Sin usuarios ni contraseñas.** Igual que el entorno de desarrollo: quien
  tiene acceso a la máquina tiene acceso al sistema.
