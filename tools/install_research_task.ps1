param(
    [string]$TaskName = 'aa-at-research-collector',
    [string]$ReleasePath = 'E:\GPT\Inves\AA-AT-research-release-v1',
    [string]$Python = 'E:\GPT\Inves\AA-AT-research-venv\Scripts\pythonw.exe'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python) -or
    -not (Test-Path -LiteralPath (Join-Path $ReleasePath 'research\trade_forensics\collector.py'))) {
    throw 'Verified isolated research release and Python environment are required.'
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $Python -Argument '-m research.trade_forensics.collector --serve --interval 300' -WorkingDirectory $ReleasePath
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds 0)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force -ErrorAction Stop | Out-Null
Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Select-Object TaskName,State
