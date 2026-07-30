# =============================================================================
# Lanzador local de Fabrica V2 (mejora 8.8) — base de datos REAL.
#
# Para USAR el sistema en el dia a dia, sin abrir terminales a mano. No
# reemplaza el entorno de desarrollo: ese sigue siendo uvicorn --reload en el
# 8000 + Vite en el 5173, y este script no lo toca.
#
# No se ejecuta directo: se hace doble clic en "Fabrica V2.bat" de la raiz.
#
# Usa backend\.env tal cual (sin overrides): la base real, el usuario y
# contrasena de siempre. Para mostrar el sistema con datos ficticios sin
# tocar la base real, ver "Fabrica V2 (demo).bat".
# =============================================================================

. (Join-Path $PSScriptRoot "_comun.ps1")

Iniciar-Fabrica -Puerto 8010 -Titulo "FABRICA V2"
