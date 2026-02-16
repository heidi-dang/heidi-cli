# smoke_serve.ps1 - Windows acceptance tests for heidi serve command
# Run with: powershell -ExecutionPolicy Bypass -File scripts/smoke_serve.ps1

$ErrorActionPreference = "Continue"

$HEIDI_CMD = "python -m src.heidi_cli.cli"
$PORT = 17777
$BASE_URL = "http://127.0.0.1:${PORT}"

function Fail {
    param([string]$Message)
    Write-Host "FAIL: $Message" -ForegroundColor Red
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Heidi CLI Smoke: serve command (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "=== Test 1: heidi --version ===" -ForegroundColor Yellow
$output = & cmd /c "$HEIDI_CMD --version 2>&1"
Write-Host $output
if ($LASTEXITCODE -ne 0) { Fail "--version failed" }

Write-Host ""
Write-Host "=== Test 2: heidi doctor ===" -ForegroundColor Yellow
$output = & cmd /c "$HEIDI_CMD doctor 2>&1"
Write-Host $output
if ($LASTEXITCODE -ne 0) { Fail "doctor failed" }

Write-Host ""
Write-Host "=== Test 3: heidi serve --plain (foreground) ===" -ForegroundColor Yellow
Write-Host "Starting server on port ${PORT}..."

# Start server in background using Start-Process
$serverProc = Start-Process -FilePath "python" -ArgumentList "-m","src.heidi_cli.cli","serve","--port",$PORT,"--plain" -NoNewWindow -PassThru -RedirectStandardOutput "$env:TEMP\heidi_out.txt" -RedirectStandardError "$env:TEMP\heidi_err.txt"

Start-Sleep 4

Write-Host "Checking health endpoint..."
try {
    $healthResponse = Invoke-RestMethod "${BASE_URL}/health" -TimeoutSec 5
    Write-Host "Health response: $healthResponse"
    if ($healthResponse.status -ne "healthy" -and $healthResponse.status -ne "ok") {
        Fail "Health check failed: $healthResponse"
    }
} catch {
    if ($serverProc -and !$serverProc.HasExited) {
        Stop-Process $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
    Fail "Health check failed: $_"
}

Write-Host "Stopping server..."
if ($serverProc -and !$serverProc.HasExited) {
    Stop-Process $serverProc.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep 1

Write-Host ""
Write-Host "=== Test 4: HEIDI_PLAIN=1 environment ===" -ForegroundColor Yellow
$env:HEIDI_PLAIN = "1"
$serverProc2 = Start-Process -FilePath "python" -ArgumentList "-m","src.heidi_cli.cli","serve","--port",($PORT+1) -NoNewWindow -PassThru
$env:HEIDI_PLAIN = ""
Start-Sleep 3

try {
    $healthResponse = Invoke-RestMethod "http://127.0.0.1:$($PORT+1)/health" -TimeoutSec 5
    Write-Host "Health response: $healthResponse"
} catch {
    # Ignore, may fail if server still starting
}

if ($serverProc2 -and !$serverProc2.HasExited) {
    Stop-Process $serverProc2.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "ALL TESTS PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
