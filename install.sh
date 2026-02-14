#!/bin/bash
set -e

# Heidi CLI One-Click Installer for Linux/macOS
# Clones repo and installs in editable mode with venv

# Save terminal state for cleanup
ORIG_STTY=""
if [ -t 0 ]; then
    ORIG_STTY="$(stty -g 2>/dev/null || true)"
fi

# Prevent Ctrl+S freeze during install
stty -ixon 2>/dev/null || true

# Cleanup function to restore terminal state
cleanup() {
    if [ -n "$ORIG_STTY" ]; then
        stty "$ORIG_STTY" 2>/dev/null || true
    else
        stty sane 2>/dev/null || true
        stty echo 2>/dev/null || true
    fi
    tput cnorm 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Heidi CLI Installer"
echo "===================="

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

# Initial setup: Check for existing installation
INSTALL_DIR="$HOME/heidi-cli"
EXISTING_INSTALL=false
EXISTING_VENV=false

# Check for existing installation directory
if [ -d "$INSTALL_DIR" ]; then
    EXISTING_INSTALL=true
fi

# Check for existing venv in common locations
for dir in "$INSTALL_DIR/heidi_cli" "$HOME/.local/heidi-cli" "."; do
    if [ -d "$dir/.venv" ] || [ -d "$dir/venv" ]; then
        EXISTING_VENV=true
        break
    fi
done

# Check if heidi command is available (in PATH)
if command -v heidi &> /dev/null; then
    echo ""
    echo "⚠️  Heidi CLI is already installed!"
    EXISTING_INSTALL=true
fi

# Prompt for action if existing installation found
if [ "$EXISTING_INSTALL" = true ] || [ "$EXISTING_VENV" = true ]; then
    echo ""
    echo "Found existing Heidi CLI installation."
    echo ""
    echo "Options:"
    echo "  [1] Uninstall and reinstall (fresh install)"
    echo "  [2] Update existing installation"
    echo "  [3] Cancel"
    echo ""
    read -r -p "Choose option [1]: " -r choice < /dev/tty
    choice=${choice:-1}

    case $choice in
        1)
            echo ""
            echo "Uninstalling existing installation..."
            
            # Remove existing installation directory
            if [ -d "$INSTALL_DIR" ]; then
                rm -rf "$INSTALL_DIR"
            fi
            
            # Remove venv in current directory if exists
            if [ -d ".venv" ]; then
                rm -rf .venv
            fi
            if [ -d "venv" ]; then
                rm -rf venv
            fi
            
            # Try to find and remove venv in common locations
            for dir in "$HOME/.local/heidi-cli"; do
                if [ -d "$dir/.venv" ] || [ -d "$dir/venv" ]; then
                    rm -rf "$dir"
                fi
            done
            
            echo "✅ Existing installation removed."
            ;;
        2)
            echo ""
            echo "Updating existing installation..."
            
            if [ -d "$INSTALL_DIR" ]; then
                cd "$INSTALL_DIR"
                git pull origin main
                if [ -d "heidi_cli/.venv" ]; then
                    cd heidi_cli
                    source .venv/bin/activate
                    pip install -e ".[dev]" -q
                fi
                echo ""
                echo "✅ Heidi CLI updated successfully!"
                echo ""
                echo "To activate, run:"
                echo "  cd $INSTALL_DIR/heidi_cli && source .venv/bin/activate"
                exit 0
            fi
            ;;
        3)
            echo "Cancelled."
            exit 0
            ;;
        *)
            echo "Invalid option. Cancelling."
            exit 1
            ;;
    esac
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone repo
echo ""
echo "Cloning heidi-cli..."
git clone https://github.com/heidi-dang/heidi-cli.git
cd heidi-cli/heidi_cli

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv .venv
source .venv/bin/activate

# Upgrade pip
echo "Installing dependencies..."
pip install --upgrade pip -q

# Install in editable mode
pip install -e ".[dev]" -q

echo ""
echo "Heidi CLI installed successfully!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run:"
echo "  heidi init"
echo "  heidi --help"
