param(
    [string]$Source = 'E:\GPT\Inves\AA-AT-recovery-20261023\research\v3\ea\S04_MomentumProxy_v2.mq5',
    [string]$ResearchRoot = 'E:\GPT\Inves\AA-AT-v3-market-vault',
    [string]$StateRoot = 'E:\GPT\Inves\AA-AT-research-state\v3'
)
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath('E:\GPT\Inves\AA-AT-recovery-20261023\research\v3')
$sourcePath = [IO.Path]::GetFullPath($Source)
if (-not $sourcePath.StartsWith($sourceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'source_outside_research_allowlist'
}
$exe = Join-Path $ResearchRoot 'mt5-portable\MetaEditor64.exe'
if ((Get-AuthenticodeSignature -LiteralPath $exe).Status -ne 'Valid') { throw 'invalid_research_metaeditor_signature' }
$logDir = Join-Path $ResearchRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 's04-compile.log'
$env:APPDATA = Join-Path $ResearchRoot 'mt5-appdata'
$env:LOCALAPPDATA = Join-Path $ResearchRoot 'mt5-localappdata'
$env:TEMP = Join-Path $ResearchRoot 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:APPDATA,$env:LOCALAPPDATA,$env:TEMP | Out-Null
$arguments = @('/portable',('/compile:"' + $sourcePath + '"'),('/log:"' + $log + '"'))
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -Wait -PassThru
if (-not (Test-Path -LiteralPath $log)) { throw 'compiler_log_missing' }
$tail = Get-Content -LiteralPath $log -Tail 1
if ($tail -notmatch 'Result: 0 errors, 0 warnings') { throw "compiler_failed:$tail" }
$binary = [IO.Path]::ChangeExtension($sourcePath, '.ex5')
if (-not (Test-Path -LiteralPath $binary)) { throw 'compiled_ea_missing' }
$manifest = [ordered]@{
    schema_version = 1
    strategy_id = 'S04'
    source_path = $sourcePath
    source_sha256 = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    binary_path = $binary
    binary_sha256 = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
    compiler_path = $exe
    compiler_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    compiler_result = $tail
    process_exit_code = $process.ExitCode
    portable_mode = $true
    broker_orders_submitted = 0
}
$buildRoot = Join-Path $StateRoot 'builds'
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
$identity = 'S04-' + $manifest.source_sha256.Substring(0,16) + '-' + $manifest.binary_sha256.Substring(0,16)
$archiveBinary = Join-Path $buildRoot ($identity + '.ex5')
if (Test-Path -LiteralPath $archiveBinary) {
    if ((Get-FileHash -LiteralPath $archiveBinary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.binary_sha256) {
        throw 'archived_binary_identity_conflict'
    }
} else {
    $temporaryBinary = Join-Path $buildRoot ('.' + [guid]::NewGuid().ToString('N') + '.ex5')
    Copy-Item -LiteralPath $binary -Destination $temporaryBinary
    Move-Item -LiteralPath $temporaryBinary -Destination $archiveBinary
}
$manifest.binary_path = $archiveBinary
$manifest.working_binary_path = $binary
$target = Join-Path $buildRoot ($identity + '.json')
if (Test-Path -LiteralPath $target) {
    $prior = Get-Content -LiteralPath $target -Raw | ConvertFrom-Json
    if ($prior.binary_sha256 -ne $manifest.binary_sha256 -or $prior.source_sha256 -ne $manifest.source_sha256) {
        throw 'build_manifest_identity_conflict'
    }
} else {
    $temporary = Join-Path $buildRoot ('.' + [guid]::NewGuid().ToString('N') + '.json')
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding utf8
    Move-Item -LiteralPath $temporary -Destination $target
}
$manifest | ConvertTo-Json -Depth 4
