# Plantilla de despliegue: instalar en la raiz del workspace, no ejecutar desde tools/deployment.
[CmdletBinding()]
param(
    [ValidateSet('desarrollo','produccion')][string]$Environment = 'desarrollo',
    [string]$AppPath = '',
    [int]$Port = 8092,
    [string]$BindAddress = '127.0.0.1',
    [switch]$Sync
)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath($PSScriptRoot)
$environmentFolder = if ($Environment -eq 'produccion') { 'ProyectoFinal' } else { 'Desarrollo' }
if (-not $AppPath) { $AppPath = Join-Path $workspace "$environmentFolder\Aplication" }
$app = (Resolve-Path -LiteralPath $AppPath).Path
$production = [IO.Path]::GetFullPath((Join-Path $workspace 'ProyectoFinal\Aplication'))
if ($Environment -eq 'produccion' -and $app -ne $production) {
    throw 'Un checkout de pruebas no puede usar el almacenamiento de producción.'
}
if ($Environment -eq 'desarrollo' -and $app -eq $production) {
    throw 'El checkout de producción no puede arrancarse como desarrollo.'
}
foreach ($file in @('server-router.php','api\config\catalog-storage.php','tools\catalog_storage.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $app $file))) {
        throw 'Esta rama no incorpora todavía el almacenamiento central. Integra el cambio antes de arrancarla.'
    }
}
foreach ($entry in @(@{file='server-router.php';marker='JsonStorage'},
                     @{file='api\core\JsonStorage.php';marker='catalogStorage'},
                     @{file='tools\anime_sync_pipeline.py';marker='catalog_storage'})) {
    if (-not (Select-String -LiteralPath (Join-Path $app $entry.file) -SimpleMatch $entry.marker -Quiet)) {
        throw 'Esta rama usa todavía datos locales versionados. No se iniciará con un catálogo atrasado.'
    }
}
$env:ALTOIDSS_STORAGE_CONFIG = Join-Path $workspace "$environmentFolder\catalog-storage.local.json"
$settings = Get-Content -LiteralPath $env:ALTOIDSS_STORAGE_CONFIG -Raw | ConvertFrom-Json
if ($settings.environment -ne $Environment) { throw 'El descriptor apunta a otro entorno.' }
Write-Output "Entorno: $Environment; catálogo: $($settings.catalogDir)"
Push-Location -LiteralPath $app
try {
    if ($Sync) {
        # Development uses its own Sheet config/token; they are never copied here.
        & 'C:\Python313\python.exe' 'tools\anime_sync_pipeline.py' --config 'config\anime-sync.json' --apply --watch --interval 300
    } else {
        & 'C:\xampp\php\php.exe' -S "${BindAddress}:$Port" -t . 'server-router.php'
    }
} finally { Pop-Location }
