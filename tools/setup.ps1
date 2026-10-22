param([switch]$EmulatorOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cacheRoot = Join-Path $projectRoot '.tools'
New-Item -ItemType Directory -Force $cacheRoot | Out-Null
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-PinnedArchive([string]$Url,[string]$Name,[string]$Hash,[string]$Destination,[string]$Marker,[string]$MemberHash='') {
    $archivePath = Join-Path $cacheRoot $Name
    if (-not (Test-Path -LiteralPath $archivePath)) {
        Write-Host "Downloading $Name from its official release..."
        & curl.exe -L --fail --silent --show-error $Url -o $archivePath
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $Name" }
    }
    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($actualHash -ne $Hash.ToUpperInvariant()) { throw "SHA256 mismatch: $Name" }

    # A stale marker is not proof that the expanded file is still the pinned
    # member.  Re-expand from the verified archive when the member is missing
    # or has been changed in place.
    $markerPath = Join-Path $cacheRoot $Marker
    $needsExpansion = -not (Test-Path -LiteralPath $markerPath -PathType Leaf)
    if (-not $needsExpansion -and $MemberHash) {
        $memberActualHash = (Get-FileHash -LiteralPath $markerPath -Algorithm SHA256).Hash.ToUpperInvariant()
        $needsExpansion = $memberActualHash -ne $MemberHash.ToUpperInvariant()
    }
    if ($needsExpansion) {
        Expand-Archive -LiteralPath $archivePath -DestinationPath (Join-Path $cacheRoot $Destination) -Force
    }
    if ($MemberHash) {
        if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
            throw "Pinned archive member was not expanded: $Marker"
        }
        $memberActualHash = (Get-FileHash -LiteralPath $markerPath -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($memberActualHash -ne $MemberHash.ToUpperInvariant()) {
            throw "Expanded member SHA256 mismatch: $Marker"
        }
    }
}

Get-PinnedArchive 'https://github.com/snes9xgit/snes9x/releases/download/1.63/snes9x-1.63-win32-x64.zip' 'snes9x.zip' 'E2BD103819051EAE57D163CDBBF6B3B92DB73FDD4A6A0EE6A939E507EAA95DB8' 'snes9x' 'snes9x/snes9x-x64.exe' 'C843D906C1FA1FEFA672E99CFD218041D229EF7598BCE720465FE7A0905F3A4B'
if ($EmulatorOnly) { return }
Get-PinnedArchive 'https://github.com/alekmaul/pvsneslib/releases/download/4.6.0/pvsneslib_460_64b_windows_release.zip' 'pvsneslib.zip' 'BFB651671AF99CD0FDC64A469A3E9CBFF53DEE9C3E0B27879E15495E2DE4F78E' 'sdk' 'sdk/pvsneslib/devkitsnes/bin/816-tcc.exe'
Get-PinnedArchive 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' 'python.zip' '4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3' 'python' 'python/python.exe'
Get-PinnedArchive 'https://github.com/snes9xgit/snes9x/releases/download/1.63/snes9x-1.63-libretro-x64.zip' 'core.zip' 'F3E88AE8540840C838DBCD57715134809894C9FD31D389E613409923AC23EA4E' 'core' 'core/snes9x_libretro.dll'
$pythonExe = Join-Path $cacheRoot 'python/python.exe'
$pathConfig = Join-Path $cacheRoot 'python/python312._pth'
(Get-Content -LiteralPath $pathConfig) -replace '#import site','import site' | Set-Content -LiteralPath $pathConfig
& $pythonExe -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('PIL') else 1)"
if ($LASTEXITCODE -ne 0) {
    $pipInstaller = Join-Path $cacheRoot 'python/get-pip.py'
    & curl.exe -L --fail --silent --show-error 'https://bootstrap.pypa.io/get-pip.py' -o $pipInstaller
    if ($LASTEXITCODE -ne 0) { throw 'Could not download pip.' }
    & $pythonExe $pipInstaller --no-warn-script-location
    if ($LASTEXITCODE -ne 0) { throw 'Could not install pip.' }
    & $pythonExe -m pip install 'Pillow==13.0.0' --no-warn-script-location
    if ($LASTEXITCODE -ne 0) { throw 'Could not install Pillow.' }
}
Write-Host 'Project-local SNES development tools are ready.'
