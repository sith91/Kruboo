#!/bin/bash

echo "🚀 AI Assistant Deployment Script"
echo "================================="

# Build the application
echo "📦 Building application..."
npm run build

# Create distribution packages
echo "🎁 Creating distribution packages..."
cd client/desktop

# Windows
echo "🪟 Building Windows package..."
npx electron-builder --win --x64

# macOS
echo "🍎 Building macOS package..."
npx electron-builder --mac --x64 --arm64

# Linux
echo "🐧 Building Linux package..."
npx electron-builder --linux --x64

echo "✅ Build complete!"
echo "📁 Packages available in: client/desktop/dist/"
echo ""
echo "To distribute:"
echo "• Windows: AI Assistant Setup 1.0.0.exe"
echo "• macOS: AI Assistant-1.0.0.dmg" 
echo "• Linux: ai-assistant_1.0.0_amd64.deb"
