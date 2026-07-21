#!/bin/bash
# Inicializacion de la base dentro del contenedor de PostgreSQL.
#
# La imagen oficial de postgres ejecuta lo que haya en
# /docker-entrypoint-initdb.d/ UNA sola vez: la primera vez que el volumen de
# datos esta vacio. En arranques posteriores no se vuelve a correr, asi que
# los datos que cargue la persona no se pisan al reiniciar.
#
# Dos modos, segun la variable MODO_DATOS:
#   demo (por defecto) -> esquema + migraciones + datos FICTICIOS
#   real               -> restaura un pg_dump montado desde afuera
#
# El modo `real` existe para que alguien pruebe el sistema con los datos
# verdaderos del negocio. Ese dump se monta al ejecutar y NUNCA se copia a la
# imagen ni al repositorio (ver docker/README.md).

set -euo pipefail

psql_() {
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$@"
}

echo ">> Modo de datos: ${MODO_DATOS:-demo}"

if [ "${MODO_DATOS:-demo}" = "real" ]; then
  # ---------- MODO REAL: restaurar un respaldo ----------
  DUMP=$(ls /dump/*.dump 2>/dev/null | head -1 || true)
  if [ -z "$DUMP" ]; then
    echo "!! MODO_DATOS=real pero no hay ningun .dump en /dump" >&2
    echo "!! Monta tu respaldo con:  -v /ruta/a/respaldos:/dump:ro" >&2
    exit 1
  fi
  echo ">> Restaurando $DUMP"
  # El dump trae el esquema completo y los datos: no se aplican migraciones
  # encima (ya vienen aplicadas en el respaldo).
  pg_restore --no-owner --no-privileges \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$DUMP"
else
  # ---------- MODO DEMO: esquema limpio + datos inventados ----------
  echo ">> Esquema base"
  psql_ -f /sql/00_schema.sql

  echo ">> Migraciones"
  # En orden numerico: cada una asume que las anteriores ya corrieron.
  for f in $(ls /sql/migraciones/*.sql | sort); do
    echo "   - $(basename "$f")"
    psql_ -f "$f"
  done

  echo ">> Datos ficticios de demostracion"
  psql_ -f /sql/seed_demo.sql
fi

# ---------- Rol de solo lectura para Power BI (mejora 8.1) ----------
# Power BI Desktop es una aplicacion Windows: NO corre en un contenedor. Lo
# que se hace es dejar la base accesible para que se conecte desde el equipo
# anfitrion, con un usuario que solo puede leer (si el reporte falla, no
# puede tocar un dato).
if [ -n "${POWERBI_PASSWORD:-}" ]; then
  echo ">> Creando rol powerbi_lectura"
  psql_ <<-EOSQL
    CREATE ROLE powerbi_lectura LOGIN PASSWORD '${POWERBI_PASSWORD}';
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO powerbi_lectura;
    GRANT USAGE ON SCHEMA public TO powerbi_lectura;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_lectura;
    -- Para que las tablas de migraciones futuras tambien le queden visibles
    -- sin repetir el GRANT a mano.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT SELECT ON TABLES TO powerbi_lectura;
EOSQL
fi

echo ">> Base lista."
