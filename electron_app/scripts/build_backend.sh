#!/usr/bin/env bash
# scripts/build_backend.sh – builds the main Python FastAPI backend using its PyInstaller spec
# This script is invoked via the npm script "build-backend".

set -e

# Resolve repository root and directory paths
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
ELECTRON_DIR="$REPO_ROOT/electron_app"
PYTHON_DIR="$REPO_ROOT/python_backend"

echo "=== Packaging Python Backend ==="
echo "Repo root: $REPO_ROOT"
echo "Python directory: $PYTHON_DIR"
echo "Electron directory: $ELECTRON_DIR"

cd "$PYTHON_DIR"

# Use the virtual environment inside python_backend if present
if [ -d "venv" ]; then
  echo "Activating virtualenv at python_backend/venv..."
  source "venv/bin/activate"
fi

PYTHON=${PYTHON_BIN:-python3}

# Install backend Python dependencies
echo "Installing Python dependencies..."
$PYTHON -m pip install -r requirements.txt

# Ensure PyInstaller is installed
if ! $PYTHON -m pip show pyinstaller > /dev/null 2>&1; then
  echo "Installing PyInstaller..."
  $PYTHON -m pip install pyinstaller
fi

# Build the backend executable via spec file
echo "Building backend with PyInstaller using backend.spec..."
$PYTHON -m PyInstaller --noconfirm backend.spec

# Ensure destination directory in electron_app resources exists and is clean
OUTPUT_DIR="$ELECTRON_DIR/resources/kruboo_backend"
echo "Cleaning and copying build output to $OUTPUT_DIR..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$ELECTRON_DIR/resources"

# Copy the built directory containing the binary, internal files, and libraries
cp -R dist/kruboo_backend "$OUTPUT_DIR"

# Set executable permission for the binary on macOS/Linux
if [ -f "$OUTPUT_DIR/kruboo_backend" ]; then
  chmod +x "$OUTPUT_DIR/kruboo_backend"
fi

echo "Backend binary and assets successfully placed in $OUTPUT_DIR"
