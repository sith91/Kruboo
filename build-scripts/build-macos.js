const { execSync, spawn } = require('child_process');
const fs = require('fs-extra');
const path = require('path');
const plist = require('plist');

class MacOSBuilder {
  constructor() {
    this.rootDir = path.join(__dirname, '..');
    this.distDir = path.join(this.rootDir, 'dist', 'macos');
    this.desktopDir = path.join(this.rootDir, 'client', 'desktop');
    this.buildDir = path.join(this.desktopDir, 'build');
    this.appName = 'AI Assistant';
  }

  async build() {
    console.log('🍎 Starting macOS build process...\n');
    
    try {
      // Setup environment
      this.cleanMacOSDist();
      this.checkMacOSRequirements();
      
      // Build steps
      await this.buildCoreEngine();
      await this.buildDesktopApp();
      await this.createDMGInstaller();
      await this.createZipDistribution();
      await this.createNotarizationProfile();
      await this.createLaunchAgent();
      
      console.log('\n✅ macOS build completed successfully!');
      console.log('📦 Installers available in:', this.distDir);
      
      this.showBuildSummary();
      
    } catch (error) {
      console.error('❌ macOS build failed:', error);
      process.exit(1);
    }
  }

  cleanMacOSDist() {
    console.log('🧹 Cleaning macOS distribution directory...');
    if (fs.existsSync(this.distDir)) {
      fs.removeSync(this.distDir);
    }
    fs.ensureDirSync(this.distDir);
  }

  checkMacOSRequirements() {
    console.log('🔍 Checking macOS build requirements...');
    
    // Check if we're on macOS
    if (process.platform !== 'darwin') {
      console.log('⚠️  Warning: Not running on macOS. Some features may not work correctly.');
    }
    
    // Check for required tools
    try {
      execSync('node --version', { stdio: 'pipe' });
      execSync('npm --version', { stdio: 'pipe' });
      console.log('✅ Node.js and npm are available');
      
      // Check for Xcode command line tools
      try {
        execSync('xcode-select --version', { stdio: 'pipe' });
        console.log('✅ Xcode command line tools are available');
      } catch (error) {
        console.log('⚠️  Xcode command line tools not found. DMG creation may fail.');
      }
      
    } catch (error) {
      throw new Error('Node.js and npm are required for building');
    }
  }

  async buildCoreEngine() {
    console.log('\n🔨 Building core engine...');
    
    const coreDir = path.join(this.rootDir, 'core-engine');
    
    try {
      // Install dependencies if needed
      if (!fs.existsSync(path.join(coreDir, 'node_modules'))) {
        console.log('📦 Installing core engine dependencies...');
        execSync('npm install', { cwd: coreDir, stdio: 'inherit' });
      }
      
      // Build TypeScript
      execSync('npm run build', { cwd: coreDir, stdio: 'inherit' });
      console.log('✅ Core engine built successfully');
      
    } catch (error) {
      throw new Error(`Core engine build failed: ${error.message}`);
    }
  }

  async buildDesktopApp() {
    console.log('\n💻 Building desktop application...');
    
    try {
      // Install dependencies if needed
      if (!fs.existsSync(path.join(this.desktopDir, 'node_modules'))) {
        console.log('📦 Installing desktop dependencies...');
        execSync('npm install', { cwd: this.desktopDir, stdio: 'inherit' });
      }
      
      // Build renderer (Vite)
      console.log('🎨 Building renderer process...');
      execSync('npm run build:renderer', { cwd: this.desktopDir, stdio: 'inherit' });
      
      // Build main process (TypeScript)
      console.log('⚡ Building main process...');
      execSync('npm run build:main', { cwd: this.desktopDir, stdio: 'inherit' });
      
      // Build macOS app with Electron Builder
      console.log('📦 Packaging macOS application...');
      const archFlags = '--x64 --arm64'; // Universal binary for both Intel and Apple Silicon
      execSync(`npx electron-builder --mac ${archFlags} --publish=never`, { 
        cwd: this.desktopDir, 
        stdio: 'inherit' 
      });
      
      console.log('✅ Desktop application built successfully');
      
    } catch (error) {
      throw new Error(`Desktop app build failed: ${error.message}`);
    }
  }

  async createDMGInstaller() {
    console.log('\n📀 Creating DMG installer...');
    
    const macBuildDir = path.join(this.desktopDir, 'dist', 'mac');
    
    if (fs.existsSync(macBuildDir)) {
      const appFiles = fs.readdirSync(macBuildDir);
      const dmgFile = appFiles.find(file => file.endsWith('.dmg'));
      
      if (dmgFile) {
        const sourceDMG = path.join(macBuildDir, dmgFile);
        const destDMG = path.join(this.distDir, `${this.appName}.dmg`);
        
        fs.copySync(sourceDMG, destDMG);
        console.log(`✅ DMG installer created: ${this.appName}.dmg`);
        
        // Also copy the .app bundle for direct installation
        const appBundle = appFiles.find(file => file.endsWith('.app'));
        if (appBundle) {
          const sourceApp = path.join(macBuildDir, appBundle);
          const destApp = path.join(this.distDir, `${this.appName}.app`);
          fs.copySync(sourceApp, destApp);
          console.log(`✅ App bundle copied: ${this.appName}.app`);
        }
      } else {
        console.log('⚠️  No DMG file found, creating custom DMG...');
        await this.createCustomDMG();
      }
    }
  }

  async createCustomDMG() {
    // Fallback DMG creation using hdiutil
    const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
    
    if (fs.existsSync(appBundlePath)) {
      try {
        const dmgName = `${this.appName}.dmg`;
        const tempDir = path.join(this.distDir, 'temp_dmg');
        
        // Create temporary directory structure
        fs.ensureDirSync(tempDir);
        fs.copySync(appBundlePath, path.join(tempDir, `${this.appName}.app`));
        
        // Create Applications folder alias
        execSync(`ln -s /Applications ${tempDir}/Applications`);
        
        // Create DMG
        const dmgPath = path.join(this.distDir, dmgName);
        execSync(`hdiutil create -volname "${this.appName}" -srcfolder "${tempDir}" -ov -format UDZO "${dmgPath}"`, {
          stdio: 'inherit'
        });
        
        // Clean up
        fs.removeSync(tempDir);
        
        console.log(`✅ Custom DMG created: ${dmgName}`);
        
      } catch (error) {
        console.log('⚠️  Custom DMG creation failed:', error.message);
        console.log('📦 Using app bundle directly');
      }
    }
  }

  async createZipDistribution() {
    console.log('\n🗜️ Creating ZIP distribution...');
    
    const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
    
    if (fs.existsSync(appBundlePath)) {
      try {
        const zipPath = path.join(this.distDir, `${this.appName}.zip`);
        
        // Create ZIP using native macOS zip
        execSync(`zip -qr "${zipPath}" "${appBundlePath}"`, {
          stdio: 'inherit'
        });
        
        console.log(`✅ ZIP distribution created: ${this.appName}.zip`);
        
      } catch (error) {
        console.log('⚠️  ZIP creation failed:', error.message);
      }
    }
  }

  async createNotarizationProfile() {
    console.log('\n🔐 Creating notarization profile...');
    
    // Notarization is required for macOS distribution
    const notarizationConfig = {
      notarize: {
        teamId: process.env.APPLE_TEAM_ID || 'YOUR_TEAM_ID',
        appBundleId: 'com.aiassistant.desktop',
        appPath: `dist/mac/${this.appName}.app`
      }
    };
    
    const configPath = path.join(this.distDir, 'notarization-config.json');
    fs.writeJsonSync(configPath, notarizationConfig, { spaces: 2 });
    
    // Create notarization script
    const notarizeScript = `#!/bin/bash

# Notarize AI Assistant for macOS
# Requirements: Apple Developer Account with App Store Connect access

echo "🔐 Starting notarization process..."

# Check environment variables
if [ -z "$APPLE_ID" ] || [ -z "$APPLE_ID_PASSWORD" ] || [ -z "$APPLE_TEAM_ID" ]; then
  echo "❌ Missing required environment variables:"
  echo "   - APPLE_ID: Your Apple Developer ID"
  echo "   - APPLE_ID_PASSWORD: App-specific password"
  echo "   - APPLE_TEAM_ID: Your Developer Team ID"
  echo ""
  echo "📝 How to set up:"
  echo "1. Create app-specific password: https://appleid.apple.com"
  echo "2. Export variables:"
  echo "   export APPLE_ID=your@email.com"
  echo "   export APPLE_ID_PASSWORD=abcd-efgh-ijkl-mnop"
  echo "   export APPLE_TEAM_ID=AB123CD456"
  exit 1
fi

# Notarize the app
npx electron-notarize \\
  --app "dist/macos/${this.appName}.app" \\
  --appleId "$APPLE_ID" \\
  --appleIdPassword "$APPLE_ID_PASSWORD" \\
  --teamId "$APPLE_TEAM_ID"

echo "✅ Notarization submitted! Check email for status."
echo "📋 Once approved, staple the notarization:"
echo "   xcrun stapler staple 'dist/macos/${this.appName}.app'"
`;

    const scriptPath = path.join(this.distDir, 'notarize.sh');
    fs.writeFileSync(scriptPath, notarizeScript);
    execSync(`chmod +x "${scriptPath}"`);
    
    console.log('✅ Notarization profile created');
    console.log('📝 Run ./notarize.sh after setting Apple Developer credentials');
  }

  async createLaunchAgent() {
    console.log('\n🚀 Creating Launch Agent for auto-start...');
    
    const launchAgentPlist = {
      Label: 'com.aiassistant.desktop',
      ProgramArguments: [
        '/Applications/AI Assistant.app/Contents/MacOS/AI Assistant',
        '--minimized'
      ],
      RunAtLoad: true,
      KeepAlive: false,
      StandardOutPath: '/tmp/ai-assistant.log',
      StandardErrorPath: '/tmp/ai-assistant-error.log'
    };
    
    const plistPath = path.join(this.distDir, 'com.aiassistant.desktop.plist');
    fs.writeFileSync(plistPath, plist.build(launchAgentPlist));
    
    // Create installation script
    const installScript = `#!/bin/bash

# Install AI Assistant Launch Agent for auto-start

echo "🚀 Installing AI Assistant Launch Agent..."

# Copy plist to LaunchAgents directory
cp "com.aiassistant.desktop.plist" ~/Library/LaunchAgents/

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.aiassistant.desktop.plist

echo "✅ Launch Agent installed successfully!"
echo "🔧 The app will now start automatically when you log in."
echo ""
echo "To uninstall:"
echo "  launchctl unload ~/Library/LaunchAgents/com.aiassistant.desktop.plist"
echo "  rm ~/Library/LaunchAgents/com.aiassistant.desktop.plist"
`;

    const scriptPath = path.join(this.distDir, 'install-launch-agent.sh');
    fs.writeFileSync(scriptPath, installScript);
    execSync(`chmod +x "${scriptPath}"`);
    
    console.log('✅ Launch Agent configuration created');
  }

  async optimizeAppBundle() {
    console.log('\n⚡ Optimizing app bundle...');
    
    const appBundlePath = path.join(this.desktopDir, 'dist', 'mac', `${this.appName}.app`);
    
    if (fs.existsSync(appBundlePath)) {
      try {
        // Remove unnecessary files to reduce bundle size
        const filesToRemove = [
          'Contents/Resources/app/node_modules/electron/dist/Electron.app',
          'Contents/Resources/app/node_modules/**/*.d.ts',
          'Contents/Resources/app/node_modules/**/test/',
          'Contents/Resources/app/node_modules/**/tests/',
          'Contents/Resources/app/node_modules/**/doc/',
          'Contents/Resources/app/node_modules/**/docs/'
        ];
        
        filesToRemove.forEach(pattern => {
          const fullPattern = path.join(appBundlePath, pattern);
          try {
            execSync(`find "${appBundlePath}" -name "${pattern.split('/').pop()}" -type d -exec rm -rf {} +`, {
              stdio: 'pipe'
            });
          } catch (error) {
            // Ignore errors for missing files
          }
        });
        
        console.log('✅ App bundle optimized');
        
      } catch (error) {
        console.log('⚠️  App optimization failed:', error.message);
      }
    }
  }

  showBuildSummary() {
    console.log('\n📊 macOS Build Summary');
    console.log('====================');
    
    const files = fs.readdirSync(this.distDir);
    
    console.log('Generated files:');
    files.forEach(file => {
      const filePath = path.join(this.distDir, file);
      const stats = fs.statSync(filePath);
      const size = (stats.size / (1024 * 1024)).toFixed(2);
      const icon = file.endsWith('.app') ? '📱' : file.endsWith('.dmg') ? '📀' : file.endsWith('.zip') ? '🗜️' : '📄';
      console.log(`  ${icon} ${file} (${size} MB)`);
    });
    
    console.log('\n🎯 Distribution Options:');
    console.log('  • .app bundle - Drag to Applications folder');
    console.log('  • .dmg file - Standard macOS installer');
    console.log('  • .zip file - Compressed distribution');
    
    console.log('\n🔧 Additional Tools:');
    console.log('  • notarize.sh - For App Store distribution');
    console.log('  • install-launch-agent.sh - For auto-start');
    
    console.log('\n🚀 Installation Instructions:');
    console.log('  1. DMG: Open and drag to Applications');
    console.log('  2. ZIP: Extract and drag .app to Applications');
    console.log('  3. Direct: Run the .app bundle directly');
    
    console.log('\n📝 Next Steps:');
    console.log('  1. Test on both Intel and Apple Silicon Macs');
    console.log('  2. Notarize for Gatekeeper compatibility');
    console.log('  3. Consider App Store distribution');
  }
}

// CLI interface
if (require.main === module) {
  const builder = new MacOSBuilder();
  builder.build().catch(console.error);
}

module.exports = MacOSBuilder;
