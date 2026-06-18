param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Version = "0.1.7"
$SidecarSource = Join-Path $Backend "dist\living-to-tell-backend.exe"
$SidecarTarget = Join-Path $Frontend "src-tauri\binaries\living-to-tell-backend-x86_64-pc-windows-msvc.exe"
$ReleaseExe = Join-Path $Frontend "src-tauri\target\release\living-to-tell-app.exe"
$NsisDir = Join-Path $Frontend "src-tauri\target\release\bundle\nsis"
$MsiDir = Join-Path $Frontend "src-tauri\target\release\bundle\msi"
$EnglishNsis = Join-Path $NsisDir ("LivingToTell_{0}_x64-setup.exe" -f $Version)
$EnglishMsi = Join-Path $MsiDir ("LivingToTell_{0}_x64_zh-CN.msi" -f $Version)

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
