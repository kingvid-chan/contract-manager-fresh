#!/bin/bash
# Contract Manager — local development launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Shared conda environment
CONDA_ENV="$HOME/外部需求/.conda/codingagent"
if [ ! -f "$CONDA_ENV/bin/python" ]; then
    echo "Error: conda env not found at $CONDA_ENV"
    echo "Create it: conda create -p $CONDA_ENV python=3.11 -y"
    exit 1
fi

PYTHON="$CONDA_ENV/bin/python"

# Install deps if needed
if [ ! -f "$CONDA_ENV/bin/uvicorn" ]; then
    echo "[run] Installing dependencies..."
    "$PYTHON" -m pip install -r requirements.txt -q
fi

# Seed data
echo "[run] Seeding database..."
"$PYTHON" seeds/seed.py

# Start server
echo "[run] Starting server..."
exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
