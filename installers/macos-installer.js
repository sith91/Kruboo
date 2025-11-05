const { execSync } = require('child_process');
const fs = require('fs-extra');
const path = require('path');
const plist = require('plist');

class MacOSInstaller {
  constructor() {
    this.rootDir = path.join(__dirname, '..');
    this.distDir = path.join(this.rootDir, 'dist', 'macos');
    this.desktopDir = path.join(this.rootDir, 'client', 'desktop');
    this.buildDir = path.join(this.desktopDir, 'build');
    this.appName = 'AI Assistant';
    this.bundleId = 'com.aiassistant.desktop';
  }

  async createInstaller() {
    console.log('🍎 Creating macOS Installer...\n');
    
    try {
      // Ensure directories exist
      this.setupDirectories();
      
      // Create DMG installer
      await this.createDMG();
      
      // Create ZIP distribution
      await this.createZipDistribution();
      
      // Create PKG installer (optional)
      await this.createPKGInstaller();
      
      // Create additional macOS assets
      await this.createMacOSAssets();
      
      console.log('\n✅ macOS installer created successfully!');
      this.showInstallerSummary();
      
    } catch (error) {
      console.error('❌ macOS installer creation failed:', error);
      process.exit(1);
    }
  }

  setupDirectories() {
    console.log('📁 Setting up directories...');
    fs.ensureDirSync(this.distDir);
    
    // Create temporary DMG content directory
    this.dmgContentDir = path.join(this.distDir, 'dmg-content');
    if (fs.existsSync(this.dmgContentDir)) {
      fs.removeSync(this.dmgContentDir);
    }
    fs.ensureDirSync(this.dmgContentDir);
  }

  async createDMG() {
    console.log('\n📀 Creating DMG installer...');
    
    const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
    
    if (!fs.existsSync(appBundlePath)) {
      throw new Error('App bundle not found. Build the app first.');
    }

    // Copy app to DMG content directory
    const targetAppPath = path.join(this.dmgContentDir, `${this.appName}.app`);
    fs.copySync(appBundlePath, targetAppPath);
    
    // Create Applications folder alias
    execSync(`ln -s /Applications "${this.dmgContentDir}/Applications"`);
    
    // Create background folder and copy background image
    const backgroundDir = path.join(this.dmgContentDir, '.background');
    fs.ensureDirSync(backgroundDir);
    
    // Copy or create background image
    const backgroundSource = path.join(this.buildDir, 'dmg-background.png');
    if (fs.existsSync(backgroundSource)) {
      fs.copySync(backgroundSource, path.join(backgroundDir, 'background.png'));
    }
    
    // Create DS_Store for DMG customization
    await this.createDSStore();
    
    // Create DMG using hdiutil
    const dmgPath = path.join(this.distDir, `${this.appName}.dmg`);
    
    const createDMGCommand = `
      hdiutil create \
        -volname "${this.appName}" \
        -srcfolder "${this.dmgContentDir}" \
        -ov \
        -format UDZO \
        -fs HFS+J \
        -imagekey zlib-level=9 \
        "${dmgPath}"
    `;
    
    execSync(createDMGCommand, { stdio: 'inherit' });
    
    // Clean up temporary directory
    fs.removeSync(this.dmgContentDir);
    
    console.log(`✅ DMG installer created: ${this.appName}.dmg`);
  }

  async createDSStore() {
    // Create a basic DS_Store file for DMG layout
    const dsStorePath = path.join(this.dmgContentDir, '.DS_Store');
    
    // This is a simplified version. In production, you might want to use a proper DS_Store generator
    const dsStoreContent = Buffer.from([
      0x00, 0x00, 0x00, 0x01, 0x42, 0x75, 0x64, 0x31,
      0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00
    ]);
    
    fs.writeFileSync(dsStorePath, dsStoreContent);
    
    // Set DMG window layout (app on left, Applications on right)
    try {
      execSync(`
        osascript -e '
          tell application "Finder"
            open POSIX file "${this.dmgContentDir}"
            set dmgWindow to window 1
            set toolbar visible of dmgWindow to false
            set statusbar visible of dmgWindow to false
            set current view of dmgWindow to icon view
            set bounds of dmgWindow to {400, 100, 900, 400}
          end tell
        '
      `, { stdio: 'pipe' });
    } catch (error) {
      console.log('⚠️  Could not customize DMG window layout automatically');
    }
  }

  async createZipDistribution() {
    console.log('\n🗜️ Creating ZIP distribution...');
    
    const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
    
    if (fs.existsSync(appBundlePath)) {
      const zipPath = path.join(this.distDir, `${this.appName}.zip`);
      
      execSync(`ditto -c -k --sequesterRsrc --keepParent "${appBundlePath}" "${zipPath}"`, {
        stdio: 'inherit'
      });
      
      console.log(`✅ ZIP distribution created: ${this.appName}.zip`);
    }
  }

  async createPKGInstaller() {
    console.log('\n📦 Creating PKG installer...');
    
    try {
      // Check if pkgbuild is available
      execSync('pkgbuild --version', { stdio: 'pipe' });
      
      const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
      const componentPkgPath = path.join(this.distDir, 'component.pkg');
      const distributionPath = path.join(this.distDir, 'Distribution.xml');
      const pkgPath = path.join(this.distDir, `${this.appName}.pkg`);
      
      // Create component package
      const pkgbuildCommand = `
        pkgbuild \
          --component "${appBundlePath}" \
          --install-location "/Applications" \
          --scripts "${path.join(this.rootDir, 'installers', 'macos-scripts')}" \
          "${componentPkgPath}"
      `;
      
      execSync(pkgbuildCommand, { stdio: 'inherit' });
      
      // Create distribution file
      const distributionXml = this.createDistributionXML();
      fs.writeFileSync(distributionPath, distributionXml);
      
      // Build product archive
      const productbuildCommand = `
        productbuild \
          --distribution "${distributionPath}" \
          --package-path "${this.distDir}" \
          --resources "${path.join(this.rootDir, 'installers', 'macos-resources')}" \
          "${pkgPath}"
      `;
      
      execSync(productbuildCommand, { stdio: 'inherit' });
      
      // Clean up intermediate files
      fs.removeSync(componentPkgPath);
      fs.removeSync(distributionPath);
      
      console.log(`✅ PKG installer created: ${this.appName}.pkg`);
      
    } catch (error) {
      console.log('⚠️  PKG installer creation skipped (pkgbuild not available or failed)');
    }
  }

  createDistributionXML() {
    return `<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>AI Assistant</title>
    <background file="background.png" alignment="bottomleft" scaling="none"/>
    <welcome file="welcome.html"/>
    <license file="license.rtf"/>
    <conclusion file="conclusion.html"/>
    <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="default">
            <line choice="${this.bundleId}"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="${this.bundleId}" visible="false">
        <pkg-ref id="${this.bundleId}"/>
    </choice>
    <pkg-ref id="${this.bundleId}" version="1.0.0" onConclusion="none">component.pkg</pkg-ref>
</installer-gui-script>`;
  }

  async createMacOSAssets() {
    console.log('\n🎨 Creating macOS assets...');
    
    const assetsDir = path.join(this.distDir, 'assets');
    fs.ensureDirSync(assetsDir);
    
    // Create uninstall script
    await this.createUninstallScript(assetsDir);
    
    // Create Launch Agent plist
    await this.createLaunchAgent(assetsDir);
    
    // Create installation instructions
    await this.createInstallationInstructions(assetsDir);
    
    console.log('✅ macOS assets created');
  }

  async createUninstallScript(assetsDir) {
    const uninstallScript = `#!/bin/bash

# AI Assistant Uninstaller for macOS
# Removes AI Assistant and all associated files

echo "🗑️  Uninstalling AI Assistant..."

APP_NAME="AI Assistant"
APP_DIR="/Applications/\$APP_NAME.app"
SUPPORT_DIR="\$HOME/Library/Application Support/ai-assistant"
LAUNCH_AGENT="\$HOME/Library/LaunchAgents/com.aiassistant.desktop.plist"

# Stop the app if running
echo "⏹️  Stopping AI Assistant..."
pkill -f "AI Assistant"
sleep 2

# Remove Launch Agent
echo "🚀 Removing Launch Agent..."
if [ -f "\$LAUNCH_AGENT" ]; then
    launchctl unload "\$LAUNCH_AGENT" 2>/dev/null
    rm -f "\$LAUNCH_AGENT"
fi

# Remove application
echo "📱 Removing application..."
if [ -d "\$APP_DIR" ]; then
    rm -rf "\$APP_DIR"
fi

# Remove support files
echo "🧹 Cleaning up support files..."
if [ -d "\$SUPPORT_DIR" ]; then
    rm -rf "\$SUPPORT_DIR"
fi

# Remove caches
echo "🗂️  Removing caches..."
rm -rf "\$HOME/Library/Caches/com.aiassistant.desktop"
rm -rf "\$HOME/Library/Logs/AI Assistant"
rm -rf "\$HOME/Library/Saved Application State/com.aiassistant.desktop.savedState"

# Remove preferences
echo "⚙️  Removing preferences..."
defaults delete com.aiassistant.desktop 2>/dev/null

echo ""
echo "✅ AI Assistant has been completely uninstalled."
echo ""
echo "If you installed from the ZIP file, you may also want to:"
echo "1. Empty Trash to completely remove the application"
echo "2. Restart your computer to ensure all processes are stopped"
`;

    const scriptPath = path.join(assetsDir, 'uninstall.sh');
    fs.writeFileSync(scriptPath, uninstallScript);
    execSync(`chmod +x "${scriptPath}"`);
  }

  async createLaunchAgent(assetsDir) {
    const launchAgentPlist = {
      Label: this.bundleId,
      ProgramArguments: [
        '/Applications/AI Assistant.app/Contents/MacOS/AI Assistant',
        '--minimized'
      ],
      RunAtLoad: true,
      KeepAlive: false,
      StandardOutPath: '/tmp/ai-assistant.log',
      StandardErrorPath: '/tmp/ai-assistant-error.log',
      ProcessType: 'Interactive'
    };

    const plistPath = path.join(assetsDir, 'com.aiassistant.desktop.plist');
    fs.writeFileSync(plistPath, plist.build(launchAgentPlist));

    // Create installation script for Launch Agent
    const installScript = `#!/bin/bash

# AI Assistant Launch Agent Installer
# Configures AI Assistant to start automatically on login

echo "🚀 Installing AI Assistant Launch Agent..."

LAUNCH_AGENT="\$HOME/Library/LaunchAgents/com.aiassistant.desktop.plist"
APP_PATH="/Applications/AI Assistant.app"

# Check if app is installed
if [ ! -d "\$APP_PATH" ]; then
    echo "❌ AI Assistant is not installed in Applications folder."
    echo "   Please install AI Assistant first."
    exit 1
fi

# Copy plist to LaunchAgents directory
cp "com.aiassistant.desktop.plist" "\$LAUNCH_AGENT"

# Load the launch agent
launchctl load "\$LAUNCH_AGENT"

echo "✅ Launch Agent installed successfully!"
echo ""
echo "The app will now start automatically when you log in."
echo ""
echo "To uninstall the Launch Agent:"
echo "  launchctl unload '\$LAUNCH_AGENT'"
echo "  rm '\$LAUNCH_AGENT'"
`;

    const scriptPath = path.join(assetsDir, 'install-launch-agent.sh');
    fs.writeFileSync(scriptPath, installScript);
    execSync(`chmod +x "${scriptPath}"`);
  }

  async createInstallationInstructions(assetsDir) {
    const instructions = `# AI Assistant - macOS Installation Guide

## Installation Methods

### Method 1: DMG Installer (Recommended)
1. Double-click \`AI Assistant.dmg\` to open it
2. Drag \`AI Assistant.app\` to the \`Applications\` folder
3. Eject the DMG when finished
4. Launch AI Assistant from Applications or Spotlight

### Method 2: ZIP Distribution
1. Double-click \`AI Assistant.zip\` to extract
2. Move \`AI Assistant.app\` to \`Applications\` folder
3. Launch AI Assistant from Applications

### Method 3: PKG Installer
1. Double-click \`AI Assistant.pkg\`
2. Follow the installation wizard
3. Launch AI Assistant from Applications

## First Run
- The app will appear in your menu bar (top-right)
- Click the menu bar icon to open the main window
- Use \`Command+Shift+A\` as a keyboard shortcut
- Configure AI API keys in Settings for full functionality

## Auto-Start (Optional)
To start AI Assistant automatically when you log in:
\`\`\`bash
chmod +x install-launch-agent.sh
./install-launch-agent.sh
\`\`\`

## Uninstallation
To completely remove AI Assistant:
\`\`\`bash
chmod +x uninstall.sh
./uninstall.sh
\`\`\`

## System Requirements
- macOS 10.14 (Mojave) or later
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space
- Microphone access for voice commands

## Support
For help and documentation, visit:
https://github.com/your-repo/ai-assistant
`;

    fs.writeFileSync(path.join(assetsDir, 'INSTALLATION.md'), instructions);
  }

  showInstallerSummary() {
    console.log('\n📊 macOS Installer Summary');
    console.log('========================');
    
    const files = fs.readdirSync(this.distDir);
    
    console.log('Generated installers:');
    files.forEach(file => {
      if (!file.includes('assets')) {
        const filePath = path.join(this.distDir, file);
        const stats = fs.statSync(filePath);
        const size = (stats.size / (1024 * 1024)).toFixed(2);
        const icon = this.getFileIcon(file);
        console.log(`  ${icon} ${file} (${size} MB)`);
      }
    });
    
    console.log('\n🎯 Distribution Options:');
    console.log('  • DMG - Standard macOS installer (drag to Applications)');
    console.log('  • ZIP - Compressed distribution');
    console.log('  • PKG - Advanced package installer');
    
    console.log('\n🔧 Additional Tools:');
    console.log('  • uninstall.sh - Complete removal script');
    console.log('  • install-launch-agent.sh - Auto-start configuration');
    console.log('  • INSTALLATION.md - Complete installation guide');
    
    console.log('\n🚀 Next Steps:');
    console.log('  1. Test installers on clean macOS installation');
    console.log('  2. Notarize for Gatekeeper compatibility');
    console.log('  3. Consider App Store distribution');
  }

  getFileIcon(filename) {
    if (filename.endsWith('.dmg')) return '📀';
    if (filename.endsWith('.zip')) return '🗜️';
    if (filename.endsWith('.pkg')) return '📦';
    if (filename.endsWith('.sh')) return '⚡';
    if (filename.endsWith('.md')) return '📝';
    return '📄';
  }
}

// CLI interface
if (require.main === module) {
  const installer = new MacOSInstaller();
  installer.createInstaller().catch(console.error);
}

module.exports = MacOSInstaller;
