# Fábrica V2 en Docker

Levanta el sistema completo (base de datos + API + interfaz) sin instalar
Python, Node ni PostgreSQL por separado. Pensado para que **otra persona lo
pruebe**, no para reemplazar el entorno de desarrollo local.

> **Estado: corrido y verificado de punta a punta (jul 2026).** Con Docker
> 29.6.2, el `docker compose up --build` construye las dos imágenes y levanta
> los tres contenedores de cero: la base aplica el esquema base + las 31
> migraciones y el seed de demo, el backend responde en `/docs` y el frontend
> sirve la app con datos de ejemplo. **El modo real también está probado**, con
> un respaldo `pg_dump` de verdad: restaura, la verificación de esquema pasa
> limpia y todos los endpoints consultados responden sin un solo error de base.
> El rol `powerbi_lectura` quedó comprobado en los dos sentidos: lee, y al
> intentar escribir recibe `permission denied`. **El modo vacío** (esquema +
> migraciones, sin datos — para instalar en un cliente nuevo) también está
> probado: 40 tablas, cero filas, la API responde sin errores.

---

## Requisito

[Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y
corriendo.

## Modo demo (datos ficticios)

```bash
docker compose up --build
```

Después abrir **http://localhost:8080**.

Los datos son **inventados** (`docker/seed_demo.sql`): productos, clientes y
proveedores de fantasía, con algunas compras, una producción intermedia, una
producción terminada y una venta, para que las pantallas se vean con
contenido. No hay ninguna información del negocio real.

Para apagar:

```bash
docker compose down        # conserva la base
docker compose down -v     # borra también la base (vuelve a cero)
```

## Modo real (a partir de un respaldo)

Para que alguien evalúe el sistema con la información verdadera.

```powershell
# Windows PowerShell — la CARPETA de respaldos, no el archivo
$env:RUTA_RESPALDOS="D:\Backups_BD_Fabrica"
docker compose -f docker-compose.yml -f docker-compose.real.yml up --build
```

Toma el primer `.dump` de esa carpeta y lo restaura. Los respaldos se generan
con `backend/scripts/backup_db.ps1`.

> **Conviene que la carpeta tenga un solo `.dump`**, el que se quiera cargar.
> Si hay varios, se restaura el primero por orden de nombre, que normalmente es
> **el más viejo** (los nombres llevan la fecha).

## Modo vacío (empresa nueva, sin datos)

Esquema y migraciones aplicados, **sin** los datos ficticios de la demo ni un
respaldo de otro negocio. Para instalar el sistema en un cliente nuevo, listo
para que la primera persona empiece a cargar proveedores, productos, etc.
desde cero.

```bash
docker compose -f docker-compose.yml -f docker-compose.vacio.yml up --build
```

Después abrir **http://localhost:8080**: la app carga, todas las pantallas
responden, y todo aparece vacío (0 clientes, 0 productos) porque no hay ni un
dato cargado todavía.

Si ya se había levantado antes en otro modo (demo o real) con este mismo
volumen, hay que `docker compose down -v` primero — la base solo se
inicializa una vez, cuando el volumen está vacío.

### El respaldo tiene que ser de la misma versión del código

Un respaldo viejo restaura **sin un solo error** y deja la base aparentemente
funcionando, pero le faltan las columnas que agregaron las migraciones
posteriores. La app levanta, entra, y después tira error 500 en las pantallas
que usan esas columnas — y quien está evaluando el sistema lo ve roto sin forma
de saber que el problema es la antigüedad del respaldo.

No se arregla re-aplicando las migraciones encima: no son idempotentes (usan
`ALTER TABLE ... ADD COLUMN` sin `IF NOT EXISTS`), así que sobre un respaldo al
día fallarían todas.

Lo que hace `init/00_init.sh` es **decirlo**: después de restaurar arma en una
base descartable el esquema que el código espera (esquema base + todas las
migraciones), lo compara columna por columna contra lo restaurado, y si falta
algo lo lista con nombre y apellido:

```
!! AVISO: el respaldo es MAS VIEJO que el codigo.
!! Le faltan estas columnas, que las migraciones ya agregaron:
!!   - Venta.Taxi_Venta
!!   - Producto_Terminado.Destacado_Producto_Terminado
!!   ...
```

Es un aviso, no un corte: la base queda restaurada igual. Para verlo:
`docker compose logs db`. La solución es generar un respaldo nuevo y volver a
levantar con `docker compose down -v` primero.

> El respaldo **no se copia a la imagen ni al repositorio**: se monta al
> ejecutar, y tanto `*.dump` como `.env` están en `.gitignore` y
> `.dockerignore`. Si se comparte la imagen construida, los datos no viajan
> dentro.

Si la base ya se había inicializado antes, hay que borrar su volumen para que
vuelva a correr la carga: `docker compose down -v`.

## Qué levanta

| Servicio   | Puerto en tu máquina | Qué es                                      |
|------------|----------------------|---------------------------------------------|
| `frontend` | 8080                 | React compilado, servido por nginx           |
| `backend`  | 8001                 | API FastAPI (documentación en `/docs`)       |
| `db`       | 5433                 | PostgreSQL 18                                |

Los puertos **8001** y **5433** están corridos a propósito: el entorno de
desarrollo local ya ocupa el 8000 (uvicorn) y el 5432 (PostgreSQL instalado).
Así se pueden tener los dos prendidos a la vez sin que choquen.

## Power BI

Power BI Desktop es una aplicación de escritorio Windows: **no se puede meter
en un contenedor** (no tiene versión Linux ni licencia para eso). Lo que sí
funciona es conectarlo desde la máquina al PostgreSQL del contenedor, igual
que hoy se conecta a la base local:

- Servidor: `localhost:5433`
- Base: `fabrica`
- Usuario: `powerbi_lectura` — contraseña: la de `POWERBI_PASSWORD` en
  `docker-compose.yml`

Ese usuario **solo puede leer** (mismo criterio de mínimo privilegio de la
mejora 8.1: si el reporte falla, no puede tocar un dato). Las medidas DAX y el
armado de cada visual están en `reportes-powerbi/README.md`.

## Notas de diseño

- **La URL del backend se fija al compilar el frontend.** Vite reemplaza
  `VITE_API_URL` dentro del código en el momento del build; no se lee en
  tiempo de ejecución. Por eso va como `args` del build en el compose y, si se
  cambia, hay que reconstruir la imagen (`--build`).
- **Es `localhost:8000` y no `http://backend:8000`.** Esa URL la usa el
  *navegador*, que corre fuera de la red de Docker y no sabría resolver el
  nombre `backend`.
- **CORS se configura por variable de entorno.** El frontend se sirve desde el
  puerto 8080, que no es el 5173 de desarrollo; sin agregar ese origen, el
  navegador bloquearía todas las llamadas.
- **La base se inicializa una sola vez**, cuando su volumen está vacío. Los
  datos que cargue quien lo prueba sobreviven a un `docker compose restart`.
- **El backend corre sin `--reload`**: eso es de desarrollo. La imagen es
  inmutable; para ver un cambio de código hay que reconstruirla.
- **PostgreSQL 18, no 16.** La versión del contenedor tiene que ser **mayor o
  igual** a la del PostgreSQL de desarrollo, no solo "razonablemente nueva".
  `pg_dump 18` escribe el archivo en formato 1.16 y el `pg_restore` de una
  versión anterior no sabe leerlo: falla con `unsupported version (1.16) in
  file header`. Con la 16 el modo demo funcionaba igual (no usa respaldos), así
  que el problema solo habría aparecido el día de cargar los datos reales.
- **El volumen se monta en `/var/lib/postgresql`, no en `.../data`.** La imagen
  oficial cambió de convención en la 18: ahora los datos van en un
  subdirectorio por versión (`/var/lib/postgresql/18/docker`), para que un
  `pg_upgrade` futuro no tropiece con el límite del punto de montaje. Con el
  montaje viejo, la 18 encuentra datos donde no los espera y se niega a
  arrancar.
- **Al subir de versión mayor hay que borrar el volumen** (`docker compose down
  -v`). Un directorio de datos escrito por la 16 no lo abre la 18: eso se
  arregla con `pg_upgrade`, que necesita las dos versiones instaladas. En el
  modo demo no importa (los datos se regeneran del seed); en el modo real se
  vuelve a restaurar el respaldo, que es la fuente.
- **El backend no sirve el frontend en Docker.** `backend.Dockerfile` copia solo
  `backend/app`, así que dentro del contenedor no existe `frontend/dist` y el
  modo "un solo proceso" del lanzador local queda inactivo: acá la interfaz la
  sirve nginx, como corresponde. Ver `lanzador/README.md`.
