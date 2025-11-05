AI Assistant - Developer Documentation: Installer Generation
📋 Overview

This documentation explains how to generate professional Windows and macOS installers for the AI Assistant application. The build system supports multiple distribution formats and automated workflows.
🏗️ Project Structure
text

ai-assistant-platform/
├── 📂 build-scripts/
│   ├── build-windows.js      # Windows installer generator
│   ├── build-macos.js        # macOS installer generator
│   └── build-all.js          # Multi-platform builder
├── 📂 installers/
│   ├── windows-installer.nsi # NSIS script for Windows
│   ├── macos-scripts/        # macOS pre/post install scripts
│   └── macos-resources/      # macOS installer assets
├── 📂 .github/workflows/
│   └── release.yml           # Automated build pipeline
└── 📜 package.json           # Build scripts configuration

🪟 Windows Installer Generation
Prerequisites

    Node.js 18+ and npm

    NSIS (Nullsoft Scriptable Install System)
    bash

# Install via Chocolatey
choco install nsis

# Or download from: https://nsis.sourceforge.io/Download

Quick Start
bash

# Build Windows installer (from project root)
npm run build:windows

# Or run directly
node build-scripts/build-windows.js

Manual Steps

    Build the application first:
    bash

npm run build:dev

Generate Windows installer:
bash

cd build-scripts
node build-windows.js

Output Files

After successful build, check dist/windows/ directory:

    AI_Assistant_Setup.exe - Standard installer

    AI_Assistant_Portable.zip - Portable version

    portable/ - Portable app directory

Windows Installer Features

    ✅ Professional NSIS-based installer

    ✅ Start Menu shortcuts

    ✅ Desktop shortcut

    ✅ Auto-start configuration

    ✅ Proper uninstaller (Add/Remove Programs)

    ✅ Admin privileges for system-wide installation

    ✅ Upgrade handling - detects previous installations

Customization

Edit installers/windows-installer.nsi to modify:

    Installer branding

    Component selection

    File associations

    Custom installation logic

🍎 macOS Installer Generation
Prerequisites

    macOS 10.14+ (for building)

    Xcode Command Line Tools
    bash

xcode-select --install

    Node.js 18+ and npm

Quick Start
bash

# Build macOS installer (from project root)
npm run build:macos

# Or run directly
node build-scripts/build-macos.js

Manual Steps

    Build the application:
    bash

npm run build:dev

Generate macOS installers:
bash

cd build-scripts
node build-macos.js

Output Files

After successful build, check dist/macos/ directory:

    AI Assistant.dmg - Standard DMG installer

    AI Assistant.zip - Compressed distribution

    AI Assistant.pkg - Package installer (if pkgbuild available)

    assets/ - Additional tools and documentation

macOS Installer Features

    ✅ Universal Binary (Intel + Apple Silicon)

    ✅ DMG installer with drag-to-install

    ✅ ZIP distribution for manual installation

    ✅ PKG installer for advanced deployment

    ✅ Launch Agent for auto-start

    ✅ Complete uninstall script

    ✅ Gatekeeper compatible (with notarization)

Customization

Edit these files for macOS customization:

    build-scripts/macos-installer.js - Build logic

    installers/macos-resources/ - Installer assets

    installers/macos-scripts/ - Pre/post install scripts

🔧 Build Script Reference
Package.json Scripts
json

{
  "scripts": {
    "build:windows": "node build-scripts/build-windows.js",
    "build:macos": "node build-scripts/build-macos.js",
    "build:all": "node build-scripts/build-all.js",
    "build:dev": "node build-scripts/build-all.js dev",
    "installer:windows": "npm run build:windows",
    "installer:macos": "npm run build:macos"
  }
}

Environment Variables

For Windows:
bash

# Optional: Code signing certificate
set SIGNTOOL_PATH="C:\Program Files (x86)\Windows Kits\10\bin\10.0.17763.0\x64\signtool.exe"
set SIGN_CERTIFICATE="path\to\certificate.pfx"
set SIGN_PASSWORD="your_password"

For macOS:
bash

# Required for notarization
export APPLE_ID="your@email.com"
export APPLE_ID_PASSWORD="app-specific-password"
export APPLE_TEAM_ID="AB123CD456"

🤖 Automated Builds with GitHub Actions
Setup Automated Pipelines

    Create GitHub Secrets:

        APPLE_ID - Apple Developer account email

        APPLE_ID_PASSWORD - App-specific password

        APPLE_TEAM_ID - Developer team ID

    Trigger builds on tag creation:
    bash

git tag v1.0.0
git push --tags

GitHub Actions Workflow

The .github/workflows/release.yml automatically:

    ✅ Builds for Windows, macOS, and Linux

    ✅ Creates installers for all platforms

    ✅ Uploads artifacts to GitHub Releases

    ✅ Handles notarization (macOS)

📦 Distribution Formats
Windows Distribution Options
Format	Purpose	Usage
.exe	Standard installer	User-friendly installation
Portable ZIP	No installation	USB drives, temporary use
Portable Folder	Direct execution	Quick testing, demos
macOS Distribution Options
Format	Purpose	Usage
.dmg	Standard installer	Most user-friendly
.zip	Compressed app	Manual installation
.pkg	Package installer	Enterprise deployment
.app	Direct bundle	Development, testing
🔐 Code Signing & Notarization
Windows Code Signing

    Obtain a code signing certificate

    Configure in windows-installer.nsi:
    nsis

!finalize 'signtool sign /f "certificate.pfx" /p password /t http://timestamp.digicert.com "%1"'

macOS Notarization

    Create app-specific password at appleid.apple.com

    Configure environment variables

    Run notarization:
    bash

cd dist/macos
./notarize.sh

🐛 Troubleshooting
Common Windows Issues

NSIS not found:
bash

# Install NSIS or use fallback
choco install nsis

Permission errors:

    Run command prompt as Administrator

    Ensure antivirus isn't blocking the build

Common macOS Issues

Xcode tools missing:
bash

xcode-select --install
sudo xcode-select --switch /Library/Developer/CommandLineTools

Notarization failures:

    Verify app-specific password

    Check team ID in developer account

    Ensure app bundle is properly structured

Gatekeeper warnings:

    Notarize the application

    Use signed developer certificate

Build Failures

    Clean build:
    bash

rm -rf dist node_modules
npm install
npm run build

Check dependencies:
bash

npm list --depth=0

    Verify platform requirements:

        Windows: NSIS, Node.js 18+

        macOS: Xcode tools, Node.js 18+

📝 Best Practices
Version Management

    Update version in multiple places:

        package.json

        windows-installer.nsi

        macOS plist files

        GitHub Actions workflow

    Use semantic versioning:
    bash

git tag v1.2.3
git push --tags

Testing Checklist

Before Distribution:

    Test installer on clean VM/computer

    Verify all shortcuts work

    Check uninstaller completeness

    Test auto-start functionality

    Validate file associations (if any)

    Verify digital signatures

Platform-Specific Tests:

    Windows: Test on Windows 10/11

    macOS: Test on Intel and Apple Silicon

    Both: Verify microphone permissions

Security Considerations

    Code signing for trust and security

    Notarization for macOS Gatekeeper

    Regular dependency updates

    Security scanning of build artifacts

🚀 Release Process
Standard Release Flow

    Preparation:
    bash

npm version patch  # or minor/major
git push --tags

    Automated Build:

        GitHub Actions triggers on tag push

        Builds all platform installers

        Creates GitHub release

    Manual Verification:

        Download and test installers

        Verify digital signatures

        Update release notes

    Distribution:

        Upload to website/download page

        Update documentation

        Announce release

Emergency Hotfix

    Create hotfix branch:
    bash

git checkout -b hotfix/1.2.4

Build locally:
bash

npm run build:all

Manual distribution while CI is fixed
