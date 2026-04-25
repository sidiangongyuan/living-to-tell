param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$specPath = Join-Path $repoRoot "writer.spec"
$versionFile = Join-Path $repoRoot "src\writer\app\version.py"
$distDir = Join-Path $repoRoot "dist"
$bundleDir = Join-Path $distDir "Writer"
$zipPath = Join-Path $distDir "Writer-portable.zip"

function Get-AppVersion {
    param(
        [string]$VersionFilePath
    )

    if (-not (Test-Path $VersionFilePath)) {
        throw "version.py not found at $VersionFilePath"
    }

    $content = Get-Content $VersionFilePath -Raw
    $match = [regex]::Match($content, 'APP_VERSION\s*=\s*"([^"]+)"')
    if (-not $match.Success) {
        throw "Could not extract APP_VERSION from $VersionFilePath"
    }
    return $match.Groups[1].Value
}

function Compress-ArchiveWithRetry {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [int]$MaxAttempts = 5,
        [int]$DelayMilliseconds = 1000
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            if (Test-Path $DestinationPath) {
                Remove-Item $DestinationPath -Force
            }

            Compress-Archive -Path $SourcePath -DestinationPath $DestinationPath -Force -ErrorAction Stop
            return
        }
        catch {
            if ($attempt -ge $MaxAttempts) {
                throw
            }

            [System.Threading.Thread]::Sleep($DelayMilliseconds)
        }
    }
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $specPath)) {
        throw "writer.spec not found at $specPath"
    }

    $appVersion = Get-AppVersion -VersionFilePath $versionFile
    $versionedZipPath = Join-Path $distDir ("Writer-" + $appVersion + "-portable.zip")

    # Clean previous build artefacts so PyInstaller always does a full rebuild.
    foreach ($d in @("build", $bundleDir)) {
        if (Test-Path $d) { Remove-Item $d -Recurse -Force }
    }
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    if (Test-Path $versionedZipPath) { Remove-Item $versionedZipPath -Force }

    & $PythonExe -m PyInstaller $specPath --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    $exePath = Join-Path $bundleDir "Writer.exe"
    if (-not (Test-Path $exePath)) {
        throw "Expected executable was not created: $exePath"
    }

    Compress-ArchiveWithRetry -SourcePath (Join-Path $bundleDir "*") -DestinationPath $versionedZipPath
    Copy-Item -Path $versionedZipPath -Destination $zipPath -Force

    Write-Output ""
    Write-Output "=== Build complete ==="
    Write-Output "  Version: $appVersion"
    Write-Output "  Bundle : $bundleDir"
    Write-Output "  Exe    : $exePath"
    Write-Output "  Zip    : $versionedZipPath"
    Write-Output "  Alias  : $zipPath"
    Write-Output ""
    Write-Output "The bundle uses a custom runtime hook (hooks/rthook_pyside6_dlls.py)"
    Write-Output "to add PySide6/ and shiboken6/ subdirectories to the DLL search path"
    Write-Output "before Qt modules are imported. This is required on Python 3.8+ where"
    Write-Output "PATH is no longer used for extension-module DLL resolution."
}
finally {
    Pop-Location
}