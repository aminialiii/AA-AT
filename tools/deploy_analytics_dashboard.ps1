param(
    [string]$TaskName = 'AAATCommandCenter',
    [string]$NewRelease = 'E:\GPT\Inves\AA-AT-dashboard-release-analytics-v1',
    [Parameter(Mandatory=$true)][string]$ExpectedRunId
)
$ErrorActionPreference = 'Stop'
if ($ExpectedRunId -notmatch '^[0-9a-f]{20}$') { throw 'Invalid analysis run ID' }
foreach ($relative in @('command_center\server.py','docs\dashboard.html','docs\assets\research.js')) {
    if (-not (Test-Path -LiteralPath (Join-Path $NewRelease $relative))) {
        throw "Dashboard release incomplete: $relative"
    }
}
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$oldAction = $task.Actions[0]
$oldRelease = $oldAction.WorkingDirectory
if ($oldRelease -eq $NewRelease) { throw 'Dashboard already points to this release' }
$tradingBefore = (Get-ScheduledTask -TaskName 'CodexDemoForward20261021' -ErrorAction Stop).State.ToString()
$newAction = New-ScheduledTaskAction -Execute $oldAction.Execute -Argument $oldAction.Arguments -WorkingDirectory $NewRelease
$tokenFile = 'E:\GPT\Inves\AA-AT-command-center-state\access_keys.txt'
$viewer = (Get-Content -LiteralPath $tokenFile | Where-Object { $_ -match '^viewer:\s*\S+' } | Select-Object -First 1) -replace '^viewer:\s*',''
if (-not $viewer) { throw 'Viewer token unavailable for post-deployment verification' }
try {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    Start-Sleep -Seconds 2
    Set-ScheduledTask -TaskName $TaskName -Action $newAction -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $verified = $false
    for ($attempt=0; $attempt -lt 15; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 2
            $analysis = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/research/analysis' -TimeoutSec 3 -Headers @{Authorization="Bearer $viewer"}
            $status = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 3 -Headers @{Authorization="Bearer $viewer"}
            if ($health.status -eq 'RUNNING' -and $analysis.analysis_run_id -eq $ExpectedRunId -and
                ((-not $status.stale) -or ($status.broker_status -eq 'STALE' -and -not $status.demo_verified))) {
                $verified = $true
                break
            }
        } catch { }
    }
    if (-not $verified) { throw 'Dashboard post-deployment health/auth/stale-data check failed' }
    $tradingAfter = (Get-ScheduledTask -TaskName 'CodexDemoForward20261021' -ErrorAction Stop).State.ToString()
    [pscustomobject]@{
        status='SUCCESS';release=$NewRelease;rollback_release=$oldRelease;
        analysis_run_id=$ExpectedRunId;dashboard_url='http://127.0.0.1:8765/';
        broker_stale=$status.stale;broker_status=$status.broker_status;
        trading_task_before=$tradingBefore;trading_task_after=$tradingAfter
    } | ConvertTo-Json -Compress
} catch {
    $failure = $_.Exception.Message
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Set-ScheduledTask -TaskName $TaskName -Action $oldAction -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    throw "Dashboard release rolled back: $failure"
}
