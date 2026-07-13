# Restaura la base de datos fabrica_V2 desde un archivo de respaldo (mejora 8.3)
# Uso:
#   powershell -File backend\scripts\restore_db.ps1 -Archivo "D:\Backups_BD_Fabrica\fabrica_V2_20260712_080000.dump"
#
# ADVERTENCIA: reemplaza (--clean) el contenido actual de la base con el del
# respaldo elegido. Pide confirmacion explicita antes de tocar nada.

param(
    [Parameter(Mandatory = $true)]
    [string]$Archivo
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Archivo)) {
    throw "No se encontro el archivo: $Archivo"
}

$envPath = Join-Path $PSScriptRoot "..\.env"
$envVars = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
        $envVars[$matches[1]] = $matches[2]
    }
}

$pgRestore = "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"
if (-not (Test-Path $pgRestore)) {
    $pgRestore = (Get-Command pg_restore -ErrorAction SilentlyContinue).Source
}
if (-not $pgRestore) {
    throw "No se encontro pg_restore. Revisa la instalacion de PostgreSQL."
}

Write-Host "Esto va a REEMPLAZAR el contenido actual de '$($envVars['DB_NAME'])' con el respaldo:"
Write-Host "  $Archivo"
$confirmacion = Read-Host "Escribi 'si' para continuar"
if ($confirmacion -ne "si") {
    Write-Host "Cancelado."
    exit
}

$env:PGPASSWORD = $envVars["DB_PASSWORD"]
try {
    & $pgRestore `
        -h $envVars["DB_HOST"] `
        -p $envVars["DB_PORT"] `
        -U $envVars["DB_USER"] `
        -d $envVars["DB_NAME"] `
        --clean --if-exists `
        $Archivo
} finally {
    Remove-Item Env:\PGPASSWORD
}

Write-Host "Restauracion completada."
