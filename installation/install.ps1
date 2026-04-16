# Eficiency — Windows installer (PowerShell)
# Creates .venv at the project root if it doesn't exist, then pip-installs
# all required packages.
#
# Run with:
#   Right-click → "Run with PowerShell"
#   — or —
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

# Resolve the project root (one level up from the installation\ folder)
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir     = Join-Path $ProjectRoot ".venv"

Write-Host "Eficiency installer"
Write-Host "Project root : $ProjectRoot"
Write-Host "Virtual env  : $VenvDir"
Write-Host ""

# ── Create venv if absent ─────────────────────────────────────────────────────
if (-Not (Test-Path $VenvDir)) {
    Write-Host "[1/3] Creating virtual environment..."
    python -m venv $VenvDir
    Write-Host "      Done."
} else {
    Write-Host "[1/3] Virtual environment already exists, skipping creation."
}

# ── Activate ──────────────────────────────────────────────────────────────────
Write-Host "[2/3] Activating virtual environment..."
$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
& $Activate

# ── Install packages ──────────────────────────────────────────────────────────
Write-Host "[3/3] Installing packages..."
pip install --upgrade pip
pip install customtkinter pynput Pillow

Write-Host ""
Write-Host "Installation complete."
Write-Host "To run Eficiency:"
Write-Host "  & '$VenvDir\Scripts\Activate.ps1'"
Write-Host "  python '$ProjectRoot\main.py'"

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
