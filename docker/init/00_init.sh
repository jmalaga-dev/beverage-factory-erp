#!/bin/bash
# Inicializacion de la base dentro del contenedor de PostgreSQL.
#
# La imagen oficial de postgres ejecuta lo que haya en
# /docker-entrypoint-initdb.d/ UNA sola vez: la primera vez que el volumen de
# datos esta vacio. En arranques posteriores no se vuelve a correr, asi que
# los datos que cargue la persona no se pisan al reiniciar.
#
# Tres modos, segun la variable MODO_DATOS:
#   demo (por defecto) -> esquema + migraciones + datos FICTICIOS
#   vacio              -> esquema + migraciones, SIN datos (para empezar de cero)
#   real               -> restaura un pg_dump montado desde afuera
#
# El modo `real` existe para que alguien pruebe el sistema con los datos
# verdaderos del negocio. Ese dump se monta al ejecutar y NUNCA se copia a la
# imagen ni al repositorio (ver docker/README.md).
#
# El modo `vacio` existe para instalar el sistema en una empresa nueva, sin
# arrastrar ni los datos ficticios de la demo ni un respaldo de otro negocio:
# solo el esquema, listo para que la primera persona empiece a cargar.

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

  # ---------- Verificar que el respaldo este al dia con el codigo ----------
  # Un respaldo viejo restaura sin un solo error y deja la base "funcionando",
  # pero le faltan las columnas que agregaron las migraciones posteriores. La
  # app arranca, entra, y despues tira 500 en las pantallas que usan esas
  # columnas. Quien lo esta evaluando ve el sistema roto y no tiene forma de
  # saber que el problema es la antiguedad del respaldo.
  #
  # No se puede arreglar re-aplicando las migraciones encima: no son
  # idempotentes (usan ALTER TABLE ... ADD COLUMN sin IF NOT EXISTS), asi que
  # sobre un respaldo al dia fallarian todas. Lo que si se puede es DECIRLO.
  #
  # Se arma en una base descartable el esquema que el codigo espera (base +
  # migraciones) y se compara columna por columna contra lo restaurado.
  echo ">> Verificando que el respaldo coincida con el codigo"
  COLUMNAS="SELECT table_name || '.' || column_name FROM information_schema.columns WHERE table_schema = 'public'"

  # Cada paso corta con `|| return 1`: al invocarse dentro de un `if`, bash
  # suspende el `set -e` para todo el cuerpo de la funcion, asi que sin esto
  # un fallo intermedio pasaria desapercibido y la comparacion se haria contra
  # un esquema de referencia incompleto (= avisos falsos).
  verificar_esquema() {
    createdb --username "$POSTGRES_USER" esquema_esperado || return 1

    psql -q -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
      --dbname esquema_esperado -f /sql/00_schema.sql || return 1
    for f in $(ls /sql/migraciones/*.sql | sort); do
      psql -q -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
        --dbname esquema_esperado -f "$f" || return 1
    done

    psql -At --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      -c "$COLUMNAS" | sort > /tmp/restaurado.txt || return 1
    psql -At --username "$POSTGRES_USER" --dbname esquema_esperado \
      -c "$COLUMNAS" | sort > /tmp/esperado.txt || return 1

    # Descartable por definicion: solo existio para tener con que comparar.
    dropdb --username "$POSTGRES_USER" esquema_esperado || return 1
  }

  if verificar_esquema; then
    # `grep -Fxv -f A B` = lineas de B que no estan en A (comparacion literal,
    # linea completa). `comm` seria mas directo pero no esta garantizado en la
    # imagen alpine; grep si.
    FALTANTES=$(grep -Fxv -f /tmp/restaurado.txt /tmp/esperado.txt || true)
    if [ -n "$FALTANTES" ]; then
      echo "!!" >&2
      echo "!! ================================================================" >&2
      echo "!! AVISO: el respaldo es MAS VIEJO que el codigo." >&2
      echo "!!" >&2
      echo "!! Le faltan estas columnas, que las migraciones ya agregaron:" >&2
      echo "$FALTANTES" | sed 's/^/!!   - /' >&2
      echo "!!" >&2
      echo "!! La app va a levantar, pero las pantallas que usen esas columnas" >&2
      echo "!! van a dar error 500. Solucion: generar un respaldo NUEVO de la" >&2
      echo "!! base de desarrollo (backend/scripts/respaldar.bat) y volver a" >&2
      echo "!! levantar con 'docker compose down -v' primero." >&2
      echo "!! ================================================================" >&2
      echo "!!" >&2
    else
      echo ">> Esquema al dia: el respaldo tiene todo lo que el codigo espera."
    fi
  else
    # Que falle la verificacion no invalida la restauracion, que ya termino
    # bien. Se avisa y se sigue.
    echo "!! No se pudo verificar el esquema. La base quedo restaurada igual." >&2
  fi
else
  # ---------- MODO DEMO y MODO VACIO comparten esquema + migraciones ----------
  echo ">> Esquema base"
  psql_ -f /sql/00_schema.sql

  echo ">> Migraciones"
  # En orden numerico: cada una asume que las anteriores ya corrieron.
  for f in $(ls /sql/migraciones/*.sql | sort); do
    echo "   - $(basename "$f")"
    psql_ -f "$f"
  done

  if [ "${MODO_DATOS:-demo}" = "vacio" ]; then
    # ---------- MODO VACIO: nada mas. Listo para cargar de cero. ----------
    echo ">> Base vacia: sin datos ficticios ni respaldo, lista para usar."
  else
    # ---------- MODO DEMO: datos inventados encima ----------
    echo ">> Datos ficticios de demostracion"
    psql_ -f /sql/seed_demo.sql
  fi
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
