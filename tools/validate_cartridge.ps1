param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$romPath = Join-Path $ProjectRoot 'dist/abaqus-after-hours.sfc'
$manifestPath = Join-Path $ProjectRoot 'dist/manifest.json'
if (-not (Test-Path -LiteralPath $romPath -PathType Leaf)) { throw 'Build the ROM first with Build.cmd.' }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'The cartridge manifest is missing. Run Build.cmd first.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.title -ne 'Abaqus: After Hours' -or [string]$manifest.version -notmatch '^\d+\.\d+\.\d+$') {
    throw 'This folder does not contain a valid Abaqus cartridge manifest.'
}
$data = [IO.File]::ReadAllBytes($romPath)
if ($data.Length -ne 4194304 -or [int64]$manifest.bytes -ne $data.Length -or
    $data[0x7fd5] -ne 0x30 -or $data[0x7fd7] -ne 0x0c -or $data[0x7fd9] -ne 1) {
    throw 'The cartridge must be a 4 MiB NTSC FastROM LoROM. Run Build.cmd first.'
}
$digest = (Get-FileHash -LiteralPath $romPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($digest -ne [string]$manifest.sha256) { throw 'The cartridge differs from its manifest. Run Build.cmd first.' }
$versionHeader = Join-Path $ProjectRoot 'src/version.h'
if (Test-Path -LiteralPath $versionHeader -PathType Leaf) {
    $versions = [regex]::Matches((Get-Content -LiteralPath $versionHeader -Raw -Encoding UTF8),
        '(?m)^\s*#define\s+ABAQUS_GAME_VERSION\s+"([0-9]+\.[0-9]+\.[0-9]+)"\s*$')
    if ($versions.Count -ne 1 -or $versions[0].Groups[1].Value -ne [string]$manifest.version) {
        throw 'The cartridge version differs from this checkout. Run Build.cmd first.'
    }
}
[pscustomobject]@{ Version = [string]$manifest.version; RomPath = $romPath; Sha256 = $digest; Bytes = $data.Length } | ConvertTo-Json
