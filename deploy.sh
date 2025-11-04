#!/bin/bash

echo "🚀 AI Assistant Quick Deploy"
echo "============================"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build core engine
echo "🔨 Building core engine..."
cd core-engine && npm run build && cd ..

# Build and package
echo "📦 Building desktop application..."
cd client/desktop

# Install desktop dependencies
npm install

# Build for current platform
echo "🎁 Packaging for $(uname -s)..."
case "$(uname -s)" in
    Linux*)     npx electron-builder --linux ;;
    Darwin*)    npx electron-builder --mac ;;
    CYGWIN*)    npx electron-builder --win ;;
    MINGW*)     npx electron-builder --win ;;
    *)          echo "Unknown OS"; exit 1 ;;
esac

echo ""
echo "✅ Build complete!"
echo "📁 Your installer is in: client/desktop/dist/"
echo ""
echo "To distribute to all platforms, run:"
echo "  node build.js all"
