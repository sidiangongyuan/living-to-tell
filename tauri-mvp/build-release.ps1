param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$TauriConfig = Join-Path $Frontend "src-tauri\tauri.conf.json"
$Version = (Get-Content -Raw -LiteralPath $TauriConfig | ConvertFrom-Json).version
$SidecarSource = Join-Path $Backend "dist\living-to-tell-backend.exe"
$SidecarTarget = Join-Path $Frontend "src-tauri\binaries\living-to-tell-backend-x86_64-pc-windows-msvc.exe"
$ReleaseExe = Join-Path $Frontend "src-tauri\target\release\living-to-tell-app.exe"
$NsisDir = Join-Path $Frontend "src-tauri\target\release\bundle\nsis"
$MsiDir = Join-Path $Frontend "src-tauri\target\release\bundle\msi"
$EnglishNsis = Join-Path $NsisDir ("LivingToTell_{0}_x64-setup.exe" -f $Version)
$EnglishMsi = Join-Path $MsiDir ("LivingToTell_{0}_x64_zh-CN.msi" -f $Version)
$InstalledBackend = Join-Path $env:LOCALAPPDATA "活着为了讲述\living-to-tell-backend.exe"

function Get-ArtifactSummary {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path $Path)) {
        return [PSCustomObject]@{
            FullName = $Path
            Length = $null
            LastWriteTime = $null
            SHA256 = "<missing>"
        }
    }

    $item = Get-Item -LiteralPath $Path
    $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
    [PSCustomObject]@{
        FullName = $item.FullName
        Length = $item.Length
        LastWriteTime = $item.LastWriteTime
        SHA256 = $hash.Hash
    }
}

foreach ($staleArtifact in @($EnglishNsis, $EnglishMsi)) {
    if (Test-Path $staleArtifact) {
        Remove-Item -LiteralPath $staleArtifact -Force
    }
}

Write-Host "Building Python sidecar..."
Push-Location $Backend
try {
    & $PythonExe -m PyInstaller living-to-tell-backend.spec --clean --noconfirm
}
finally {
    Pop-Location
}

if (-not (Test-Path $SidecarSource)) {
    throw "Sidecar build failed: $SidecarSource was not created."
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SidecarTarget) | Out-Null
Copy-Item -LiteralPath $SidecarSource -Destination $SidecarTarget -Force

$sourceHash = Get-FileHash -LiteralPath $SidecarSource -Algorithm SHA256
$targetHash = Get-FileHash -LiteralPath $SidecarTarget -Algorithm SHA256
if ($sourceHash.Hash -ne $targetHash.Hash) {
    throw "Sidecar hash mismatch after copy. Source=$($sourceHash.Hash) Target=$($targetHash.Hash)"
}

Write-Host "Sidecar source/target:"
@(
    Get-ArtifactSummary $SidecarSource
    Get-ArtifactSummary $SidecarTarget
) | Format-Table -AutoSize

Write-Host "Building Tauri installer..."
Push-Location $Frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "npm run build failed with exit code $LASTEXITCODE."
    }
    npm run tauri build
    if ($LASTEXITCODE -ne 0) {
        throw "npm run tauri build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

if (Test-Path $NsisDir) {
    $nsisInstaller = Get-ChildItem -LiteralPath $NsisDir -Filter "*_x64-setup.exe" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($nsisInstaller -and $nsisInstaller.FullName -ne $EnglishNsis) {
        Copy-Item -LiteralPath $nsisInstaller.FullName -Destination $EnglishNsis -Force
    }
}

if (Test-Path $MsiDir) {
    $msiInstaller = Get-ChildItem -LiteralPath $MsiDir -Filter "*_x64_zh-CN.msi" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($msiInstaller -and $msiInstaller.FullName -ne $EnglishMsi) {
        Copy-Item -LiteralPath $msiInstaller.FullName -Destination $EnglishMsi -Force
    }
}

Write-Host "Release artifacts:"
Get-Item `
    $ReleaseExe, `
    $EnglishNsis, `
    $EnglishMsi |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 6 FullName, Length, LastWriteTime |
    Format-Table -AutoSize

Write-Host "Backend artifact hashes:"
@(
    Get-ArtifactSummary $SidecarSource
    Get-ArtifactSummary $SidecarTarget
    Get-ArtifactSummary $InstalledBackend
) | Format-Table -AutoSize
