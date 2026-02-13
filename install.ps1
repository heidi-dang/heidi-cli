# Heidi CLI One-Click Installer for Windows PowerShell
# Verifies py exists, installs pipx, and installs Heidi CLI from GitHub

$ErrorActionPreference = "Stop"

Write-Host "🚀 Heidi CLI Installer" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

# Verify py exists
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python launcher 'py' not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found Python launcher: py" -ForegroundColor Green

# Install/ensure pipx
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing pipx..." -ForegroundColor Yellow
    py -m pip install --user pipx
    py -m pipx ensurepath
    Write-Host "✅ pipx installed" -ForegroundColor Green
} else {
    Write-Host "✅ pipx already installed" -ForegroundColor Green
}

# Install Heidi CLI from GitHub
Write-Host "📦 Installing Heidi CLI..." -ForegroundColor Yellow
pipx install git+https://github.com/heidi-dang/heidi-cli.git

Write-Host ""
Write-Host "🎉 Heidi CLI installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "Open a new PowerShell window" -ForegroundColor White
Write-Host "Run: heidi" -ForegroundColor White
Write-Host ""
Write-Host "For help, run: heidi --help" -ForegroundColor White