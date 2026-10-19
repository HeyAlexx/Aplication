[CmdletBinding()]
param(
    [ValidateSet('desarrollo','produccion')][string]$Environment='desarrollo',
    [string]$Workspace=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))),
    [string]$AppPath=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))),
    [int]$Port=8092,
    [string]$BindAddress='127.0.0.1',
    [string]$PhpBin='php',
    [string]$PythonBin='python',
    [switch]$Sync
)
$ErrorActionPreference='Stop'
$workspaceRoot=(Resolve-Path -LiteralPath $Workspace).Path
$app=(Resolve-Path -LiteralPath $AppPath).Path
$production=[IO.Path]::GetFullPath((Join-Path $workspaceRoot 'ProyectoFinal\Aplication'))
if (($Environment -eq 'produccion') -ne ($app -eq $production)) {
    throw 'Producción solo puede arrancar desde su instalación; no usar datos reales en un checkout de pruebas.'
}
foreach($file in @('api\config\catalog-storage.php','tools\storage_transaction.py')) {
    if (!(Test-Path -LiteralPath (Join-Path $app $file))) {throw 'Integra primero el soporte de catálogo central en esta rama.'}
}
$folder=if($Environment -eq 'produccion'){'ProyectoFinal'}else{'Desarrollo'}
$descriptor=Join-Path $workspaceRoot "$folder\catalog-storage.local.json"
$settings=Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
if ($settings.environment -ne $Environment) {throw 'El descriptor apunta a otro entorno.'}
foreach($key in @('catalogDir','syncStateDir')) {
    if (!(Test-Path -LiteralPath $settings.$key -PathType Container)) {throw "Directorio central no disponible: $key"}
}
$previousDescriptor=$env:ALTOIDSS_STORAGE_CONFIG
$env:ALTOIDSS_STORAGE_CONFIG=$descriptor
Push-Location -LiteralPath $app
try {
    if ($Sync) {
        $config=Join-Path $app 'config\anime-sync.json'
        $own=Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
        if ($Environment -eq 'desarrollo') {
            $productionConfig=Join-Path $production 'config\anime-sync.json'
            if (Test-Path -LiteralPath $productionConfig) {
                $real=Get-Content -LiteralPath $productionConfig -Raw | ConvertFrom-Json
                if ($own.googleSheets.spreadsheetId -eq $real.googleSheets.spreadsheetId) {
                    throw 'La hoja de desarrollo no puede ser la hoja de producción.'
                }
            }
        }
        & $PythonBin tools/anime_sync_pipeline.py --config $config --apply --watch --interval 300
    } else {
        Write-Output "Entorno: $Environment; servidor: http://${BindAddress}:$Port/Html/catalogo.html"
        & $PhpBin -S "${BindAddress}:$Port" -t . server-router.php
    }
    if ($LASTEXITCODE -ne 0) {throw "El proceso terminó con código $LASTEXITCODE"}
} finally {
    Pop-Location
    $env:ALTOIDSS_STORAGE_CONFIG=$previousDescriptor
}
