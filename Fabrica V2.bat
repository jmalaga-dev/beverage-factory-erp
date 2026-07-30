@echo off
REM ===========================================================================
REM Fabrica V2 - lanzador de uso diario (mejora 8.8)
REM
REM Doble clic aca y listo: levanta la base, compila la interfaz si hace falta,
REM arranca el servidor y abre el navegador. Al cerrar esta ventana se apaga
REM todo.
REM
REM Para tenerlo a mano: clic derecho sobre este archivo > "Enviar a" >
REM "Escritorio (crear acceso directo)".
REM
REM Este .bat no hace el trabajo, solo llama al script de PowerShell que si lo
REM hace. Es el mismo patron de backend\scripts\respaldar.bat: un .ps1 no se
REM puede doble-clickear (Windows lo abre en el editor), y ademas la politica
REM de ejecucion por defecto lo bloquearia. El .bat resuelve las dos cosas.
REM ===========================================================================

title Fabrica V2
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lanzador\iniciar.ps1"

REM Si PowerShell no llego ni a arrancar (raro), sin esto la ventana se
REM cerraria sin dejar ver el error.
if errorlevel 1 pause
