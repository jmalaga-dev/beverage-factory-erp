@echo off
REM ===========================================================================
REM Fabrica V2 - lanzador de DEMO ONLINE (link publico, datos ficticios)
REM
REM Igual que "Fabrica V2 (demo).bat", pero ademas abre un Cloudflare Quick
REM Tunnel: te da una URL publica (https://algo.trycloudflare.com) para
REM compartir con un cliente o en una entrevista, SIN cuenta ni dominio.
REM
REM La URL sale impresa en esta ventana y queda copiada al portapapeles. Es
REM valida SOLO mientras esta ventana este abierta, y cambia cada vez.
REM
REM Requiere tener instalado cloudflared una vez:
REM   winget install --id Cloudflare.cloudflared
REM
REM Es un .bat APARTE del demo normal a proposito: compartir el demo por
REM internet tiene que ser una decision explicita (doble clic en ESTE
REM archivo), nunca un efecto secundario de abrir el de siempre.
REM ===========================================================================

title Fabrica V2 - DEMO ONLINE
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lanzador\iniciar-demo.ps1" -Compartir

REM Si PowerShell no llego ni a arrancar (raro), sin esto la ventana se
REM cerraria sin dejar ver el error.
if errorlevel 1 pause
