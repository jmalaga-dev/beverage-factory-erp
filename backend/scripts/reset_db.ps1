# Vacia TODAS las tablas de la base de datos (deja el esquema intacto).
# Uso: powershell -File backend\scripts\reset_db.ps1
#
# Pensado para probar el ciclo completo respaldo -> vaciar -> restaurar
# mientras la base solo tiene datos de prueba (jul 2026). NO correr esto una
# vez que haya datos reales del negocio sin antes tener un backup_db.ps1
# reciente a mano.
#
# ADVERTENCIA: TRUNCATE ... CASCADE sobre todas las tablas del esquema
# "public" y reinicio de los ids (RESTART IDENTITY). Pide confirmacion
# escribiendo el nombre de la base antes de tocar nada.

$ErrorActionPreference = "Stop"

$envPath = Join-Path $PSScriptRoot "..\.env"
$envVars = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
        $envVars[$matches[1]] = $matches[2]
    }
}

$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path $psql)) {
    $psql = (Get-Command psql -ErrorAction SilentlyContinue).Source
}
if (-not $psql) {
    throw "No se encontro psql. Revisa la instalacion de PostgreSQL."
}

$nombreBD = $envVars["DB_NAME"]

Write-Host "Esto va a BORRAR TODOS LOS DATOS de todas las tablas de '$nombreBD' (el esquema queda intacto)."
Write-Host "Si te importa lo que hay ahora, corre backup_db.ps1 antes de seguir."
$confirmacion = Read-Host "Escribi el nombre de la base ('$nombreBD') para confirmar"
if ($confirmacion -ne $nombreBD) {
    Write-Host "Cancelado."
    exit
}

$sql = @'
DO $$
DECLARE
    tablas text;
BEGIN
    SELECT string_agg(quote_ident(schemaname) || '.' || quote_ident(tablename), ', ')
    INTO tablas
    FROM pg_tables
    WHERE schemaname = 'public';
    IF tablas IS NOT NULL THEN
        EXECUTE 'TRUNCATE TABLE ' || tablas || ' RESTART IDENTITY CASCADE';
    END IF;
END
$$;
'@

$env:PGPASSWORD = $envVars["DB_PASSWORD"]
try {
    & $psql -h $envVars["DB_HOST"] -p $envVars["DB_PORT"] -U $envVars["DB_USER"] -d $nombreBD -c $sql
} finally {
    Remove-Item Env:\PGPASSWORD
}

Write-Host "Listo: todas las tablas quedaron vacias (ids reiniciados)."
