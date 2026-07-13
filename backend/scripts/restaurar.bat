@echo off
set /p Archivo="Ruta del archivo de respaldo a restaurar: "
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_db.ps1" -Archivo "%Archivo%"
pause
