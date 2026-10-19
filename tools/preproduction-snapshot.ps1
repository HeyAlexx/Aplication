[CmdletBinding()]
param(
    [ValidatePattern('^[a-z0-9-]+$')][string]$Phase = 'baseline',
    [switch]$RefreshCatalog
)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$production = Join-Path $workspace 'ProyectoFinal\Aplication'
$development = Join-Path $workspace 'Desarrollo\Aplication'
$snapshot = Join-Path $workspace ('work\preproduction-snapshots\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $Phase)
$excluded = @('.git', 'backups', 'node_modules', '__pycache__')
$lockedLogs = @('watcher.log', 'watcher-error.log', '.watcher.lock', '.storage.lock')
$manifest = [ordered]@{ phase=$Phase; timestamp=(Get-Date -Format o); containsPrivateConfiguration=$true; excludedActiveLogs=$lockedLogs; copies=@(); parity=@() }

function Save-Tree([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($entry in Get-ChildItem -LiteralPath $Source -Force) {
        if ($entry.Name -in $excluded -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
        if ($entry.Name -in $lockedLogs) { continue } # Live process holds exclusive log handles.
        $target = Join-Path $Destination $entry.Name
        if ($entry.PSIsContainer) { Save-Tree $entry.FullName $target; continue }
        Copy-Item -LiteralPath $entry.FullName -Destination $target
        $sourceHash = (Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256).Hash
        if ($sourceHash -ne (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash) { throw "Copia no verificada: $($entry.Name)" }
        $manifest.copies += [ordered]@{ source=$entry.FullName; backup=$target; sha256=$sourceHash }
    }
}

function Read-GitState([string]$Repository, [string[]]$Arguments) {
    $result = & git -c "safe.directory=$Repository" -C $Repository @Arguments
    if ($LASTEXITCODE -ne 0) { throw "No se pudo registrar el estado Git de $Repository" }
    return $result
}

foreach ($environment in @(@{name='production';path=$production}, @{name='development';path=$development})) {
    Save-Tree $environment.path (Join-Path $snapshot $environment.name)
    $descriptor = Join-Path (Split-Path $environment.path -Parent) 'catalog-storage.local.json'
    if (Test-Path -LiteralPath $descriptor) {
        $settings = Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
        foreach ($entry in @(@{key='catalogDir';name='catalogo'}, @{key='syncStateDir';name='anime-sync'})) {
            $centralPath = [IO.Path]::GetFullPath($settings.($entry.key))
            if (-not $centralPath.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'El directorio central está fuera del workspace autorizado.'
            }
            Save-Tree $centralPath (Join-Path $snapshot ($environment.name + '-central\' + $entry.name))
        }
        Copy-Item -LiteralPath $descriptor -Destination (Join-Path $snapshot ($environment.name + '-catalog-storage.local.json'))
    }
    # Git metadata is shared: save identity and patches, never replace the .git directory.
    $gitState = [ordered]@{
        branch=(Read-GitState $environment.path @('branch','--show-current'))
        commit=(Read-GitState $environment.path @('rev-parse','HEAD'))
        status=@(Read-GitState $environment.path @('status','--short'))
        unstaged=(Read-GitState $environment.path @('diff','--binary') | Out-String)
        staged=(Read-GitState $environment.path @('diff','--cached','--binary') | Out-String)
    }
    $gitState | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $snapshot ($environment.name + '-git.json')) -Encoding utf8
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $snapshot 'manifest.json') -Encoding utf8

if ($RefreshCatalog) {
    foreach ($file in @('anime.json', 'peliculas.json', 'series.json', 'noticias.json', 'temporadas.json', 'episodios.json', 'anime-hoja.json')) {
        # Use the verified production snapshot, not a moving source. Never copy accounts,
        # queues, Sheets configuration or tokens between environments.
        $source = Join-Path $snapshot "production\data\$file"
        $target = Join-Path $development "data\$file"
        $centralSource = Join-Path $snapshot "production-central\catalogo\$file"
        $devDescriptor = Join-Path (Split-Path $development -Parent) 'catalog-storage.local.json'
        if (Test-Path -LiteralPath $centralSource) {
            if (-not (Test-Path -LiteralPath $devDescriptor)) { throw 'Desarrollo no tiene descriptor central.' }
            $devSettings = Get-Content -LiteralPath $devDescriptor -Raw | ConvertFrom-Json
            $source = $centralSource
            $target = Join-Path $devSettings.catalogDir $file
        }
        if ($file -eq 'anime-hoja.json' -and -not (Test-Path -LiteralPath $source)) { continue }
        $records = @(Get-Content -LiteralPath $source -Raw | ConvertFrom-Json)
        Copy-Item -LiteralPath $source -Destination $target -Force
        $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        if ($hash -ne (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash) { throw "Paridad fallida: $file" }
        $manifest.parity += [ordered]@{ file=$file; count=$records.Count; sha256=$hash }
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $snapshot 'manifest.json') -Encoding utf8
}
foreach ($deploymentFile in @('Iniciar-Altoidss.cmd', 'Iniciar-Catalogo-Central.ps1')) {
    $source = Join-Path $workspace $deploymentFile
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $snapshot ('deployment\' + $deploymentFile)
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
        if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) {
            throw 'No se pudo verificar el respaldo del arranque.'
        }
    }
}
Write-Output ("Snapshot verificado: {0}; archivos: {1}" -f $snapshot, $manifest.copies.Count)
$manifest.parity | ForEach-Object { Write-Output ("Paridad {0}: {1} registros" -f $_.file, $_.count) }
Write-Output 'Contiene datos privados: no publicar. No captura sesiones PHP ni verifica restauración completa.'
