# Quick start script for Tauri MVP (development mode)
# Run from tauri-mvp directory: .\start-dev.ps1

Write-Host "=== Starting Living to Tell Tauri preview (development) ===" -ForegroundColor Cyan
Write-Host ""

# Start backend in background
Write-Host "[1/2] Starting FastAPI backend on :8000..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\backend"
    & python run.py --dev
}

# Wait for backend to be ready
Write-Host "Waiting for backend to start..."
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $response = Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Backend ready" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    Write-Host "⚠ Backend didn't start in time, but continuing anyway..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/2] Starting Vue frontend on :1420..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Open http://localhost:1420 in your browser" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Cyan
Write-Host ""

try {
    Set-Location frontend
    npm run dev
} finally {
    # Cleanup
    Write-Host ""
    Write-Host "Stopping backend..." -ForegroundColor Yellow
    Stop-Job $backendJob
    Remove-Job $backendJob
}
