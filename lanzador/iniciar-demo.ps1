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
# =============================================================================

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

Iniciar-Fabrica -Puerto 8011 `
    -Titulo "FABRICA V2 - DEMO (datos ficticios)" `
    -PrefijoLog "registro-demo" `
    -AntesDeArrancar $resetear `
    -VariablesEntornoDiferidas $variablesDemo
