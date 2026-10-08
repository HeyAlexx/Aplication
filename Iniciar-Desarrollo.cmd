@echo off
setlocal
title Altoidss - Desarrollo local
set "DEV_APP_DIR=%~dp0"
set "DEV_PHP_EXE="
if exist "C:\xampp\php\php.exe" set "DEV_PHP_EXE=C:\xampp\php\php.exe"
if not defined DEV_PHP_EXE (
    for /f "delims=" %%I in ('where php 2^>nul') do if not defined DEV_PHP_EXE set "DEV_PHP_EXE=%%I"
)
if not defined DEV_PHP_EXE (
    echo [ERROR] No se encontro PHP. Agregalo al PATH o instala XAMPP.
    exit /b 1
)
if not exist "%DEV_APP_DIR%server-router.php" (
    echo [ERROR] Falta server-router.php.
    exit /b 1
)
echo [INFO] Entorno local de desarrollo: %DEV_APP_DIR%
echo [INFO] URL: http://127.0.0.1:8092/Html/index.html
echo [INFO] No se inicia Cloudflare ni la sincronizacion de Google Sheets.
if /i "%~1"=="--check" exit /b 0
echo [INFO] Deja esta terminal abierta; Ctrl+C detiene el servidor.
"%DEV_PHP_EXE%" -S 127.0.0.1:8092 -t "%DEV_APP_DIR%." "%DEV_APP_DIR%server-router.php"
exit /b %errorlevel%
