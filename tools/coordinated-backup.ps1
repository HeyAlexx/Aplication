[CmdletBinding()]
param([Parameter(Mandatory=$true)][switch]$PauseAndResume,
      [string]$Workspace=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))),
      [string]$PythonBin='C:\Python313\python.exe', [string]$PhpBin='C:\xampp\php\php.exe')
$ErrorActionPreference='Stop'
if (!$PauseAndResume) { throw 'Se requiere autorización explícita para pausar y reanudar.' }
$workspaceRoot=(Resolve-Path -LiteralPath $Workspace).Path
if (![IO.Path]::GetPathRoot($workspaceRoot).Equals('C:\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Se esperaba el proyecto migrado en C:.' }
$diskC=Get-Partition -DriveLetter C
$diskF=Get-Partition -DriveLetter F
$diskG=Get-Partition -DriveLetter G -ErrorAction SilentlyContinue
$volumeF=Get-Volume -DriveLetter F
if ($diskC.DiskNumber -eq $diskF.DiskNumber -or ($diskG -and $diskG.DiskNumber -eq $diskF.DiskNumber) -or
    $volumeF.HealthStatus -ne 'Healthy' -or $volumeF.FileSystem -ne 'NTFS') { throw 'F: no cumple aislamiento/estado/NTFS requeridos.' }
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backupParent='F:\Altoidss-Backups'
if (!(Test-Path -LiteralPath $backupParent)) { New-Item -ItemType Directory -Path $backupParent | Out-Null }
if ((Get-Item -LiteralPath $backupParent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'El destino no puede ser una junction.' }
$backup=Join-Path $backupParent ($stamp+'-step5')
if (Test-Path -LiteralPath $backup) { throw 'La carpeta destino ya existe.' }
New-Item -ItemType Directory -Path $backup | Out-Null
$security=[Security.AccessControl.DirectorySecurity]::new()
$security.SetAccessRuleProtection($true,$false)
$backupOwner=[Security.Principal.WindowsIdentity]::GetCurrent().User
$security.SetOwner($backupOwner)
foreach ($principal in @($backupOwner,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
    $rule=[Security.AccessControl.FileSystemAccessRule]::new($principal,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    $security.AddAccessRule($rule)
}
Set-Acl -LiteralPath $backup -AclObject $security
if (!(Get-Acl -LiteralPath $backup).AreAccessRulesProtected) { throw 'No se protegió la carpeta privada.' }
$operations=Join-Path $workspaceRoot ('work\step5-operations\'+$stamp)
New-Item -ItemType Directory -Path $operations | Out-Null
$services=@(@{name='production';port=8091;bind='127.0.0.1';folder='ProyectoFinal'},
            @{name='development';port=8092;bind='0.0.0.0';folder='Desarrollo'})
$operator=[ordered]@{startedAt=(Get-Date -Format o);backup=$backup;physicalDisks=@{C=$diskC.DiskNumber;F=$diskF.DiskNumber;G=$diskG.DiskNumber};
    accessControlled=$true;encrypted=$false;paused=@();resumed=@();sheetsStarted=$false;status='PREPARING'}
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$estimateRaw=& $PythonBin (Join-Path $PSScriptRoot 'coordinated_recovery.py') preflight --workspace $workspaceRoot --backup $backup
if ($LASTEXITCODE -ne 0) { throw 'Falló el inventario previo; no se pausan servicios.' }
$estimate=($estimateRaw -join "`n") | ConvertFrom-Json
$required=[long]($estimate.totalBytes*1.1+2GB)
if ((Get-Volume -DriveLetter F).SizeRemaining -lt $required -or (Get-Volume -DriveLetter C).SizeRemaining -lt ($required+$estimate.totalBytes)) { throw 'Falta espacio para captura, respaldo y restauración.' }
Write-Output "Preflight: $($estimate.files) archivos, $($estimate.totalBytes) bytes; $($estimate.reparsePoints) enlaces excluidos."
if (@(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -match 'anime_sync_pipeline' }).Count) {
    throw 'Hay un monitor activo: no pausar ni respaldar hasta revisarlo.'
}
foreach ($service in $services) {
    $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $service.port -ErrorAction Stop)
    if ($listeners.Count -ne 1) { throw 'Se esperaba un servidor por puerto.' }
    $process=Get-CimInstance Win32_Process -Filter "ProcessId = $($listeners[0].OwningProcess)"
    if ($process.ExecutablePath -ne $PhpBin -or $process.CommandLine -notmatch ('-S '+[regex]::Escape($service.bind+':'+$service.port)) -or
        $process.CommandLine -notmatch 'server-router.php') { throw 'Proceso inesperado: no se detiene.' }
    $service.pid=$process.ProcessId
    $service.creation=$process.CreationDate
    $service.path=Join-Path $workspaceRoot ($service.folder+'\Aplication')
    $health=Invoke-WebRequest -Uri ('http://127.0.0.1:'+$service.port+'/api/index.php?route=/health') -TimeoutSec 10
    if ($health.StatusCode -ne 200) { throw 'El servidor no completó la comprobación previa.' }
}
$operator | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'operator.json') -Encoding utf8
$pausedServices=[Collections.Generic.List[object]]::new()
try {
    foreach ($service in $services) {
        $process=Get-CimInstance Win32_Process -Filter "ProcessId = $($service.pid)"
        if ($process.ExecutablePath -ne $PhpBin -or $process.CreationDate -ne $service.creation) { throw 'El proceso cambió; no se detiene.' }
        $pausedServices.Add($service)
        Stop-Process -Id $service.pid -Force -ErrorAction Stop
        Wait-Process -Id $service.pid -Timeout 15 -ErrorAction SilentlyContinue
        $operator.paused+=@{name=$service.name;pid=$service.pid;at=(Get-Date -Format o)}
    }
    if (@(Get-NetTCPConnection -State Listen -LocalPort 8091,8092 -ErrorAction SilentlyContinue).Count) { throw 'Queda un escritor HTTP activo.' }
    $operator.status='PAUSED_CAPTURING_TO_F'
    $operator | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'operator.json') -Encoding utf8
    Write-Output 'Servidores pausados. Capturando directamente en un archivo secuencial de F:...'
    & $PythonBin (Join-Path $PSScriptRoot 'coordinated_recovery.py') archive --workspace $workspaceRoot --backup $backup
    if ($LASTEXITCODE -ne 0) { throw 'El respaldo quedó incompleto; no usarlo para desplegar.' }
    $operator.status='INDEPENDENT_CAPTURE_VERIFIED'
} finally {
    $resumeErrors=[Collections.Generic.List[string]]::new()
    foreach ($service in $pausedServices) {
        $previousDescriptor=$env:ALTOIDSS_STORAGE_CONFIG
        try {
            $existing=@(Get-NetTCPConnection -State Listen -LocalPort $service.port -ErrorAction SilentlyContinue)
            if ($existing.Count) {
                if ($existing.Count -eq 1 -and $existing[0].OwningProcess -eq $service.pid) { continue }
                throw 'El puerto fue ocupado por otro proceso; no se detiene ese proceso.'
            }
            $env:ALTOIDSS_STORAGE_CONFIG=Join-Path $workspaceRoot ($service.folder+'\catalog-storage.local.json')
            $arguments=@('-S',($service.bind+':'+$service.port),'-t',$service.path,(Join-Path $service.path 'server-router.php'))
            $resumed=Start-Process -FilePath $PhpBin -ArgumentList $arguments -WorkingDirectory $service.path -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput (Join-Path $operations ($service.name+'.stdout.log')) `
                -RedirectStandardError (Join-Path $operations ($service.name+'.stderr.log'))
            $operator.resumed+=@{name=$service.name;pid=$resumed.Id;at=(Get-Date -Format o)}
        } catch { $resumeErrors.Add($service.name+': '+$_.Exception.Message) }
        finally { $env:ALTOIDSS_STORAGE_CONFIG=$previousDescriptor }
    }
    $operator | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'operator.json') -Encoding utf8
    if ($resumeErrors.Count) { throw ('Se intentó reanudar ambos servidores, pero hay fallos: '+($resumeErrors -join '; ')) }
}
foreach ($service in $services) {
    $ready=$false
    for ($attempt=0;$attempt -lt 20;$attempt++) {
        try { $ready=(Invoke-WebRequest -Uri ('http://127.0.0.1:'+$service.port+'/Html/catalogo.html') -TimeoutSec 2).StatusCode -eq 200 }
        catch { Start-Sleep -Milliseconds 250 }
        if ($ready) { break }
    }
    if (!$ready) { throw 'Se inició el proceso, pero no se confirmó el servicio; revisar logs antes de continuar.' }
}
Write-Output 'Ambos servidores reanudados. Copia independiente ya verificada en F:.'
Write-Output 'Ensayando restauración aislada desde F:...'
& $PythonBin (Join-Path $PSScriptRoot 'coordinated_recovery.py') restore --workspace $workspaceRoot --backup $backup --php $PhpBin
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo aislado; conservar el respaldo y revisar.' }
$operator.status='BACKUP_AND_RECOVERY_VERIFIED'
$operator.finishedAt=Get-Date -Format o
$operator | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'operator.json') -Encoding utf8
Write-Output "Paso 5 verificado: $backup"
