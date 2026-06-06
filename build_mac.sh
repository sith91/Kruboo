#!/bin/bash
# =============================================================================
# Kruboo AI Assistant — macOS Build Script
# Creates a distributable .dmg installer
# =============================================================================
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ELECTRON_DIR="$APP_DIR/electron_app"
BACKEND_DIR="$APP_DIR/python_backend"
DIST_DIR="$ELECTRON_DIR/dist"

echo "🚀 Building Kruboo AI Assistant for macOS..."
echo ""

# ── Step 1: Build Python backend with PyInstaller ──────────────────────────
echo "📦 Step 1/3: Bundling Python backend..."
cd "$BACKEND_DIR"
source venv/bin/activate

export LLAMA_NO_METAL=1
export GGML_NO_METAL=1

# Clean previous build
rm -rf dist/kruboo_backend build/

pyinstaller backend.spec \
  --noconfirm \
  --clean \
  --distpath "$BACKEND_DIR/dist"

echo "✅ Python backend bundled → $BACKEND_DIR/dist/kruboo_backend/"

# ── Step 2: Copy bundled backend into Electron extraResources ──────────────
echo ""
echo "📂 Step 2/3: Copying backend into Electron resources..."
RESOURCES_TARGET="$ELECTRON_DIR/resources/kruboo_backend"
rm -rf "$RESOURCES_TARGET"
mkdir -p "$ELECTRON_DIR/resources"
cp -r "$BACKEND_DIR/dist/kruboo_backend" "$RESOURCES_TARGET"
echo "✅ Backend copied → $RESOURCES_TARGET"

# ── Step 3: Package Electron app with electron-builder ────────────────────
echo ""
echo "🔨 Step 3/3: Building macOS .app and .dmg..."
cd "$ELECTRON_DIR"
PATH=/Users/sithija/.nvm/versions/node/v25.8.2/bin:$PATH npm run dist -- --mac dmg

echo ""
echo "🎉 Done! Installer ready at:"
ls -lh "$DIST_DIR"/*.dmg 2>/dev/null || ls -lh "$DIST_DIR"
