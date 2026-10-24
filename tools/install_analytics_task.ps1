param(
    [string]$TaskName = 'aa-at-daily-analytics',
    [string]$ReleasePath = 'E:\GPT\Inves\AA-AT-analytics-release-v1',
    [string]$Python = 'E:\GPT\Inves\AA-AT-research-venv\Scripts\pythonw.exe',
    [Parameter(Mandatory=$true)][string]$GitCommit
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python) -or
    -not (Test-Path -LiteralPath (Join-Path $ReleasePath 'research\trade_forensics\daily_analytics.py'))) {
    throw 'Validated isolated analytics release and Python are required.'
}
if ($GitCommit -notmatch '^[0-9a-f]{40}$') { throw 'Invalid Git commit' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$argument = '-m research.trade_forensics.daily_analytics --git-commit ' + $GitCommit
$action = New-ScheduledTaskAction -Execute $Python -Argument $argument -WorkingDirectory $ReleasePath
$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $identity),
    (New-ScheduledTaskTrigger -Daily -At 2:30AM)
)
$settings = New-ScheduledTaskSettingsSet -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Force -ErrorAction Stop | Out-Null
Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Select-Object TaskName,State
