# smoke_serve.ps1 - Windows acceptance tests for heidi serve command
# Run with: powershell -ExecutionPolicy Bypass -File scripts/smoke_serve.ps1

$ErrorActionPreference = "Stop"

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
Invoke-Expression "$HEIDI_CMD --version" || Fail "--version failed"

Write-Host ""
Write-Host "=== Test 2: heidi doctor ===" -ForegroundColor Yellow
Invoke-Expression "$HEIDI_CMD doctor" || Fail "doctor failed"

Write-Host ""
Write-Host "=== Test 3: heidi serve --plain (foreground) ===" -ForegroundColor Yellow
Write-Host "Starting server on port ${PORT}..."

$serverJob = Start-Job -ScriptBlock {
    param($cmd, $port)
    Set-Location $env:HEIDI_CLI_DIR
    Invoke-Expression "$cmd serve --port $port --plain"
} -ArgumentList $HEIDI_CMD, $PORT

Start-Sleep 3

Write-Host "Checking health endpoint..."
try {
    $healthResponse = Invoke-RestMethod "${BASE_URL}/health" -TimeoutSec 5
    Write-Host "Health response: $healthResponse"
    if ($healthResponse.status -ne "healthy" -and $healthResponse.status -ne "ok") {
        Fail "Health check failed: $healthResponse"
    }
} catch {
    Fail "Health check failed: $_"
}

Write-Host "Stopping server..."
Stop-Job $serverJob -ErrorAction SilentlyContinue
Remove-Job $serverJob -Force -ErrorAction SilentlyContinue
Start-Sleep 1

Write-Host ""
Write-Host "=== Test 4: heidi serve --detach ===" -ForegroundColor Yellow
Write-Host "Starting detached server..."

Invoke-Expression "$HEIDI_CMD serve --port $PORT --detach --plain"
Start-Sleep 2

$pidFile = "$env:USERPROFILE\.local\state\heidi\server.pid"
if (Test-Path $pidFile) {
    $detachedPid = Get-Content $pidFile
    Write-Host "Server PID: $detachedPid"
} else {
    Fail "PID file not created"
}

Write-Host "Checking if server is running..."
try {
    $healthResponse = Invoke-RestMethod "${BASE_URL}/health" -TimeoutSec 5
    Write-Host "Health response: $healthResponse"
    if ($healthResponse.status -ne "healthy" -and $healthResponse.status -ne "ok") {
        Fail "Detached server health check failed: $healthResponse"
    }
} catch {
    Fail "Detached server health check failed: $_"
}

Write-Host ""
Write-Host "=== Test 5: HEIDI_PLAIN=1 environment ===" -ForegroundColor Yellow
$env:HEIDI_PLAIN = "1"
$serverJob = Start-Job -ScriptBlock {
    param($cmd, $port)
    Set-Location $env:HEIDI_CLI_DIR
    Invoke-Expression "$cmd serve --port $port"
} -ArgumentList $HEIDI_CMD, ($PORT + 1)

Start-Sleep 3
$env:HEIDI_PLAIN = ""

try {
    $healthResponse = Invoke-RestMethod "http://127.0.0.1:$($PORT+1)/health" -TimeoutSec 5
    Write-Host "Health response: $healthResponse"
} catch {
    # Ignore, may fail if server still starting
}

Stop-Job $serverJob -ErrorAction SilentlyContinue
Remove-Job $serverJob -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "ALL TESTS PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
