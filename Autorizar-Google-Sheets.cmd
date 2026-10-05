@echo off
setlocal
cd /d "%~dp0"

if not exist "config\google-oauth-client.json" (
    echo [ERROR] Falta config\google-oauth-client.json.
    echo Descarga el cliente OAuth de tipo Aplicacion de escritorio desde Google Cloud
    echo y guardalo con ese nombre. Consulta docs\google-sheets-writeback.md.
    echo.
    pause
    exit /b 1
)

python tools\google_sheets_writeback.py --authorize
echo.
pause
