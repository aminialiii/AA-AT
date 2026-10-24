param(
    [string]$TaskName = 'aa-at-backup-worker',
    [string]$ReleasePath = 'E:\GPT\Inves\AA-AT-backup-release-v1',
    [string]$BackupPath = 'D:\AA-AT-Backups'
)

$ErrorActionPreference = 'Stop'
$python = 'C:\Users\SOC-Peyman\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe'
$script = Join-Path $ReleasePath 'backup_worker.py'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $script)) {
    throw 'Verified Python and backup-worker release are required before installation.'
}
if (-not (Test-Path -LiteralPath (Join-Path $BackupPath 'AA-AT-Backup-V1.zip'))) {
    throw 'The initial verified V1 backup is required before scheduling.'
}
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '" --serve') -WorkingDirectory $ReleasePath
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$startup = New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds 0)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $startup -Settings $settings -Principal $principal -Force -ErrorAction Stop | Out-Null
Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Select-Object TaskName,State
