param(
    [string]$Vault = 'E:\GPT\Inves\AA-AT-v3-market-vault',
    [string]$State = 'E:\GPT\Inves\AA-AT-research-state\v3',
    [int]$TimeoutSeconds = 40
)
$ErrorActionPreference = 'Stop'
$expectedVault = [IO.Path]::GetFullPath('E:\GPT\Inves\AA-AT-v3-market-vault')
if ([IO.Path]::GetFullPath($Vault) -ne $expectedVault) { throw 'research_vault_allowlist_mismatch' }
if ($TimeoutSeconds -lt 10 -or $TimeoutSeconds -gt 60) { throw 'invalid_probe_timeout' }
$terminal = Join-Path $Vault 'mt5-portable\terminal64.exe'
$editor = Join-Path $Vault 'mt5-portable\MetaEditor64.exe'
$researchMeta = 'C:\Users\SOC-Peyman\AppData\Roaming\MetaQuotes\Terminal\A7806C9494F93E37A61F4174F2E3283B'
$origin = (Get-Content -LiteralPath (Join-Path $researchMeta 'origin.txt') -Raw).Trim()
if ([IO.Path]::GetFullPath($origin) -ne [IO.Path]::GetFullPath((Split-Path $terminal))) {
    throw 'research_terminal_metadata_origin_mismatch'
}
foreach ($accounts in @((Join-Path $researchMeta 'config\accounts.dat'),
                       (Join-Path (Split-Path $terminal) 'config\accounts.dat'))) {
    if (Test-Path -LiteralPath $accounts) { throw 'research_terminal_credentials_present' }
}
foreach ($exe in @($terminal,$editor)) {
    if ((Get-AuthenticodeSignature -LiteralPath $exe).Status -ne 'Valid') {
        throw 'research_terminal_signature_invalid'
    }
}
$existing = Get-CimInstance Win32_Process -Filter "name = 'terminal64.exe'" |
    Where-Object { $_.ExecutablePath -eq $terminal }
if ($existing) { throw 'research_terminal_already_running' }
$assistantConfig = Join-Path $Vault 'mt5-portable\config\assistant.ini'
if (Test-Path -LiteralPath $assistantConfig) {
    $assistantText = Get-Content -LiteralPath $assistantConfig -Raw
    if ($assistantText -match '(?im)^\s*(ApiKey\s*=|Enable\s*=\s*1\s*$|Endpoint\s*=)') {
        throw 'research_mcp_bridge_or_key_must_be_disabled'
    }
}
$source = 'E:\GPT\Inves\AA-AT-recovery-20261023\research\v3\ea\S04_MomentumProxy_v1.ex5'
$expertDir = Join-Path $Vault 'mt5-portable\MQL5\Experts\AAATV3'
New-Item -ItemType Directory -Path $expertDir -Force | Out-Null
$sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
$expertName = 'S04_MomentumProxy_' + $sourceHash.Substring(0,16)
$expert = Join-Path $expertDir ($expertName + '.ex5')
if (Test-Path -LiteralPath $expert) {
    if ($sourceHash -ne (Get-FileHash -LiteralPath $expert -Algorithm SHA256).Hash.ToLowerInvariant()) {
        throw 'research_ea_binary_conflict'
    }
} else { Copy-Item -LiteralPath $source -Destination $expert }
$configDir = Join-Path $Vault 'config'
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
$config = Join-Path $configDir 'tester-probe.ini'
$ini = @'
[Common]
ProxyEnable=1
ProxyAddress=127.0.0.1:9
NewsEnable=0
KeepPrivate=0
[Experts]
AllowLiveTrading=0
AllowDllImport=0
Enabled=1
[Tester]
Expert=AAATV3\__EXPERT_NAME__
Symbol=AAATV3_NO_DATA
Period=M1
Model=0
Optimization=0
FromDate=2024.01.15
ToDate=2024.01.16
UseCloud=0
Visual=0
Report=reports\tester-probe
ReplaceReport=1
ShutdownTerminal=1
'@
$ini = $ini.Replace('__EXPERT_NAME__', $expertName)
$ini | Set-Content -LiteralPath $config -Encoding ascii
$env:APPDATA = Join-Path $Vault 'mt5-appdata'
$env:LOCALAPPDATA = Join-Path $Vault 'mt5-localappdata'
$env:TEMP = Join-Path $Vault 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:APPDATA,$env:LOCALAPPDATA,$env:TEMP -Force | Out-Null
$args = @('/portable',('/config:"' + $config + '"'))
$process = Start-Process -FilePath $terminal -ArgumentList $args -WorkingDirectory (Split-Path $terminal) -WindowStyle Hidden -PassThru
$timedOut = $false
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    $timedOut = $true
    $running = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $process.Id)
    if ($running -and $running.ExecutablePath -eq $terminal) {
        Stop-Process -Id $process.Id -Force
    } else { throw 'probe_process_identity_uncertain' }
}
$logs = Get-ChildItem -LiteralPath (Join-Path $Vault 'mt5-portable\logs') -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 2
$testerLogs = Get-ChildItem -LiteralPath (Join-Path $Vault 'mt5-portable\Tester\logs') -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 2
$summary = [ordered]@{
    schema_version = 1
    observed_utc = (Get-Date -AsUTC -Format o)
    research_terminal_path = $terminal
    research_terminal_sha256 = (Get-FileHash -LiteralPath $terminal -Algorithm SHA256).Hash.ToLowerInvariant()
    research_config_path = $config
    research_config_sha256 = (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash.ToLowerInvariant()
    research_expert_sha256 = (Get-FileHash -LiteralPath $expert -Algorithm SHA256).Hash.ToLowerInvariant()
    launched_pid = $process.Id
    timed_out = $timedOut
    process_exited = (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue))
    terminal_log_names = @($logs | ForEach-Object Name)
    tester_log_names = @($testerLogs | ForEach-Object Name)
    data_symbol = 'AAATV3_NO_DATA'
    account_file_present = ((Test-Path -LiteralPath (Join-Path $researchMeta 'config\accounts.dat')) -or
                            (Test-Path -LiteralPath (Join-Path (Split-Path $terminal) 'config\accounts.dat')))
    historical_trades_claimed = 0
    note = 'Probe only. Missing custom-symbol history is expected; no baseline claim.'
}
$output = Join-Path $State 'tester-probe.json'
$temporary = Join-Path $State ('.tester-probe-' + [guid]::NewGuid().ToString('N') + '.json')
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporary -Encoding utf8
Move-Item -LiteralPath $temporary -Destination $output -Force
$summary | ConvertTo-Json -Depth 5
