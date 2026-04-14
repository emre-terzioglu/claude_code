#!/usr/bin/env bash
# Morning Briefing — one-time setup script
# Usage: bash setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  Morning Briefing — Setup"
echo "=========================================="
echo ""

# ── Python version check ────────────────────────────────────
PY=$(python3 --version 2>&1 || true)
if [[ -z "$PY" ]]; then
    echo "ERROR: python3 not found. Install Python 3.11+."
    exit 1
fi
echo "Python: $PY"

# ── Virtual environment ─────────────────────────────────────
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment: venv/"
else
    echo "Virtual environment already exists: venv/"
fi

source venv/bin/activate

# ── Dependencies ─────────────────────────────────────────────
echo "Installing dependencies…"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "Dependencies installed."

# ── .env file ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from template."
    echo ">>> EDIT .env NOW and add your API keys <<<"
else
    echo ".env already exists — skipping."
fi

# ── Log file touch ───────────────────────────────────────────
touch morning_briefing.log

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1.  Edit .env with your real API keys"
echo "  2.  Test manually:"
echo "        source venv/bin/activate"
echo "        python main.py"
echo "  3.  Add the cron job (see README.md)"
echo ""
