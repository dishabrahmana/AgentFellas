#!/usr/bin/env bash
set -euo pipefail

# WorkTracker AI Agent — Deploy Script
# Usage: bash scripts/deploy.sh
# Run from the server to pull latest code and restart.

echo "=== WorkTracker Deploy ==="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 1. Pull latest code
echo "[1/4] Pulling latest code..."
git pull origin main

# 2. Activate venv & install deps
echo "[2/4] Installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt -q

# 3. Run DB migration (if any)
echo "[3/4] Database check..."
python -c "from db.connection import init_db; import asyncio; asyncio.run(init_db())" 2>/dev/null || echo "  (async check skipped)"

# 4. Restart service
echo "[4/4] Restarting service..."
if systemctl is-active --quiet worktracker 2>/dev/null; then
    sudo systemctl restart worktracker
    echo "  ✓ worktracker restarted"
    sudo systemctl status worktracker --no-pager | head -5
else
    echo "  ⚠️  systemd service not found. Start manually:"
    echo "  source .venv/bin/activate && python -m bot.main &"
fi

echo ""
echo "=== Deploy Complete ==="
