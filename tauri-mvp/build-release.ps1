param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$SidecarSource = Join-Path $Backend "dist\writer-backend.exe"
$SidecarTarget = Join-Path $Frontend "src-tauri\binaries\writer-backend-x86_64-pc-windows-msvc.exe"

Write-Host "Building Python sidecar..."
Push-Location $Backend
try {
    & $PythonExe -m PyInstaller writer-backend.spec --clean --noconfirm
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
    npm run tauri build
}
finally {
    Pop-Location
}

Write-Host "Release artifacts:"
Get-Item `
    (Join-Path $Frontend "src-tauri\target\release\writer-app.exe"), `
    (Join-Path $Frontend "src-tauri\target\release\bundle\nsis\Writer_*_x64-setup.exe"), `
    (Join-Path $Frontend "src-tauri\target\release\bundle\msi\Writer_*_x64_en-US.msi") |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 6 FullName, Length, LastWriteTime |
    Format-Table -AutoSize
