param(
    [ValidateSet('dev', 'prepare', 'check', 'login', 'deploy')]
    [string]$Action = 'dev'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskVersion = '24.22.1'
$taskArchiveHash = 'D2046D28C2C3DCD211AC5145C0BF30E2047EF9DFB306693C8C6E2ECCD8B95FA5'
$taskExeHash = 'D702DAA815EABBFF763C7D3808E235CF031CF2CA70211B56847BC72F51E240E5'
$taskTools = Join-Path $taskRoot '.tools/node'
$taskArchiveName = "node-v$taskVersion-win-x64.zip"
$taskArchive = Join-Path $taskTools $taskArchiveName
$taskNodeDir = Join-Path $taskTools "node-v$taskVersion-win-x64"
$taskNode = Join-Path $taskNodeDir 'node.exe'

if (-not (Test-Path -LiteralPath $taskArchive)) {
    New-Item -ItemType Directory -Force -Path $taskTools | Out-Null
    Write-Host "Downloading project-local Node $taskVersion..."
    Invoke-WebRequest -UseBasicParsing -Uri "https://nodejs.org/dist/v$taskVersion/$taskArchiveName" -OutFile $taskArchive
}
if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash -ne $taskArchiveHash) {
    throw 'Node archive SHA-256 does not match the official pin.'
}
if (-not (Test-Path -LiteralPath $taskNode) -or (Get-FileHash -LiteralPath $taskNode -Algorithm SHA256).Hash -ne $taskExeHash) {
    Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskTools -Force
}
if ((Get-FileHash -LiteralPath $taskNode -Algorithm SHA256).Hash -ne $taskExeHash) {
    throw 'Expanded Node executable SHA-256 does not match the official pin.'
}
$env:PATH = "$taskNodeDir;$env:PATH"
$env:WRANGLER_SEND_METRICS = 'false'
Push-Location $taskRoot
try {
    if ($Action -ne 'login') {
        & $taskNode tools/build_web.mjs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    if ($Action -eq 'prepare') { exit 0 }

    $taskLock = (Get-FileHash -LiteralPath 'package-lock.json' -Algorithm SHA256).Hash
    $taskMarker = Join-Path $taskRoot '.tools/web/npm-lock.sha256'
    $taskWrangler = Join-Path $taskRoot 'node_modules/wrangler/bin/wrangler.js'
    if (-not (Test-Path -LiteralPath $taskWrangler) -or -not (Test-Path -LiteralPath $taskMarker) -or (Get-Content -LiteralPath $taskMarker -Raw).Trim() -ne $taskLock) {
        & $taskNode "$taskNodeDir/node_modules/npm/bin/npm-cli.js" ci --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $taskMarker) | Out-Null
        Set-Content -LiteralPath $taskMarker -Value $taskLock -Encoding ascii
    }
    switch ($Action) {
        'dev' { & $taskNode $taskWrangler dev --ip 127.0.0.1 --port 8787 }
        'check' { & $taskNode $taskWrangler deploy --dry-run --outdir build/cloudflare/dry-run }
        'login' { & $taskNode $taskWrangler login }
        'deploy' { & $taskNode $taskWrangler deploy }
    }
    exit $LASTEXITCODE
}
finally { Pop-Location }
