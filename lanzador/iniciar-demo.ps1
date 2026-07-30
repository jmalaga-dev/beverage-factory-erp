# =============================================================================
# Lanzador de DEMO de Fabrica V2 — datos FICTICIOS, base aparte.
#
# Para mostrar el sistema a un cliente o en una entrevista sin exponer un
# solo dato del negocio real. No se ejecuta directo: se hace doble clic en
# "Fabrica V2 (demo).bat" de la raiz.
#
# Diferencias con el lanzador real (lanzador\iniciar.ps1):
#   - Puerto 8011 (el real usa 8010), asi los dos pueden estar abiertos a la
#     vez sin pisarse: la app real corriendo para uso propio y el demo al
#     lado para mostrar.
#   - Base fabrica_V2_demo, con datos inventados (docker\seed_demo.sql).
#   - Se RESETEA en cada apertura: lo que haya tocado una demo anterior no
#     se arrastra a la siguiente.
#   - Se conecta con el rol acotado fabrica_demo_local, que no puede tocar
#     ni fabrica_V2 (la real) ni fabrica_V2_pruebas.
#
# Por que dos .bat separados y no un menu adentro de uno solo: el momento de
# usar el demo suele ser con alguien mirando. Un menu agrega un paso donde
# equivocarse de tecla significa mostrar los datos reales. Con dos iconos de
# nombre distinto no hay tecla que apretar mal.
#
# El parametro -Compartir (no se toca a mano: lo pasa "Fabrica V2 (demo
# online).bat") agrega un Cloudflare Quick Tunnel: el demo queda accesible
# desde internet por unos minutos, con una URL publica distinta cada vez.
# Por el mismo criterio de "sin menu": es OTRO archivo .bat, para que
# compartir el demo por internet sea una eleccion explicita, nunca sin
# querer al abrir el de siempre.
# =============================================================================

param([switch]$Compartir)

. (Join-Path $PSScriptRoot "_comun.ps1")
. (Join-Path $PSScriptRoot "resetear-demo.ps1")

# El reseteo corre DESPUES de validar requisitos y compilar, y ANTES de
# levantar uvicorn (ver el parametro AntesDeArrancar en _comun.ps1). Si algo
# falla ahi, el servidor no llega a arrancar y no queda un demo a medias.
$resetear = { Resetear-BaseDemo }

# Las credenciales las escribe resetear-demo.ps1 en backend\.env.demo la
# primera vez, asi que se leen DESPUES de que el reseteo haya corrido. Por
# eso se pasan como scriptblock diferido en vez de leerlas aca arriba.
$variablesDemo = {
    $envDemoPath = Join-Path (Split-Path -Parent $PSScriptRoot) "backend\.env.demo"
    $vars = @{}
    Get-Content $envDemoPath | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') { $vars[$matches[1]] = $matches[2] }
    }
    return $vars
}

$titulo = if ($Compartir) { "FABRICA V2 - DEMO ONLINE (link publico)" } else { "FABRICA V2 - DEMO (datos ficticios)" }

Iniciar-Fabrica -Puerto 8011 `
    -Titulo $titulo `
    -PrefijoLog "registro-demo" `
    -AntesDeArrancar $resetear `
    -VariablesEntornoDiferidas $variablesDemo `
    -CompartirPorTunel:$Compartir
