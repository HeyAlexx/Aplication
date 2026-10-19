[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Snapshot)
$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$snapshotRoot=[IO.Path]::GetFullPath((Join-Path $workspace 'work\preproduction-snapshots'))
$source=[IO.Path]::GetFullPath($Snapshot)
if (!$source.StartsWith($snapshotRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'El snapshot debe estar dentro del directorio de respaldos de este workspace.'
}
if (!(Test-Path -LiteralPath (Join-Path $source 'manifest.json'))) {throw 'Falta el manifiesto del snapshot.'}
$destination=Join-Path $workspace ('work\recovery-drills\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$report=[ordered]@{timestamp=(Get-Date -Format o);snapshot=$source;destination=$destination;productionModified=$false;checks=@()}
foreach($environment in @('production','development')) {
    $target=Join-Path $destination $environment
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    foreach($file in @('anime.json','peliculas.json','series.json','noticias.json')) {
        $original=Join-Path $source "$environment\data\$file"
        $centralOriginal=Join-Path $source "$environment-central\catalogo\$file"
        if(Test-Path -LiteralPath $centralOriginal){$original=$centralOriginal}
        $restored=Join-Path $target $file
        Copy-Item -LiteralPath $original -Destination $restored
        $hash=(Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash
        if($hash -ne (Get-FileHash -LiteralPath $restored -Algorithm SHA256).Hash) {throw "Recuperación no verificada: $environment/$file"}
        $records=@(Get-Content -LiteralPath $restored -Raw | ConvertFrom-Json)
        $report.checks += [ordered]@{environment=$environment;file=$file;sha256=$hash;records=$records.Count;passed=$true}
    }
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $destination 'report.json') -Encoding utf8
Write-Output "OK: ocho JSON recuperados y verificados en $destination; instalaciones reales sin modificaciones."
