# =============================================================================
# Nucleo compartido por los lanzadores de Fabrica V2 (mejora 8.8 + demo).
#
# No se ejecuta directo: lo cargan (dot-source) iniciar.ps1 e
# iniciar-demo.ps1, que solo difieren en el puerto, la base de datos y si
# hace falta resetear datos antes de arrancar. Toda la mecanica de "levantar
# un proceso, esperar a que responda, abrir el navegador y apagar todo al
# cerrar" vive aca UNA sola vez.
# =============================================================================

$ErrorActionPreference = "Stop"

function Escribir($texto, $color = "Gray") { Write-Host $texto -ForegroundColor $color }

function Abortar($mensaje) {
    Write-Host ""
    Escribir "  ERROR: $mensaje" "Red"
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 1
}

# -----------------------------------------------------------------------------
# Job Object: que al cerrar la ventana se cierre el servidor
# -----------------------------------------------------------------------------
# El problema: en Windows, cerrar la ventana de la consola NO mata a los
# procesos que esa consola lanzo. Quedarian uvicorn corriendo huerfano,
# invisible, ocupando el puerto para la proxima vez.
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
# huerfano), se mete al script que llama a esta funcion. La pertenencia al
# job se HEREDA, asi que todo lo que se lance a partir de aca ya nace
# adentro. Cero carrera.
#
# `Add-Type` no admite redefinir el mismo tipo dos veces en el mismo proceso
# de PowerShell; el chequeo evita el error si algo llegara a cargar este
# archivo mas de una vez.
if (-not ("GrupoProcesos" -as [type])) {
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
}

# -----------------------------------------------------------------------------
# Iniciar-Fabrica: levanta un servidor, espera, abre el navegador y se queda
# esperando hasta que lo cierren.
# -----------------------------------------------------------------------------
# Parametros:
#   Puerto           puerto donde escucha uvicorn. Cada modo (real/demo) usa
#                     uno distinto para poder tener los dos abiertos a la vez.
#   Titulo            texto del encabezado, para distinguir a simple vista
#                     cual lanzador es cual (ej. "FABRICA V2" vs
#                     "FABRICA V2 - DEMO").
#   PrefijoLog        nombre base de los archivos de registro, para que el
#                     modo demo no pise los logs del modo real.
#   VariablesEntorno  hashtable con DB_HOST/DB_PORT/DB_NAME/DB_USER/
#                     DB_PASSWORD para el proceso de uvicorn. Vacio (por
#                     defecto) = usa backend\.env tal cual, que es el modo
#                     real. El modo demo la usa para apuntar a
#                     fabrica_V2_demo con un rol de PostgreSQL acotado, sin
#                     tocar backend\.env.
#   VariablesEntornoDiferidas
#                     lo mismo, pero como scriptblock que se evalua DESPUES
#                     de AntesDeArrancar. Hace falta cuando las credenciales
#                     todavia no existen al invocar la funcion: en el modo
#                     demo, backend\.env.demo lo escribe el reseteo la
#                     primera vez que se corre.
#   AntesDeArrancar   scriptblock opcional que corre despues de validar los
#                     requisitos y ANTES de levantar uvicorn. El modo demo lo
#                     usa para resetear su base de datos en cada apertura.
function Iniciar-Fabrica {
    param(
        [Parameter(Mandatory)][int]$Puerto,
        [Parameter(Mandatory)][string]$Titulo,
        [string]$PrefijoLog = "registro",
        [hashtable]$VariablesEntorno = @{},
        [scriptblock]$VariablesEntornoDiferidas = $null,
        [scriptblock]$AntesDeArrancar = $null
    )

    $Url = "http://127.0.0.1:$Puerto"

    $RaizRepo = Split-Path -Parent $PSScriptRoot
    $RutaBackend = Join-Path $RaizRepo "backend"
    $RutaFrontend = Join-Path $RaizRepo "frontend"
    $RutaDist = Join-Path $RutaFrontend "dist"
    $LogSalida = Join-Path $PSScriptRoot "$PrefijoLog.log"
    $LogErrores = Join-Path $PSScriptRoot "$PrefijoLog-errores.log"

    Clear-Host
    Escribir ""
    Escribir "  ==================================================" "Cyan"
    Escribir "   $Titulo" "Cyan"
    Escribir "  ==================================================" "Cyan"
    Escribir ""

    $hayGrupo = [GrupoProcesos]::Crear((Get-Process -Id $PID).Handle)

    # ---------- Requisitos ----------
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
    # anterior ocupando el puerto, se cierra. Cada modo tiene su puerto
    # exclusivo, asi que lo que este ahi es de una corrida propia y no del
    # entorno de desarrollo. Sin esto, un huerfano bloquearia el arranque
    # sin explicacion.
    $ocupado = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
    foreach ($conexion in $ocupado) {
        Escribir "  Cerrando un servidor anterior que quedo en el $Puerto..." "Yellow"
        Stop-Process -Id $conexion.OwningProcess -Force -ErrorAction SilentlyContinue
    }

    # ---------- Recompilar el frontend solo si hace falta ----------
    # El lanzador sirve el frontend COMPILADO, asi que un cambio de codigo no
    # se ve hasta recompilar. Compilar siempre costaria ~20 segundos en cada
    # arranque; no compilar nunca haria que un dia se mire una version vieja
    # sin saberlo. Se compara la fecha de las fuentes contra la del
    # compilado.
    #
    # El mismo compilado sirve para real y demo: VITE_API_URL=MISMO_ORIGEN
    # deja las llamadas relativas al origen que sirvio la pagina, que ya
    # trae el puerto correcto sin importar cual de los dos sea.
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
    # `npm run build` a mano (o el de Docker, que fija localhost:8001) deja
    # un dist mas nuevo que las fuentes pero apuntando a otro puerto, y el
    # lanzador lo serviria tal cual: la app cargaria y ninguna pantalla
    # traeria datos. Por eso el lanzador deja una marca al compilar. Si la
    # marca falta, o si el dist es mas nuevo que ella (lo compilo otro), se
    # recompila.
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

        $env:VITE_API_URL = "MISMO_ORIGEN"
        & npm --prefix "$RutaFrontend" run build
        $codigo = $LASTEXITCODE
        Remove-Item Env:\VITE_API_URL
        if ($codigo -ne 0) { Abortar "Fallo la compilacion de la interfaz ('npm run build')." }

        # La marca va DESPUES de compilar y AFUERA de dist: Vite vacia dist
        # en cada build, asi que una marca adentro no sobreviviria a la
        # compilacion de otro y no habria con que detectarla.
        Set-Content -Path $marca -Value "MISMO_ORIGEN" -Encoding utf8

        Escribir "  [OK] Interfaz compilada" "Green"
    } else {
        Escribir "  [OK] Interfaz al dia (sin cambios que compilar)" "Green"
    }

    # ---------- Paso previo especifico del modo (ej. resetear el demo) ----------
    if ($AntesDeArrancar) {
        & $AntesDeArrancar
    }

    # Recien ahora, con el paso previo ya corrido, se pueden leer credenciales
    # que ese paso haya generado (ver el parametro en la cabecera).
    if ($VariablesEntornoDiferidas) {
        $VariablesEntorno = & $VariablesEntornoDiferidas
    }

    # ---------- Levantar el servidor ----------
    # Un solo proceso: uvicorn sirve la API y, al existir frontend/dist,
    # tambien la interfaz (ver backend/app/main.py). Sin --reload, que es de
    # desarrollo: aca el codigo no cambia mientras se usa.
    #
    # --host 127.0.0.1 y no 0.0.0.0: escucha solo en esta maquina. Para que
    # entren otros hace falta el tunel de la mejora 8.7, no abrir el puerto.
    Escribir "  Levantando el servidor..." "Gray"

    # Las variables se setean en ESTE proceso antes de lanzar uvicorn: las
    # hereda el hijo. python-dotenv (backend/app/database.py) usa
    # load_dotenv() con override=False, asi que estas variables ganan por
    # sobre lo que diga backend\.env sin tener que tocar ese archivo. Se
    # restauran despues por prolijidad, aunque el script ya no las necesita.
    $originales = @{}
    foreach ($clave in $VariablesEntorno.Keys) {
        $originales[$clave] = [System.Environment]::GetEnvironmentVariable($clave)
        [System.Environment]::SetEnvironmentVariable($clave, $VariablesEntorno[$clave])
    }

    $servidor = Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Puerto" `
        -WorkingDirectory $RutaBackend `
        -NoNewWindow -PassThru `
        -RedirectStandardOutput $LogSalida -RedirectStandardError $LogErrores

    foreach ($clave in $originales.Keys) {
        [System.Environment]::SetEnvironmentVariable($clave, $originales[$clave])
    }

    # ---------- Esperar a que responda y abrir el navegador ----------
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
        Abortar "No se pudo levantar el servidor. Detalle completo en lanzador\$PrefijoLog-errores.log"
    }

    Escribir "  [OK] Servidor respondiendo en $Url" "Green"

    # Se abre con explorer.exe y no con Start-Process directo a proposito.
    # Como este script esta en el Job Object que mata a sus hijos, un
    # navegador lanzado desde aca seria hijo y se cerraria junto con el
    # lanzador: si el navegador no estaba abierto, se llevaria puestas todas
    # las pestanas del usuario. explorer.exe ya esta corriendo, recibe la
    # URL y la abre desde su propio arbol de procesos, afuera del grupo.
    Start-Process "explorer.exe" -ArgumentList $Url

    # ---------- Quedarse esperando ----------
    Escribir ""
    Escribir "  ==================================================" "Cyan"
    Escribir "   $Titulo esta corriendo." "White"
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

    # Salida ordenada por la via del Enter. Si en cambio se cerro la ventana
    # con la X, nada de esto corre y el Job Object hace el trabajo.
    Escribir "  Apagando..." "Gray"
    if (-not $servidor.HasExited) { Stop-Process -Id $servidor.Id -Force -ErrorAction SilentlyContinue }
}
