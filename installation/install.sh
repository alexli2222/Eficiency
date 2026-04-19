#!/usr/bin/env bash
# Eficiency — macOS/Linux installer
# Creates .venv at the project root if it doesn't exist, then pip-installs
# all required packages.

set -euo pipefail

# Resolve the project root (one level up from the installation/ folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "Eficiency installer"
echo "Project root : $PROJECT_ROOT"
echo "Virtual env  : $VENV_DIR"
echo ""

# ── Create venv if absent ─────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "      Done."
else
    echo "[1/3] Virtual environment already exists, skipping creation."
fi

# ── Activate ──────────────────────────────────────────────────────────────────
echo "[2/3] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# ── Install packages ──────────────────────────────────────────────────────────
echo "[3/3] Installing packages..."
pip install --upgrade pip
pip install customtkinter pynput Pillow tkinterdnd2 pypdf

# Platform-specific extras
if [[ "$(uname)" == "Darwin" ]]; then
    echo "      macOS detected — installing pyobjc-framework-Quartz (macro recording)..."
    pip install pyobjc-framework-Quartz
elif [[ "$(uname)" == "Linux" ]]; then
    echo "      Linux detected — installing pygame (audio backend)..."
    pip install pygame
fi

echo ""
echo "Installation complete."
echo "To run Eficiency:"
echo "  source '$VENV_DIR/bin/activate'"
echo "  python '$PROJECT_ROOT/main.py'"
