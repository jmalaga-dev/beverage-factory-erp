# Respaldo manual de la base de datos fabrica_V2 (mejora 8.3)
# Uso (desde cualquier carpeta):
#   powershell -File backend\scripts\backup_db.ps1
#
# Genera un dump con pg_dump en formato "custom" (comprimido) con fecha y hora
# en el nombre, y lo guarda en D:\Backups_BD_Fabrica. No borra respaldos
# anteriores: la limpieza/retencion se decide mas adelante, cuando se sepa
# cuanto pesan en la practica.

$ErrorActionPreference = "Stop"

$envPath = Join-Path $PSScriptRoot "..\.env"
$envVars = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
        $envVars[$matches[1]] = $matches[2]
    }
}

$pgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    $pgDump = (Get-Command pg_dump -ErrorAction SilentlyContinue).Source
}
if (-not $pgDump) {
    throw "No se encontro pg_dump. Revisa la instalacion de PostgreSQL."
}

$destino = "D:\Backups_BD_Fabrica"
if (-not (Test-Path $destino)) {
    New-Item -ItemType Directory -Path $destino | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archivo = Join-Path $destino "fabrica_V2_$timestamp.dump"

$env:PGPASSWORD = $envVars["DB_PASSWORD"]
try {
    & $pgDump `
        -h $envVars["DB_HOST"] `
        -p $envVars["DB_PORT"] `
        -U $envVars["DB_USER"] `
        -F c `
        -f $archivo `
        $envVars["DB_NAME"]
} finally {
    Remove-Item Env:\PGPASSWORD
}

$tamanoMB = [math]::Round((Get-Item $archivo).Length / 1MB, 2)
Write-Host "Respaldo creado: $archivo ($tamanoMB MB)"
