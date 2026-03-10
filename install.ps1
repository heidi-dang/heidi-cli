#
# Heidi CLI One-Click Installer for Windows
# 
# This script will:
# 1. Clone the latest Heidi CLI from main branch
# 2. Build and install it
# 3. Verify installation
# 4. Clean up temporary files
#
# Usage: .\install.ps1
#

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "$env:USERPROFILE\heidi-cli",
    [switch]$Force
)

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Cyan = "Cyan"
    Magenta = "Magenta"
}

# Print functions
function Write-Header {
    Write-Host "================================" -ForegroundColor $Colors.Magenta
    Write-Host "🚀 Heidi CLI One-Click Installer" -ForegroundColor $Colors.Magenta
    Write-Host "================================" -ForegroundColor $Colors.Magenta
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Colors.Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "🔄 $Message" -ForegroundColor $Colors.Cyan
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check system requirements
function Test-Requirements {
    Write-Step "Checking system requirements..."
    
    # Check Python
    try {
        $python = Get-Command python -ErrorAction Stop
        $pythonVersion = & python --version 2>&1
        Write-Success "Python found: $pythonVersion"
    }
    catch {
        Write-Error "Python is required but not installed"
        Write-Info "Please install Python 3.10 or higher from https://python.org"
        exit 1
    }
    
    # Check pip
    try {
        $pip = Get-Command pip -ErrorAction Stop
        Write-Success "pip found"
    }
    catch {
        Write-Error "pip is required but not installed"
        Write-Info "Please install pip"
        exit 1
    }
    
    # Check git
    try {
        $git = Get-Command git -ErrorAction Stop
        Write-Success "git found"
    }
    catch {
        Write-Error "git is required but not installed"
        Write-Info "Please install git from https://git-scm.com"
        exit 1
    }
    
    Write-Success "All requirements satisfied"
}

# Create temporary directory
function New-TempDirectory {
    $tempDir = Join-Path $env:TEMP "heidi-cli-install-$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Info "Created temporary directory: $tempDir"
    return $tempDir
}

# Clone Heidi CLI
function Invoke-CloneHeidi {
    param([string]$TempDir)
    
    Write-Step "Cloning Heidi CLI from main branch..."
    
    $repoUrl = "https://github.com/heidi-dang/heidi-cli.git"
    $cloneDir = Join-Path $tempDir "heidi-cli"
    
    try {
        & git clone $repoUrl $cloneDir
        Set-Location $cloneDir
        Write-Success "Heidi CLI cloned successfully"
        
        # Show current commit info
        $commitHash = & git rev-parse HEAD
        $commitDate = & git log -1 --format="%cd" --date=short
        Write-Info "Installing commit: $commitHash ($commitDate)"
    }
    catch {
        Write-Error "Failed to clone Heidi CLI repository"
        exit 1
    }
}

# Setup virtual environment
function New-VirtualEnvironment {
    Write-Step "Setting up virtual environment..."
    
    try {
        & python -m venv venv
        & venv\Scripts\Activate.ps1
        Write-Success "Virtual environment created and activated"
        
        # Upgrade pip
        & python -m pip install --upgrade pip
        Write-Success "pip upgraded"
    }
    catch {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Install dependencies
function Install-Dependencies {
    Write-Step "Installing dependencies..."
    
    try {
        & pip install -e .
        Write-Success "Dependencies installed"
    }
    catch {
        Write-Error "Failed to install Heidi CLI dependencies"
        exit 1
    }
}

# Build Heidi CLI
function Build-Heidi {
    Write-Step "Building Heidi CLI..."
    
    try {
        # Check if build tools are available
        if (Get-Command "python -m build" -ErrorAction SilentlyContinue) {
            & python -m build
            Write-Success "Heidi CLI built with modern build system"
        } else {
            # Fallback to setup.py
            & python setup.py build
            Write-Success "Heidi CLI built with setup.py"
        }
    }
    catch {
        Write-Error "Failed to build Heidi CLI"
        exit 1
    }
}

# Install Heidi CLI
function Install-Heidi {
    Write-Step "Installing Heidi CLI..."
    
    try {
        & pip install -e . --user
        Write-Success "Heidi CLI installed successfully"
    }
    catch {
        Write-Error "Failed to install Heidi CLI"
        exit 1
    }
}

# Verify installation
function Test-Installation {
    Write-Step "Verifying installation..."
    
    # Check if heidi command is available
    try {
        $heidi = Get-Command heidi -ErrorAction Stop
        Write-Success "heidi command is available"
        
        # Show version
        try {
            $version = & heidi --version 2>$null
            Write-Success "Heidi CLI version: $version"
        }
        catch {
            Write-Warning "Could not get version - this is normal for first run"
        }
        
        # Test basic functionality
        try {
            & heidi --help >$null 2>&1
            Write-Success "Heidi CLI help command works"
        }
        catch {
            Write-Warning "Heidi CLI help command failed - installation may have issues"
        }
    }
    catch {
        Write-Error "heidi command not found after installation"
        Write-Info "You may need to restart your terminal or add Python Scripts to PATH"
        exit 1
    }
}

# Run post-install setup
function Invoke-PostInstallSetup {
    Write-Step "Running post-install setup..."
    
    # Initialize Heidi CLI
    try {
        & heidi doctor >$null 2>&1
        Write-Success "Heidi CLI initialization successful"
    }
    catch {
        Write-Warning "Heidi CLI initialization had issues - this is normal for first run"
    }
    
    # Show next steps
    Write-Host ""
    Write-Info "🎉 Installation completed successfully!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Run: heidi setup"
    Write-Host "  2. Generate API key: heidi api generate -name 'My Key'"
    Write-Host "  3. Start model server: heidi model serve"
    Write-Host "  4. View help: heidi --help"
    Write-Host ""
    Write-Info "Documentation: https://github.com/heidi-dang/heidi-cli/blob/main/docs/how-to-use.md"
}

# Cleanup temporary files
function Remove-TempFiles {
    param([string]$TempDir)
    
    Write-Step "Cleaning up temporary files..."
    
    try {
        Set-Location $env:USERPROFILE
        Remove-Item -Path $TempDir -Recurse -Force
        Write-Success "Temporary files cleaned up"
    }
    catch {
        Write-Warning "Failed to clean up temporary files: $TempDir"
    }
}

# Error handling
function Handle-Error {
    Write-Error "Installation failed!"
    Write-Info "Check the error messages above for details"
    Write-Info "You can try running the installer again"
    if ($TempDir) {
        Remove-TempFiles -TempDir $TempDir
    }
    exit 1
}

# Main installation function
function Main {
    Write-Header
    
    # Set up error handling
    trap { Handle-Error } ERR
    
    # Check if running as Administrator
    if (-not (Test-Administrator)) {
        Write-Warning "Not running as Administrator - installing for current user only"
    }
    
    # Run installation steps
    Test-Requirements
    $tempDir = New-TempDirectory
    Invoke-CloneHeidi -TempDir $tempDir
    New-VirtualEnvironment
    Install-Dependencies
    Build-Heidi
    Install-Heidi
    Test-Installation
    Invoke-PostInstallSetup
    
    # Cleanup
    Remove-TempFiles -TempDir $tempDir
    
    Write-Success "🎉 Heidi CLI installation completed successfully!"
    Write-Info "You can now use: heidi --version"
}

# Run main function
try {
    Main
}
catch {
    Handle-Error
}
