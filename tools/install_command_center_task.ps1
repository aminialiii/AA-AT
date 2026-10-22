param([switch]$StartNow)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stateDir = Join-Path (Split-Path $repoRoot -Parent) 'AA-AT-command-center-state'
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$pythonwExe = Join-Path (Split-Path $pythonExe -Parent) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonwExe)) { throw 'pythonw.exe is required for quiet task operation' }
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$authPath = Join-Path $stateDir 'auth_hashes.json'
if (-not (Test-Path -LiteralPath $authPath)) {
    Push-Location $repoRoot
    try { & $pythonExe -m command_center.server --init-auth | Out-Null }
    finally { Pop-Location }
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $stateDir /inheritance:r /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Unable to restrict dashboard secret directory ACL' }
$taskName = 'AAATCommandCenter'
$action = New-ScheduledTaskAction -Execute $pythonwExe -Argument '-m command_center.launcher' -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
if ($StartNow) { Start-ScheduledTask -TaskName $taskName }
[pscustomobject]@{Task=$taskName;Url='http://127.0.0.1:8765/';AuthFile=(Join-Path $stateDir 'access_keys.txt');Started=[bool]$StartNow} | ConvertTo-Json -Compress
