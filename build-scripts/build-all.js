const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class BuildAutomation {
  constructor() {
    this.rootDir = path.join(__dirname, '..');
    this.distDir = path.join(this.rootDir, 'dist');
  }

  async buildAll() {
    console.log('🚀 Starting AI Assistant build process...\n');
    
    try {
      // Clean previous builds
      this.cleanDist();
      
      // Build core engine
      await this.buildCoreEngine();
      
      // Build desktop app for all platforms
      await this.buildDesktopApps();
      
      // Create installers
      await this.createInstallers();
      
      console.log('\n✅ Build completed successfully!');
      console.log('📦 Installers available in:', this.distDir);
      
    } catch (error) {
      console.error('❌ Build failed:', error);
      process.exit(1);
    }
  }

  cleanDist() {
    console.log('🧹 Cleaning previous builds...');
    if (fs.existsSync(this.distDir)) {
      fs.rmSync(this.distDir, { recursive: true });
    }
    fs.mkdirSync(this.distDir, { recursive: true });
  }

  async buildCoreEngine() {
    console.log('🔨 Building core engine...');
    execSync('npm run build', { 
      cwd: path.join(this.rootDir, 'core-engine'),
      stdio: 'inherit'
    });
  }

  async buildDesktopApps() {
    console.log('💻 Building desktop applications...');
    
    const platforms = {
      win32: '--win --x64',
      darwin: '--mac --x64 --arm64',
      linux: '--linux --x64'
    };

    for (const [platform, flags] of Object.entries(platforms)) {
      console.log(`\n📦 Building for ${platform}...`);
      
      // Build renderer
      execSync('npm run build:renderer', {
        cwd: path.join(this.rootDir, 'client/desktop'),
        stdio: 'inherit'
      });
      
      // Build main process
      execSync('npm run build:main', {
        cwd: path.join(this.rootDir, 'client/desktop'),
        stdio: 'inherit'
      });
      
      // Package Electron app
      execSync(`npx electron-builder ${flags}`, {
        cwd: path.join(this.rootDir, 'client/desktop'),
        stdio: 'inherit'
      });
    }
  }

  async createInstallers() {
    console.log('📋 Creating installers...');
    
    // Create a releases directory
    const releasesDir = path.join(this.distDir, 'releases');
    fs.mkdirSync(releasesDir, { recursive: true });
    
    // Copy installers to releases directory
    const platforms = ['win-unpacked', 'mac', 'linux-unpacked'];
    platforms.forEach(platform => {
      const source = path.join(this.rootDir, 'client/desktop/dist', platform);
      if (fs.existsSync(source)) {
        const target = path.join(releasesDir, platform);
        this.copyFolderSync(source, target);
      }
    });
    
    // Create README for installers
    this.createInstallerReadme(releasesDir);
  }

  copyFolderSync(source, target) {
    if (!fs.existsSync(target)) {
      fs.mkdirSync(target, { recursive: true });
    }
    
    const files = fs.readdirSync(source);
    files.forEach(file => {
      const sourcePath = path.join(source, file);
      const targetPath = path.join(target, file);
      
      if (fs.lstatSync(sourcePath).isDirectory()) {
        this.copyFolderSync(sourcePath, targetPath);
      } else {
        fs.copyFileSync(sourcePath, targetPath);
      }
    });
  }

  createInstallerReadme(releasesDir) {
    const readmeContent = `# AI Assistant Installers

## Available Installers

### Windows
- **AI Assistant Setup.exe** - Standard installer
- **AI Assistant Portable.exe** - Portable version (no installation needed)

### macOS
- **AI Assistant.dmg** - Drag to Applications folder
- **AI Assistant.zip** - Compressed version

### Linux
- **AI Assistant.AppImage** - Run without installation
- **AI Assistant.deb** - Debian/Ubuntu package
- **AI Assistant.rpm** - Red Hat/Fedora package

## Installation Instructions

### Windows
1. Run "AI Assistant Setup.exe"
2. Follow the installation wizard
3. Launch from Start Menu or Desktop shortcut

### macOS
1. Open "AI Assistant.dmg"
2. Drag AI Assistant to Applications folder
3. Launch from Applications or Spotlight

### Linux
**AppImage:**
\`\`\`bash
chmod +x AI-Assistant-*.AppImage
./AI-Assistant-*.AppImage
\`\`\`

**DEB Package:**
\`\`\`bash
sudo dpkg -i ai-assistant_*.deb
\`\`\`

## System Requirements
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space
- **Microphone**: Required for voice commands

## First Run
1. The app will start minimized in system tray
2. Click the tray icon or use Ctrl+Shift+A to open
3. Configure AI API keys in Settings for full functionality
`;
    
    fs.writeFileSync(path.join(releasesDir, 'INSTALLATION.md'), readmeContent);
  }
}

// Run the build
new BuildAutomation().buildAll();
