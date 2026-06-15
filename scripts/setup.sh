#!/usr/bin/env bash
set -euo pipefail

# WorkTracker AI Agent — Setup Script
# Usage: bash scripts/setup.sh
# Run this once on the server after initial git clone.

echo "=== WorkTracker Setup ==="

# 1. Detect OS & install dependencies
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "[1/5] Installing system dependencies..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv sqlite3 git curl
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "[1/5] macOS detected — assuming Python already installed."
else
    echo "[1/5] Unknown OS: $OSTYPE — proceeding..."
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 2. Create Python virtual environment
echo "[2/5] Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. Create data & logs directories
echo "[3/5] Creating data directories..."
mkdir -p data logs config

# 4. Create .env from example if not exists
echo "[4/5] Setting up environment..."
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "  ⚠️  .env file created from .env.example — EDIT IT with your keys!"
else
    echo "  ✓ .env already exists"
fi

# 5. Create systemd service (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "[5/5] Installing systemd service..."
    sudo tee /etc/systemd/system/worktracker.service > /dev/null <<'SERVICE'
[Unit]
Description=WorkTracker AI Agent
After=network.target

[Service]
Type=simple
User=worktracker
WorkingDirectory=/home/worktracker/worktracker
ExecStart=/home/worktracker/worktracker/.venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE
    sudo systemctl daemon-reload
    echo "  ✓ systemd service installed: worktracker"
    echo "  Run: sudo systemctl enable worktracker"
    echo "  Run: sudo systemctl start worktracker"
else
    echo "[5/5] Skipping systemd (not Linux)."
    echo "  Run manually: source .venv/bin/activate && python -m bot.main"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: source .venv/bin/activate && python -m bot.main"
