#!/usr/bin/env bash
# start_backend.sh – development helper to launch the FastAPI backend
# Usage: ./start_backend.sh
# It runs uvicorn on the Python FastAPI app located at python_backend/app.py
# The script expects a Python virtual environment with dependencies installed.

set -e
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
# Activate virtualenv if present
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
  source "$SCRIPT_DIR/venv/bin/activate"
fi

# Install dependencies if needed
if ! $PYTHON_BIN -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies..."
  $PYTHON_BIN -m pip install -r "$SCRIPT_DIR/python_backend/requirements.txt"
fi

# Run uvicorn
$PYTHON_BIN -m uvicorn python_backend.app:app --host 127.0.0.1 --port 8000
