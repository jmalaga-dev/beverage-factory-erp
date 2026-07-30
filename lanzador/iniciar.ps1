# =============================================================================
# Lanzador local de Fabrica V2 (mejora 8.8)
#
# Para USAR el sistema en el dia a dia, sin abrir terminales a mano. No
# reemplaza el entorno de desarrollo: ese sigue siendo uvicorn --reload en el
# 8000 + Vite en el 5173, y este script no lo toca.
#
# No se ejecuta directo: se hace doble clic en "Fabrica V2.bat" de la raiz.
#
# Que hace, en orden:
#   1. Arma un Job Object de Windows para que al cerrar la ventana se apague
#      TODO lo que este script levante (ver el bloque de abajo).
#   2. Verifica que PostgreSQL este corriendo y que exista backend\.env.
#   3. Recompila el frontend solo si hay codigo mas nuevo que el compilado.
#   4. Levanta un unico proceso (uvicorn sin --reload) que sirve la API Y la
#      interfaz en el mismo puerto.
#   5. Espera a que responda y abre el navegador.
#   6. Se queda esperando. Al cerrarse, apaga el servidor.
# =============================================================================

$ErrorActionPreference = "Stop"

# El puerto es 8010 y no 8000 a proposito, mismo criterio que los 8001/5433
# del compose: el entorno de desarrollo ya ocupa el 8000. Asi se puede estar
# usando la app por el lanzador y programando al mismo tiempo, sin que uno
# mate al otro ni haya que adivinar cual de los dos esta respondiendo.
$Puerto = 8010
$Url = "http://127.0.0.1:$Puerto"

$RaizRepo = Split-Path -Parent $PSScriptRoot
$RutaBackend = Join-Path $RaizRepo "backend"
$RutaFrontend = Join-Path $RaizRepo "frontend"
$RutaDist = Join-Path $RutaFrontend "dist"
$LogSalida = Join-Path $PSScriptRoot "registro.log"
$LogErrores = Join-Path $PSScriptRoot "registro-errores.log"

function Escribir($texto, $color = "Gray") { Write-Host $texto -ForegroundColor $color }

function Abortar($mensaje) {
    Write-Host ""
    Escribir "  ERROR: $mensaje" "Red"
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 1
}

Clear-Host
Escribir ""
Escribir "  ==================================================" "Cyan"
Escribir "   FABRICA V2" "Cyan"
Escribir "  ==================================================" "Cyan"
Escribir ""

# -----------------------------------------------------------------------------
# 1. Job Object: que al cerrar la ventana se cierre el servidor
# -----------------------------------------------------------------------------
# El problema: en Windows, cerrar la ventana de la consola NO mata a los
# procesos que esa consola lanzo. Quedarian uvicorn (y npm) corriendo
# huerfanos, invisibles, ocupando el puerto para la proxima vez.
#
# La solucion del propio Windows es un "Job Object" con la marca
# KILL_ON_JOB_CLOSE: un grupo de procesos que el sistema operativo termina
# cuando se cierra el ultimo handle del grupo. Como el handle lo tiene este
# script, muera como muera (la X, Ctrl+C, o hasta un taskkill), el sistema
# se encarga de matar lo que quede adentro. No depende de que el script
# alcance a ejecutar codigo de limpieza, que es justamente lo que no pasa
# cuando se cierra la ventana con la X.
#
# El truco fino: en vez de meter cada proceso hijo al job de a uno (y dejar
# una ventana de milisegundos entre lanzarlo y meterlo, donde podria quedar
# huerfano), se mete a este script. La pertenencia al job se HEREDA, asi que
# todo lo que se lance a partir de aca ya nace adentro. Cero carrera.
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct IO_COUNTERS {
    public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
    public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
}

[StructLayout(LayoutKind.Sequential)]
public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
    public long PerProcessUserTimeLimit;
    public long PerJobUserTimeLimit;
    public uint LimitFlags;
    public UIntPtr MinimumWorkingSetSize;
    public UIntPtr MaximumWorkingSetSize;
    public uint ActiveProcessLimit;
    public UIntPtr Affinity;
    public uint PriorityClass;
    public uint SchedulingClass;
}

[StructLayout(LayoutKind.Sequential)]
public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
    public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
    public IO_COUNTERS IoInfo;
    public UIntPtr ProcessMemoryLimit;
    public UIntPtr JobMemoryLimit;
    public UIntPtr PeakProcessMemoryUsed;
    public UIntPtr PeakJobMemoryUsed;
}

public static class GrupoProcesos {
    const int ClaseLimitesExtendidos = 9;
    const uint MATAR_AL_CERRAR = 0x2000;   // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern IntPtr CreateJobObject(IntPtr atributos, string nombre);
    [DllImport("kernel32.dll")]
    static extern bool SetInformationJobObject(IntPtr job, int clase, IntPtr info, uint tamano);
    [DllImport("kernel32.dll")]
    static extern bool AssignProcessToJobObject(IntPtr job, IntPtr proceso);
    [DllImport("kernel32.dll")]
    static extern bool CloseHandle(IntPtr handle);

    // Crea el grupo y le engancha el proceso indicado. Devuelve false si el
    // sistema no lo permitio; el llamador decide si sigue igual.
    public static bool Crear(IntPtr proceso) {
        IntPtr job = CreateJobObject(IntPtr.Zero, null);
        if (job == IntPtr.Zero) return false;

        var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        info.BasicLimitInformation.LimitFlags = MATAR_AL_CERRAR;

        int tamano = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
        IntPtr puntero = Marshal.AllocHGlobal(tamano);
        Marshal.StructureToPtr(info, puntero, false);
        bool ok = SetInformationJobObject(job, ClaseLimitesExtendidos, puntero, (uint)tamano);
        Marshal.FreeHGlobal(puntero);

        if (!ok || !AssignProcessToJobObject(job, proceso)) { CloseHandle(job); return false; }

        // A proposito NO se cierra el handle del job: mientras viva este
        // proceso, vive el grupo. Al morir, Windows cierra el handle y con
        // eso mata a todos los procesos de adentro.
        return true;
    }
}
"@

$hayGrupo = [GrupoProcesos]::Crear((Get-Process -Id $PID).Handle)

# -----------------------------------------------------------------------------
# 2. Requisitos
# -----------------------------------------------------------------------------
$servicio = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue |
            Select-Object -First 1
if (-not $servicio) {
    Abortar "No se encontro el servicio de PostgreSQL. Sin base de datos no hay sistema."
}
if ($servicio.Status -ne "Running") {
    Escribir "  Base de datos detenida. Arrancando $($servicio.Name)..." "Yellow"
    try { Start-Service $servicio.Name }
    catch { Abortar "No se pudo arrancar $($servicio.Name). Probar abriendo este lanzador como administrador." }
}
Escribir "  [OK] Base de datos: $($servicio.Name)" "Green"

if (-not (Test-Path (Join-Path $RutaBackend ".env"))) {
    Abortar "Falta backend\.env (la configuracion de conexion). Copiar backend\.env.example como .env y completarlo."
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { Abortar "No se encontro Python en el PATH." }

# Red de seguridad: si por lo que sea quedo un servidor de una corrida
# anterior ocupando el puerto, se cierra. El 8010 es exclusivo del lanzador,
# asi que lo que este ahi es de una corrida propia y no del entorno de
# desarrollo. Sin esto, un huerfano bloquearia el arranque sin explicacion.
$ocupado = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
foreach ($conexion in $ocupado) {
    Escribir "  Cerrando un servidor anterior que quedo en el $Puerto..." "Yellow"
    Stop-Process -Id $conexion.OwningProcess -Force -ErrorAction SilentlyContinue
}

# -----------------------------------------------------------------------------
# 3. Recompilar el frontend solo si hace falta
# -----------------------------------------------------------------------------
# El lanzador sirve el frontend COMPILADO, asi que un cambio de codigo no se
# ve hasta recompilar. Compilar siempre costaria ~20 segundos en cada
# arranque; no compilar nunca haria que un dia mires una version vieja sin
# saberlo. Se compara la fecha de las fuentes contra la del compilado.
$fuentes = @(
    Join-Path $RutaFrontend "src"
    Join-Path $RutaFrontend "index.html"
    Join-Path $RutaFrontend "package.json"
    Join-Path $RutaFrontend "vite.config.js"
) | Where-Object { Test-Path $_ }

$ultimoCambio = ($fuentes |
    ForEach-Object { Get-ChildItem $_ -Recurse -File -ErrorAction SilentlyContinue } |
    Measure-Object -Property LastWriteTimeUtc -Maximum).Maximum

$indice = Join-Path $RutaDist "index.html"
$compilado = if (Test-Path $indice) { (Get-Item $indice).LastWriteTimeUtc } else { [datetime]::MinValue }

# La fecha sola no alcanza: no dice CON QUE URL de backend se compilo. Un
# `npm run build` a mano (o el de Docker, que fija localhost:8001) deja un
# dist mas nuevo que las fuentes pero apuntando a otro puerto, y el lanzador
# lo serviria tal cual: la app cargaria y ninguna pantalla traeria datos.
# Por eso el lanzador deja una marca al compilar. Si la marca falta, o si el
# dist es mas nuevo que ella (lo compilo otro), se recompila.
$marca = Join-Path $PSScriptRoot ".compilado"
$fechaMarca = if (Test-Path $marca) { (Get-Item $marca).LastWriteTimeUtc } else { [datetime]::MinValue }
$compiladoPorOtro = $fechaMarca -eq [datetime]::MinValue -or $compilado -gt $fechaMarca

if ($ultimoCambio -gt $compilado -or $compiladoPorOtro) {
    if ($compilado -eq [datetime]::MinValue) {
        Escribir "  Primera vez: compilando la interfaz (un minuto)..." "Yellow"
    } elseif ($compiladoPorOtro) {
        Escribir "  La interfaz fue compilada por otro medio: recompilando (~20 segundos)..." "Yellow"
    } else {
        Escribir "  Hay cambios en la interfaz: recompilando (~20 segundos)..." "Yellow"
    }

    if (-not (Test-Path (Join-Path $RutaFrontend "node_modules"))) {
        Escribir "  Instalando dependencias del frontend (solo esta vez)..." "Yellow"
        & npm --prefix "$RutaFrontend" install
        if ($LASTEXITCODE -ne 0) { Abortar "Fallo 'npm install'." }
    }

    # MISMO_ORIGEN: las llamadas al backend salen relativas, porque en este
    # modo la API y la interfaz comparten puerto. Ver frontend/src/api.js.
    $env:VITE_API_URL = "MISMO_ORIGEN"
    & npm --prefix "$RutaFrontend" run build
    $codigo = $LASTEXITCODE
    Remove-Item Env:\VITE_API_URL
    if ($codigo -ne 0) { Abortar "Fallo la compilacion de la interfaz ('npm run build')." }

    # La marca va DESPUES de compilar y AFUERA de dist: Vite vacia dist en
    # cada build, asi que una marca adentro no sobreviviria a la compilacion
    # de otro y no habria con que detectarla.
    Set-Content -Path $marca -Value "MISMO_ORIGEN" -Encoding utf8

    Escribir "  [OK] Interfaz compilada" "Green"
} else {
    Escribir "  [OK] Interfaz al dia (sin cambios que compilar)" "Green"
}

# -----------------------------------------------------------------------------
# 4. Levantar el servidor
# -----------------------------------------------------------------------------
# Un solo proceso: uvicorn sirve la API y, al existir frontend/dist, tambien
# la interfaz (ver backend/app/main.py). Sin --reload, que es de desarrollo:
# aca el codigo no cambia mientras se usa.
#
# --host 127.0.0.1 y no 0.0.0.0: escucha solo en esta maquina. Para que
# entren otros hace falta el tunel de la mejora 8.7, no abrir el puerto.
Escribir "  Levantando el servidor..." "Gray"

$servidor = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Puerto" `
    -WorkingDirectory $RutaBackend `
    -NoNewWindow -PassThru `
    -RedirectStandardOutput $LogSalida -RedirectStandardError $LogErrores

# -----------------------------------------------------------------------------
# 5. Esperar a que responda y abrir el navegador
# -----------------------------------------------------------------------------
$listo = $false
foreach ($intento in 1..60) {
    if ($servidor.HasExited) { break }
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        $listo = $true
        break
    } catch {
        # Mientras arranca, la conexion se rechaza: es normal, se reintenta.
        Start-Sleep -Milliseconds 500
    }
}

if (-not $listo) {
    Escribir "  El servidor no respondio. Ultimas lineas del registro:" "Red"
    if (Test-Path $LogErrores) { Get-Content $LogErrores -Tail 15 | ForEach-Object { Escribir "    $_" "DarkGray" } }
    Abortar "No se pudo levantar el servidor. Detalle completo en lanzador\registro-errores.log"
}

Escribir "  [OK] Servidor respondiendo en $Url" "Green"

# Se abre con explorer.exe y no con Start-Process directo a proposito. Como
# este script esta en el Job Object que mata a sus hijos, un navegador
# lanzado desde aca seria hijo y se cerraria junto con el lanzador: si el
# navegador no estaba abierto, se llevaria puestas todas las pestanas del
# usuario. explorer.exe ya esta corriendo, recibe la URL y la abre desde su
# propio arbol de procesos, afuera del grupo.
Start-Process "explorer.exe" -ArgumentList $Url

# -----------------------------------------------------------------------------
# 6. Quedarse esperando
# -----------------------------------------------------------------------------
Escribir ""
Escribir "  ==================================================" "Cyan"
Escribir "   Fabrica V2 esta corriendo." "White"
Escribir ""
Escribir "   Abierto en:  $Url" "White"
if (-not $hayGrupo) {
    Escribir "   Aviso: no se pudo crear el grupo de procesos; si cerras" "Yellow"
    Escribir "   con la X puede quedar el servidor corriendo." "Yellow"
    Escribir ""
}
Escribir "   Para APAGAR: cerra esta ventana (o Enter aca)." "White"
Escribir "  ==================================================" "Cyan"
Escribir ""

Read-Host "  Enter para apagar" | Out-Null

# Salida ordenada por la via del Enter. Si en cambio se cerro la ventana con
# la X, nada de esto corre y el Job Object hace el trabajo.
Escribir "  Apagando..." "Gray"
if (-not $servidor.HasExited) { Stop-Process -Id $servidor.Id -Force -ErrorAction SilentlyContinue }
