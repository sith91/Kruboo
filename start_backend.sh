#!/bin/bash
# =============================================================================
# AI Assistant Backend — Auto-restart launcher
# Uses llama-cpp-python (CPU-only, no Metal) to avoid SIGABRT on Apple Silicon
# =============================================================================

cd "$(dirname "$0")/python_backend"
source venv/bin/activate

# Completely disable Metal/GPU at the OS environment level
# (must be set BEFORE Python starts — in-Python os.environ calls are too late)
export LLAMA_NO_METAL=1
export GGML_NO_METAL=1
export GGML_METAL_PATH_RESOURCES=""
export GPT4ALL_BACKEND=cpu

echo "=== AI Assistant Backend ==="
echo "Model: Phi-3-mini (CPU-only via llama-cpp-python)"
echo "Metal GPU: DISABLED"
echo ""

RESTART_COUNT=0

while true; do
    echo "[$(date '+%H:%M:%S')] Starting server (attempt #$((RESTART_COUNT + 1)))..."
    python main.py
    EXIT_CODE=$?
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "[$(date '+%H:%M:%S')] Server exited (code=$EXIT_CODE). Restarting in 3s..."
    sleep 3
done
