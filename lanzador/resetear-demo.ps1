# =============================================================================
# Resetea la base de datos del lanzador de demo (fabrica_V2_demo).
#
# Se ejecuta SIEMPRE que se abre "Fabrica V2 (demo).bat", antes de levantar
# el servidor: borra la base de demo si existia y la vuelve a crear desde
# cero con esquema + migraciones + datos FICTICIOS (docker/seed_demo.sql,
# el mismo seed que usa el modo demo de Docker). Asi cada apertura arranca
# prolija, sin arrastrar lo que haya tocado una demo anterior.
#
# Por que una base y un rol de PostgreSQL APARTE, y no reusar
# fabrica_V2_pruebas: esa base es una COPIA restaurada de un respaldo real
# (verificado antes de armar esto: mismo contenido que la base real, no
# datos ficticios). Mostrarsela a alguien filtraria nombres y numeros reales
# del negocio. El demo necesita una base con datos inventados, separada de
# la real y de la de pruebas.
#
# El rol `fabrica_demo_local` que usa el proceso de uvicorn en este modo NO
# es el superusuario `postgres` de siempre: no tiene NINGUN privilegio sobre
# las tablas de fabrica_V2 (la real) ni de fabrica_V2_pruebas. Verificado
# con esas credenciales: contra la base real no puede leer un solo dato
# ("permiso denegado a la tabla ...") y `information_schema` no le muestra
# ni un nombre de tabla, porque esa vista filtra por privilegios.
#
# Matiz importante, para no prometer de mas: el rol SI puede abrir una
# conexion a la base real. PostgreSQL le da CONNECT a PUBLIC por defecto en
# toda base, y no existe un "denegar" por rol: la unica forma de cortarlo
# seria `REVOKE CONNECT ON DATABASE "fabrica_V2" FROM PUBLIC`, que afecta a
# TODOS los roles (incluido powerbi_lectura) y por eso no se hace desde
# aca — es una decision sobre la base real, no sobre el demo. La proteccion
# efectiva es la de tablas: conecta, pero no ve absolutamente nada.
#
# No se ejecuta directo normalmente: lo llama iniciar-demo.ps1 antes de
# levantar el servidor. Se puede correr suelto para resetear el demo sin
# abrir el navegador (por ejemplo, para dejarlo listo de antemano):
#   powershell -File lanzador\resetear-demo.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# Escribe SQL a un archivo temporal en UTF-8 SIN BOM y devuelve la ruta.
#
# El "sin BOM" no es cosmetico. `Set-Content -Encoding utf8` en Windows
# PowerShell 5.1 escribe un BOM (los bytes EF BB BF al principio), y psql
# solo lo ignora si su codificacion de cliente resulta ser UTF8. En una
# consola en espanol (codepage 850/1252, que es lo normal al hacer doble
# clic en el .bat) psql interpreta esos tres bytes como los caracteres
# "i>>?" y los pega al primer comando, con lo que el archivo entero falla:
#
#   ERROR: error de sintaxis en o cerca de <<i>>?DO>>
#
# Es un error que aparece o no segun el idioma/codepage de Windows, asi que
# escribiendo sin BOM el script funciona igual en cualquier maquina. El
# `$false` del constructor es justamente "no emitir BOM".
function Escribir-SqlTemporal($sql) {
    $ruta = [System.IO.Path]::GetTempFileName() + ".sql"
    [System.IO.File]::WriteAllText($ruta, $sql, (New-Object System.Text.UTF8Encoding $false))
    return $ruta
}

function Resetear-BaseDemo {
    $RaizRepo = Split-Path -Parent $PSScriptRoot
    $RutaBackend = Join-Path $RaizRepo "backend"

    $NombreBaseDemo = "fabrica_V2_demo"
    $NombreRolDemo = "fabrica_demo_local"

    # ---------- Credenciales de superusuario, para poder crear la base y el rol ----------
    $envPath = Join-Path $RutaBackend ".env"
    if (-not (Test-Path $envPath)) {
        throw "Falta backend\.env: hace falta para saber con que superusuario administrar PostgreSQL."
    }
    $envVars = @{}
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') { $envVars[$matches[1]] = $matches[2] }
    }

    # ---------- Ubicar las herramientas de linea de comandos de PostgreSQL ----------
    # Mismo criterio que backend/scripts/backup_db.ps1 y restore_db.ps1: primero
    # la ruta tipica de una instalacion en Windows, si no esta se busca en el PATH.
    function Ubicar-Herramienta($nombre) {
        $ruta = "C:\Program Files\PostgreSQL\18\bin\$nombre.exe"
        if (Test-Path $ruta) { return $ruta }
        $enPath = (Get-Command $nombre -ErrorAction SilentlyContinue).Source
        if ($enPath) { return $enPath }
        throw "No se encontro $nombre. Revisa la instalacion de PostgreSQL."
    }
    $psql = Ubicar-Herramienta "psql"
    $createdb = Ubicar-Herramienta "createdb"
    $dropdb = Ubicar-Herramienta "dropdb"

    $argsConexion = @("-h", $envVars["DB_HOST"], "-p", $envVars["DB_PORT"], "-U", $envVars["DB_USER"])

    $env:PGPASSWORD = $envVars["DB_PASSWORD"]
    try {
        Escribir "  Reseteando la base de demo..." "Gray"

        # ---------- Recrear la base de cero ----------
        # `dropdb`/`createdb` (los ejecutables, no sentencias SQL sueltas) toman
        # el nombre tal cual y lo entrecomillan al armar el SQL internamente, asi
        # se preserva la mayuscula de la V exacta. Escribiendo "CREATE DATABASE
        # fabrica_V2_demo" a mano sin comillas, Postgres pliega el nombre a
        # minusculas por default y quedaria una base distinta
        # ("fabrica_v2_demo") a la que despues nadie apunta.
        #
        # --force (dropdb) = DROP DATABASE ... WITH (FORCE): corta cualquier
        # conexion que haya quedado abierta (ej. un demo anterior que no cerro
        # bien) en vez de fallar por "database is being accessed by other users".
        & $dropdb --if-exists --force @argsConexion $NombreBaseDemo
        if ($LASTEXITCODE -ne 0) { throw "No se pudo borrar la base de demo anterior." }

        & $createdb @argsConexion $NombreBaseDemo
        if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la base de demo." }

        # ---------- Esquema + migraciones + datos ficticios ----------
        # Mismas fuentes que el modo demo de Docker (docker/init/00_init.sh):
        # el esquema base, las migraciones en orden numerico, y el seed
        # inventado. Asi el demo local y el demo de Docker muestran
        # exactamente los mismos datos ficticios.
        $argsDemo = $argsConexion + @("-v", "ON_ERROR_STOP=1", "-q", "-d", $NombreBaseDemo)

        & $psql @argsDemo -f (Join-Path $RaizRepo "fabrica_v2_postgres.sql")
        if ($LASTEXITCODE -ne 0) { throw "Fallo al aplicar el esquema base." }

        $migraciones = Get-ChildItem (Join-Path $RutaBackend "migraciones\*.sql") | Sort-Object Name
        foreach ($migracion in $migraciones) {
            & $psql @argsDemo -f $migracion.FullName
            if ($LASTEXITCODE -ne 0) { throw "Fallo la migracion $($migracion.Name)." }
        }

        & $psql @argsDemo -f (Join-Path $RaizRepo "docker\seed_demo.sql")
        if ($LASTEXITCODE -ne 0) { throw "Fallo al cargar los datos ficticios de demo." }

        # ---------- Rol acotado: solo fabrica_V2_demo, nunca la real ni la de pruebas ----------
        # La contrasena se genera UNA vez y se guarda en backend\.env.demo
        # (gitignored, ver .gitignore: backend/.env.*). En las siguientes
        # aperturas se reusa la misma, asi el rol no cambia de clave en cada
        # reset — solo cambian los datos que contiene la base.
        $envDemoPath = Join-Path $RutaBackend ".env.demo"
        $passwordRol = $null
        if (Test-Path $envDemoPath) {
            $envDemoVars = @{}
            Get-Content $envDemoPath | ForEach-Object {
                if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') { $envDemoVars[$matches[1]] = $matches[2] }
            }
            $passwordRol = $envDemoVars["DB_PASSWORD"]
        }
        if (-not $passwordRol) {
            # Solo alfanumericos: esta clave se interpola directo en SQL mas
            # abajo (dentro de un bloque DO), y un caracter como una comilla
            # simple rompería esa sentencia. No hace falta mas que eso: el rol
            # solo es alcanzable desde localhost, sobre datos ficticios.
            $passwordRol = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
        }

        # ---------- Crear/actualizar el rol y sus permisos (conectado a la base de mantenimiento) ----------
        $sqlRol = @"
DO `$`$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$NombreRolDemo') THEN
      CREATE ROLE $NombreRolDemo LOGIN PASSWORD '$passwordRol';
   ELSE
      ALTER ROLE $NombreRolDemo WITH LOGIN PASSWORD '$passwordRol';
   END IF;
END
`$`$;
GRANT CONNECT ON DATABASE "$NombreBaseDemo" TO $NombreRolDemo;
"@
        # Se escribe a un archivo temporal y se corre con -f, en vez de pasar
        # el SQL como argumento -c: un argumento con comillas dobles adentro
        # (las que preservan mayusculas en "fabrica_V2_demo") es fragil al
        # pasarlo a un ejecutable nativo desde PowerShell. Un archivo evita
        # por completo ese problema de escapado.
        $archivoTemp = Escribir-SqlTemporal $sqlRol
        try {
            & $psql @argsConexion -v ON_ERROR_STOP=1 -q -d postgres -f $archivoTemp
            if ($LASTEXITCODE -ne 0) { throw "Fallo al crear/actualizar el rol de demo." }
        } finally {
            Remove-Item $archivoTemp -ErrorAction SilentlyContinue
        }

        # ---------- Permisos DENTRO de fabrica_V2_demo (schema, tablas, secuencias) ----------
        # SELECT/INSERT/UPDATE/DELETE: quien entra al demo tiene que poder
        # cargar clientes, ventas, etc. de verdad, no solo mirar. Nada de DDL
        # (crear/alterar tablas): eso queda reservado al superusuario que
        # corre las migraciones.
        # ALTER DEFAULT PRIVILEGES: para que una migracion futura que agregue
        # una tabla no requiera acordarse de otorgarle permiso a mano (mismo
        # criterio que el rol powerbi_lectura en docker/init/00_init.sh).
        $sqlPermisos = @"
GRANT USAGE ON SCHEMA public TO $NombreRolDemo;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $NombreRolDemo;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $NombreRolDemo;
"@
        $archivoTemp2 = Escribir-SqlTemporal $sqlPermisos
        try {
            & $psql @argsDemo -f $archivoTemp2
            if ($LASTEXITCODE -ne 0) { throw "Fallo al otorgar permisos dentro de la base de demo." }
        } finally {
            Remove-Item $archivoTemp2 -ErrorAction SilentlyContinue
        }

        # ---------- Guardar/confirmar backend\.env.demo ----------
        if (-not (Test-Path $envDemoPath)) {
            $contenidoEnvDemo = @"
# Generado automaticamente por lanzador\resetear-demo.ps1 -- no editar a mano.
# Credenciales del rol acotado de la base de demo. Nunca se versiona (ver
# .gitignore: backend/.env.*). Solo alcanza fabrica_V2_demo: no puede tocar
# fabrica_V2 (la real) ni fabrica_V2_pruebas.
DB_HOST=$($envVars["DB_HOST"])
DB_PORT=$($envVars["DB_PORT"])
DB_NAME=$NombreBaseDemo
DB_USER=$NombreRolDemo
DB_PASSWORD=$passwordRol
"@
            Set-Content -Path $envDemoPath -Value $contenidoEnvDemo -Encoding utf8
        }

        Escribir "  [OK] Base de demo lista, con datos ficticios nuevos" "Green"
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

# Si el archivo se ejecuta directo (no con dot-source, "."), corre el reseteo
# de una y espera Enter -- util para dejar el demo listo sin abrir el
# navegador. Si en cambio lo cargo iniciar-demo.ps1 con ". resetear-demo.ps1",
# solo define la funcion y deja que el llamador decida cuando invocarla.
if ($MyInvocation.InvocationName -eq '.') {
    return
}
if (-not (Get-Command Escribir -ErrorAction SilentlyContinue)) {
    function Escribir($texto, $color = "Gray") { Write-Host $texto -ForegroundColor $color }
}
Resetear-BaseDemo
Write-Host ""
Read-Host "Enter para cerrar"
