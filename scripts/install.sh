#!/bin/bash
set -e

# Heidi CLI One-Click Installer for Linux/macOS
# Uses pipx for global installation so heidi is available from any directory

VERSION=""
REF="main"
VALID_TAG_REGEX='^v?[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9._-]+)?$'

while [[ $# -gt 0 ]]; do
    case $1 in
        --version|-v)
            if [[ -z "$2" || "$2" == -* ]]; then
                echo "Error: --version/-v requires a value"
                echo "Usage: $0 [--version <tag>]"
                echo "Example: $0 --version v0.1.1"
                exit 1
            fi
            VERSION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--version <tag>]"
            echo ""
            echo "Options:"
            echo "  --version, -v <tag>   Install specific version (e.g., v0.1.1). If not provided, installs latest from main."
            echo "  --help, -h           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Heidi CLI Installer (pipx mode)"
echo "================================"

if [ -n "$VERSION" ]; then
    if ! [[ "$VERSION" =~ $VALID_TAG_REGEX ]]; then
        echo "Error: Invalid version format. Expected format: v0.1.1 or 0.1.1"
        exit 1
    fi
    REF="$VERSION"
    echo "Installing heidi-cli@$REF"
else
    echo "Installing heidi-cli from main (latest)"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python 3.10+ first."
    exit 1
fi

# Determine Python command
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "Found Python: $PYTHON_CMD"

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Python $PYTHON_VERSION is too old. Please install Python 3.10 or later."
    exit 1
fi

echo "Python version: $PYTHON_VERSION"

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo ""
    echo "Installing pipx..."
    "$PYTHON_CMD" -m pip install --user pipx
    pipx ensurepath
    export PATH="$HOME/.local/bin:$PATH"
fi

# Build the package URL
PKG_URL="git+https://github.com/heidi-dang/heidi-cli.git"
if [ "$REF" != "main" ]; then
    PKG_URL="${PKG_URL}@${REF}"
fi

echo ""
echo "Installing Heidi CLI globally via pipx..."
echo "Resolved ref: $REF"
pipx install --force "${PKG_URL}"

echo ""
echo "Building UI into cache..."
heidi ui build

echo ""
echo "================================"
echo "Heidi CLI installed successfully!"
echo ""
echo "Usage from any directory:"
echo "  heidi --help"
echo "  heidi serve --ui"
echo ""
