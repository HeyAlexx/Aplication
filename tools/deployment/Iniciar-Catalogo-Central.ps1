# Plantilla de despliegue: instalar en la raiz del workspace, no ejecutar desde tools/deployment.
[CmdletBinding()]
param(
    [ValidateSet('desarrollo','produccion')][string]$Environment = 'desarrollo',
    [string]$AppPath = '',
    [int]$Port = 8092,
    [string]$BindAddress = '127.0.0.1',
    [switch]$Sync,
    [string]$PhpExecutable = '',
    [string]$PythonExecutable = '',
    [switch]$CheckRuntime
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
$toolchainFile = Join-Path $workspace 'runtime\toolchain.local.json'
$toolchain = $null
if ((-not $Sync -and -not $PhpExecutable) -or ($Sync -and -not $PythonExecutable)) {
    if (-not (Test-Path -LiteralPath $toolchainFile -PathType Leaf)) {
        throw 'Falta runtime/toolchain.local.json. Preparar y aprobar el toolchain antes de activar este launcher.'
    }
    $toolchain = Get-Content -LiteralPath $toolchainFile -Raw | ConvertFrom-Json
    if ($toolchain.schemaVersion -ne 1) { throw 'Formato de toolchain no admitido.' }
}
if ($Sync) {
    if (-not $PythonExecutable) { $PythonExecutable = $toolchain.pythonExecutable }
    $PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
    $runtimeProfile = & $PythonExecutable '-B' '-c' "import sys,importlib.metadata,json;print(json.dumps({'version':sys.version.split()[0],'openpyxl':importlib.metadata.version('openpyxl'),'et_xmlfile':importlib.metadata.version('et_xmlfile')}))"
    if ($LASTEXITCODE -ne 0) { throw 'El Python seleccionado no cumple el perfil.' }
    $runtimeProfile = $runtimeProfile | ConvertFrom-Json
    if ($runtimeProfile.version -ne '3.13.12' -or $runtimeProfile.openpyxl -ne '3.1.5' -or $runtimeProfile.et_xmlfile -ne '2.0.0') {
        throw 'El Python o sus dependencias no coinciden con el perfil revisado.'
    }
} else {
    if (-not $PhpExecutable) { $PhpExecutable = $toolchain.phpExecutable }
    $PhpExecutable = (Resolve-Path -LiteralPath $PhpExecutable).Path
    $runtimeProfile = & $PhpExecutable '-r' "echo json_encode(['version'=>PHP_VERSION,'extensions'=>get_loaded_extensions()],JSON_THROW_ON_ERROR);"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar el PHP seleccionado.' }
    $runtimeProfile = $runtimeProfile | ConvertFrom-Json
    if ($runtimeProfile.version -ne '8.4.27') { throw 'El PHP seleccionado no coincide con el perfil 8.4.27.' }
    foreach ($extension in @('curl','mbstring','openssl','fileinfo','json','session','pdo_sqlite')) {
        if ($runtimeProfile.extensions -notcontains $extension) { throw "Falta la extension requerida: $extension" }
    }
    $env:PHP_BIN = $PhpExecutable
}
if ($CheckRuntime) {
    @{status='RUNTIME_VERIFIED_NO_START';environment=$Environment;profile=$runtimeProfile} | ConvertTo-Json -Compress -Depth 5
    return
}
Write-Output "Entorno: $Environment; catálogo: $($settings.catalogDir)"
Push-Location -LiteralPath $app
try {
    if ($Sync) {
        # Development uses its own Sheet config/token; they are never copied here.
        & $PythonExecutable 'tools\anime_sync_pipeline.py' --config 'config\anime-sync.json' --apply --watch --interval 300
    } else {
        & $PhpExecutable -S "${BindAddress}:$Port" -t . 'server-router.php'
    }
} finally { Pop-Location }
