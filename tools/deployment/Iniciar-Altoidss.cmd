@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Altoidss - Inicio protegido

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%ProyectoFinal\Aplication"
set "PORT=8091"
set "LOCAL_URL=http://127.0.0.1:%PORT%/Html/index.html"
set "HEALTH_URL=http://127.0.0.1:%PORT%/api/index.php?route=/health"
set "PUBLIC_URL=https://altoids.codealex.com"
set "TUNNEL_NAME=altoidss"
set "PHP_EXE="
set "PYTHON_EXE="
set "CLOUDFLARED_EXE="

rem Older branches must not silently serve their versioned, stale catalogue.
if exist "%ROOT_DIR%ProyectoFinal\catalog-storage.local.json" (
    if not exist "%APP_DIR%\api\config\catalog-storage.php" (
        echo [ERROR] Esta rama no incorpora el catalogo central. Integra ese cambio antes de iniciar.
        pause
        exit /b 1
    )
    rem The current router delegates catalogue reads to the central-aware JsonStorage.
    findstr /L /C:"JsonStorage" "%APP_DIR%\server-router.php" >nul
    if errorlevel 1 (
        echo [ERROR] El router de esta rama no usa el catalogo central. Integra el cambio antes de iniciar.
        pause
        exit /b 1
    )
    findstr /L /C:"new CatalogService" "%APP_DIR%\server-router.php" >nul
    if errorlevel 1 (
        echo [ERROR] El router de esta rama no usa el catalogo central. Integra el cambio antes de iniciar.
        pause
        exit /b 1
    )
    findstr /C:"catalogStorage" "%APP_DIR%\api\core\JsonStorage.php" >nul
    if errorlevel 1 (
        echo [ERROR] La API de esta rama no usa el catalogo central.
        pause
        exit /b 1
    )
)

if not exist "%APP_DIR%\Html\index.html" (
    echo [ERROR] No se encontro la aplicacion en:
    echo         %APP_DIR%
    echo.
    pause
    exit /b 1
)

rem Runtime elegido por el despliegue aprobado; nunca sustituir XAMPP ni usar un fallback antiguo.
set "ALTOIDSS_TOOLCHAIN_CONFIG=%ROOT_DIR%runtime\toolchain.local.json"
set "ALTOIDSS_STORAGE_CONFIG=%ROOT_DIR%ProyectoFinal\catalog-storage.local.json"
if not exist "%ALTOIDSS_TOOLCHAIN_CONFIG%" (
    echo [ERROR] Falta runtime\toolchain.local.json. Preparar y aprobar el toolchain antes de iniciar.
    exit /b 1
)
for /f "delims=" %%I in ('powershell.exe -NoProfile -Command "$c=ConvertFrom-Json ([IO.File]::ReadAllText($env:ALTOIDSS_TOOLCHAIN_CONFIG));if($c.schemaVersion -eq 1){$c.phpExecutable}"') do set "PHP_EXE=%%I"
for /f "delims=" %%I in ('powershell.exe -NoProfile -Command "$c=ConvertFrom-Json ([IO.File]::ReadAllText($env:ALTOIDSS_TOOLCHAIN_CONFIG));if($c.schemaVersion -eq 1){$c.pythonExecutable}"') do set "PYTHON_EXE=%%I"
if not defined PHP_EXE exit /b 1
if not defined PYTHON_EXE exit /b 1
if not exist "%PHP_EXE%" exit /b 1
if not exist "%PYTHON_EXE%" exit /b 1
set "PHP_BIN=%PHP_EXE%"
"%PHP_EXE%" -r "exit(PHP_VERSION === '8.4.27' && count(array_diff(['curl','mbstring','openssl','fileinfo','json','session','pdo_sqlite'],get_loaded_extensions())) === 0 ? 0 : 1);"
if errorlevel 1 (
    echo [ERROR] PHP no coincide con el perfil 8.4.27.
    exit /b 1
)
"%PYTHON_EXE%" -B -c "import sys,importlib.metadata;assert sys.version.split()[0]=='3.13.12';assert importlib.metadata.version('openpyxl')=='3.1.5';assert importlib.metadata.version('et_xmlfile')=='2.0.0'"
if errorlevel 1 (
    echo [ERROR] Python o sus dependencias no coinciden con el perfil revisado.
    exit /b 1
)
if /i "%~1"=="--check-runtime" (
    echo [OK] PHP 8.4.27 y Python 3.13.12 con dependencias bloqueadas.
    echo [OK] PHP: %PHP_EXE%
    echo [OK] Python: %PYTHON_EXE%
    exit /b 0
)
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" set "CLOUDFLARED_EXE=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED_EXE (
    for /f "delims=" %%I in ('where cloudflared 2^>nul') do if not defined CLOUDFLARED_EXE set "CLOUDFLARED_EXE=%%I"
)

if not defined CLOUDFLARED_EXE (
    echo [ERROR] No se encontro cloudflared.
    echo         Reinstalalo con: winget install Cloudflare.cloudflared
    echo.
    pause
    exit /b 1
)

if not exist "%APP_DIR%\tools\anime_sync_pipeline.py" (
    echo [ERROR] No se encontro el sincronizador de anime.
    echo.
    pause
    exit /b 1
)

if not exist "%APP_DIR%\config\anime-sync.json" (
    echo [ERROR] No se encontro config\anime-sync.json.
    echo.
    pause
    exit /b 1
)

if not exist "%APP_DIR%\server-router.php" (
    echo [ERROR] No se encontro server-router.php.
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no tiene instalado openpyxl.
    echo         Ejecuta: "%PYTHON_EXE%" -m pip install openpyxl
    echo.
    pause
    exit /b 1
)

set "SERVER_STATE="
for /f "delims=" %%S in ('powershell.exe -NoProfile -Command "$url='%HEALTH_URL%'; try{$r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2;if($r.StatusCode -eq 200 -and $r.Content -match 'Altoidss API'){'READY'}else{'OCCUPIED'}}catch{try{$c=[Net.Sockets.TcpClient]::new();$c.Connect('127.0.0.1',%PORT%);$c.Dispose();'OCCUPIED'}catch{'FREE'}}"') do set "SERVER_STATE=%%S"

set "TUNNEL_RUNNING="
powershell.exe -NoProfile -Command "if(Get-Process -Name cloudflared -ErrorAction SilentlyContinue){exit 0};exit 1" >nul 2>&1
if not errorlevel 1 set "TUNNEL_RUNNING=1"

set "SYNC_RUNNING="
set "SYNC_PID="
if exist "%APP_DIR%\runtime\anime-sync\watcher.pid" set /p SYNC_PID=<"%APP_DIR%\runtime\anime-sync\watcher.pid"
if defined SYNC_PID (
    powershell.exe -NoProfile -Command "if(Get-Process -Id !SYNC_PID! -ErrorAction SilentlyContinue){exit 0};exit 1" >nul 2>&1
    if not errorlevel 1 set "SYNC_RUNNING=1"
)

if /i "%~1"=="--check" (
    echo [OK] Aplicacion:  %APP_DIR%
    echo [OK] PHP:         %PHP_EXE%
    echo [OK] Python:      %PYTHON_EXE%
    echo [OK] Cloudflare:  !CLOUDFLARED_EXE!
    echo [OK] Drive:       config\anime-sync.json
    echo [OK] Puerto fijo: %PORT%
    if /i "%SERVER_STATE%"=="READY" (
        echo [OK] Servidor:     Altoidss ya esta activo
        "%PYTHON_EXE%" "%APP_DIR%\tools\check_session_cookie.py" --url "%HEALTH_URL%"
        if errorlevel 1 goto session_cookie_failed
    )
    if /i "%SERVER_STATE%"=="FREE" echo [OK] Servidor:     listo para iniciar
    if /i "%SERVER_STATE%"=="OCCUPIED" echo [ERROR] Servidor: el puerto %PORT% esta ocupado por otra aplicacion
    if defined SYNC_RUNNING (echo [OK] Sincronizador: activo) else echo [OK] Sincronizador: listo para iniciar
    if defined TUNNEL_RUNNING (echo [OK] Tunel:        cloudflared esta activo) else echo [OK] Tunel:        listo para iniciar
    echo [OK] Acceso web:   %PUBLIC_URL%
    if /i "%SERVER_STATE%"=="OCCUPIED" exit /b 1
    exit /b 0
)

if /i "%SERVER_STATE%"=="OCCUPIED" (
    echo [ERROR] El puerto %PORT% esta ocupado por otra aplicacion.
    echo         Cierra esa aplicacion y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if /i "%SERVER_STATE%"=="READY" (
    echo [OK] Altoidss ya esta activo en el puerto %PORT%.
) else (
    echo Iniciando Altoidss en %LOCAL_URL% ...
    start "Altoidss - Servidor PHP %PORT%" /D "%APP_DIR%" "%PHP_EXE%" -d session.cookie_secure=1 -S 127.0.0.1:%PORT% -t "%APP_DIR%" "server-router.php"

    powershell.exe -NoProfile -Command "$url='%HEALTH_URL%';for($i=0;$i -lt 30;$i++){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1;if($r.StatusCode -eq 200 -and $r.Content -match 'Altoidss API'){exit 0}}catch{};Start-Sleep -Milliseconds 300};exit 1" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Altoidss no pudo iniciar en el puerto %PORT%.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Servidor local activo.
)

rem Refuse public launch if an existing backend still issues an insecure session cookie.
"%PYTHON_EXE%" "%APP_DIR%\tools\check_session_cookie.py" --url "%HEALTH_URL%"
if errorlevel 1 goto session_cookie_failed

if defined SYNC_RUNNING (
    echo [OK] La sincronizacion de Google Sheets ya esta activa.
) else (
    echo Iniciando revision automatica de Google Sheets cada 5 minutos ...
    start "Altoidss - Sincronizacion Drive" /D "%APP_DIR%" "%PYTHON_EXE%" "tools\anime_sync_pipeline.py" --config "config\anime-sync.json" --apply --watch --interval 300
)

if defined TUNNEL_RUNNING (
    echo [OK] El tunel de Cloudflare ya esta activo.
) else (
    echo Iniciando acceso protegido de Cloudflare ...
    start "Altoidss - Cloudflare protegido" /D "%ROOT_DIR%" "!CLOUDFLARED_EXE!" tunnel --url "http://127.0.0.1:%PORT%" run "%TUNNEL_NAME%"
    powershell.exe -NoProfile -Command "Start-Sleep -Seconds 3"
)

start "" "%PUBLIC_URL%"
echo.
echo [OK] Altoidss protegido: %PUBLIC_URL%
echo [INFO] Origen local de diagnostico: %LOCAL_URL%
echo [INFO] Inicia sesion por %PUBLIC_URL% usando HTTPS.
echo [INFO] Solo el correo autorizado en Cloudflare Access puede ingresar.
echo.
echo El servidor, el sincronizador y Cloudflare se ejecutan en ventanas separadas.
echo Cierra esas ventanas cuando quieras detener Altoidss.
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 6"
exit /b 0

:session_cookie_failed
echo [ERROR] El servidor no cumple la politica de cookies para HTTPS publico.
echo         Reinicia el servidor con -SecureCookies antes de publicar.
exit /b 1
