@echo off
REM ===========================================================================
REM Fabrica V2 - lanzador de DEMO (datos ficticios)
REM
REM Doble clic aca para mostrar el sistema a un cliente o en una entrevista
REM SIN exponer ningun dato del negocio real. Usa una base aparte
REM (fabrica_V2_demo) con datos inventados, que se resetea en cada apertura.
REM
REM Corre en el puerto 8011, distinto del 8010 del lanzador real: los dos
REM pueden estar abiertos a la vez sin pisarse.
REM
REM Para tenerlo a mano: clic derecho sobre este archivo > "Enviar a" >
REM "Escritorio (crear acceso directo)".
REM ===========================================================================

title Fabrica V2 - DEMO
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lanzador\iniciar-demo.ps1"

REM Si PowerShell no llego ni a arrancar (raro), sin esto la ventana se
REM cerraria sin dejar ver el error.
if errorlevel 1 pause
