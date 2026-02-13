#!/bin/bash
set -e

# Heidi CLI One-Click Installer for Linux/macOS
# Ensures pipx exists and installs Heidi CLI from GitHub

echo "🚀 Heidi CLI Installer"
echo "======================"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Determine Python command
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✅ Found Python: $PYTHON_CMD"

# Install pipx if not available
if ! command -v pipx &> /dev/null; then
    echo "📦 Installing pipx..."
    $PYTHON_CMD -m pip install --user pipx
    $PYTHON_CMD -m pipx ensurepath
    echo "✅ pipx installed"
else
    echo "✅ pipx already installed"
fi

# Install Heidi CLI from GitHub
echo "📦 Installing Heidi CLI..."
pipx install git+https://github.com/heidi-dang/heidi-cli.git

echo ""
echo "🎉 Heidi CLI installed successfully!"
echo ""
echo "Next steps:"
echo "Run: heidi"
echo ""
echo "For help, run: heidi --help"