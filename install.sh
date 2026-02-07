#!/bin/bash
# Inkling AI Companion - Install Script
# Usage: bash install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"
SERVICE_USER="${USER:-pi}"

echo "======================================="
echo "  Inkling AI Companion - Installer"
echo "======================================="
echo ""
echo "Install directory: $INSTALL_DIR"
echo "User: $SERVICE_USER"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is required but not found."
    echo "Install with: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/.venv"
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "Dependencies installed."

# Create data directory
mkdir -p "$HOME/.inkling"
echo "Data directory: $HOME/.inkling"

# Set up .env file
if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ -f "$INSTALL_DIR/.env.example" ]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        echo ""
        echo "Created .env file from .env.example"
        echo "IMPORTANT: Edit .env to add your API keys:"
        echo "  nano $INSTALL_DIR/.env"
    fi
else
    echo ".env file already exists."
fi

# Create local config if not exists
if [ ! -f "$INSTALL_DIR/config.local.yml" ]; then
    if [ -f "$INSTALL_DIR/config.local.yml.example" ]; then
        cp "$INSTALL_DIR/config.local.yml.example" "$INSTALL_DIR/config.local.yml"
        echo "Created config.local.yml from example."
    fi
fi

# Offer to install systemd service
echo ""
echo "======================================="
echo "  Autostart Setup (optional)"
echo "======================================="
echo ""
echo "Install as a systemd service for auto-start on boot?"
echo "  1) Web mode (recommended - browser access)"
echo "  2) SSH mode (terminal access)"
echo "  3) Skip"
echo ""
read -p "Choice [1/2/3]: " -r CHOICE

if [ "$CHOICE" = "1" ] || [ "$CHOICE" = "2" ]; then
    if [ "$CHOICE" = "1" ]; then
        SERVICE_FILE="inkling-web.service"
        SERVICE_NAME="inkling-web"
    else
        SERVICE_FILE="inkling-ssh.service"
        SERVICE_NAME="inkling-ssh"
    fi

    # Update service file with actual paths
    TEMP_SERVICE="/tmp/$SERVICE_FILE"
    sed -e "s|User=pi|User=$SERVICE_USER|" \
        -e "s|/home/pi/inkling|$INSTALL_DIR|g" \
        "$INSTALL_DIR/deployment/$SERVICE_FILE" > "$TEMP_SERVICE"

    echo ""
    echo "Installing $SERVICE_NAME service..."

    if sudo cp "$TEMP_SERVICE" "/etc/systemd/system/$SERVICE_FILE"; then
        sudo systemctl daemon-reload
        sudo systemctl enable "$SERVICE_FILE"
        echo "Service installed and enabled."
        echo ""
        echo "Start now with: sudo systemctl start $SERVICE_FILE"
        echo "View logs with: sudo journalctl -u $SERVICE_FILE -f"
    else
        echo "Failed to install service (need sudo access)."
        echo "Manual install: sudo cp deployment/$SERVICE_FILE /etc/systemd/system/"
    fi

    rm -f "$TEMP_SERVICE"
fi

echo ""
echo "======================================="
echo "  Installation Complete!"
echo "======================================="
echo ""
echo "Quick start:"
echo "  source $INSTALL_DIR/.venv/bin/activate"
echo "  python main.py --mode web   # Web UI at http://localhost:8081"
echo "  python main.py --mode ssh   # Terminal chat"
echo ""
echo "Don't forget to add your API keys to .env!"
echo ""
