# Fábrica V2 en Docker

Levanta el sistema completo (base de datos + API + interfaz) sin instalar
Python, Node ni PostgreSQL por separado. Pensado para que **otra persona lo
pruebe**, no para reemplazar el entorno de desarrollo local.

> **Estado: probado y funcionando.** El `docker compose up --build` levanta los
> tres contenedores de cero (Docker 29 / Compose v5): la base aplica el esquema
> base + las migraciones y el seed de demo, el backend responde en `/docs` y el
> frontend sirve la app con datos de ejemplo. También está verificado contra
> PostgreSQL real que el esquema + migraciones producen un esquema **idéntico**
> al de producción (226 columnas, cero diferencias).

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
| `db`       | 5433                 | PostgreSQL 16                                |

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
