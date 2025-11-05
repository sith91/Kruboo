const { execSync, spawn } = require('child_process');
const fs = require('fs-extra');
const path = require('path');
const archiver = require('archiver');

class WindowsBuilder {
  constructor() {
    this.rootDir = path.join(__dirname, '..');
    this.distDir = path.join(this.rootDir, 'dist', 'windows');
    this.desktopDir = path.join(this.rootDir, 'client', 'desktop');
    this.buildDir = path.join(this.desktopDir, 'build');
  }

  async build() {
    console.log('🪟 Starting Windows build process...\n');
    
    try {
      // Setup environment
      this.cleanWindowsDist();
      this.checkWindowsRequirements();
      
      // Build steps
      await this.buildCoreEngine();
      await this.buildDesktopApp();
      await this.createWindowsInstaller();
      await this.createPortableVersion();
      await this.createZipPackage();
      
      console.log('\n✅ Windows build completed successfully!');
      console.log('📦 Installers available in:', this.distDir);
      
      this.showBuildSummary();
      
    } catch (error) {
      console.error('❌ Windows build failed:', error);
      process.exit(1);
    }
  }

  cleanWindowsDist() {
    console.log('🧹 Cleaning Windows distribution directory...');
    if (fs.existsSync(this.distDir)) {
      fs.removeSync(this.distDir);
    }
    fs.ensureDirSync(this.distDir);
  }

  checkWindowsRequirements() {
    console.log('🔍 Checking Windows build requirements...');
    
    // Check if we're on Windows (optional, but good for warnings)
    if (process.platform !== 'win32') {
      console.log('⚠️  Warning: Not running on Windows. Some features may not work correctly.');
    }
    
    // Check for required tools
    try {
      execSync('node --version', { stdio: 'pipe' });
      execSync('npm --version', { stdio: 'pipe' });
      console.log('✅ Node.js and npm are available');
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
      
      // Build Windows executable with Electron Builder
      console.log('📦 Packaging Windows executable...');
      execSync('npx electron-builder --win --x64 --publish=never', { 
        cwd: this.desktopDir, 
        stdio: 'inherit' 
      });
      
      console.log('✅ Desktop application built successfully');
      
    } catch (error) {
      throw new Error(`Desktop app build failed: ${error.message}`);
    }
  }

  async createWindowsInstaller() {
    console.log('\n📋 Creating Windows installer...');
    
    const nsisScript = `
; AI Assistant Windows Installer
Unicode true

!include "MUI2.nsh"
!include "FileFunc.nsh"

; Basic installer settings
Name "AI Assistant"
OutFile "${this.distDir}\\\\AI_Assistant_Setup.exe"
InstallDir "$PROGRAMFILES64\\\\AI Assistant"
InstallDirRegKey HKLM "Software\\\\AI Assistant" "Install_Dir"
RequestExecutionLevel admin

; Modern UI configuration
!define MUI_ABORTWARNING
!define MUI_ICON "${this.buildDir}\\\\icon.ico"
!define MUI_UNICON "${this.buildDir}\\\\icon.ico"

; Installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${this.rootDir}\\\\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

Section "AI Assistant"
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  
  ; Copy application files
  File /r "${this.desktopDir}\\\\dist\\\\win-unpacked\\\\*.*"
  
  ; Create registry entries
  WriteRegStr HKLM "Software\\\\AI Assistant" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "DisplayName" "AI Assistant"
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "UninstallString" '"$INSTDIR\\\\uninstall.exe"'
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "DisplayIcon" "$INSTDIR\\\\AI Assistant.exe"
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "Publisher" "AI Assistant Team"
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "DisplayVersion" "1.0.0"
  WriteRegStr HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant" "URLInfoAbout" "https://github.com/your-repo/ai-assistant"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\\\\uninstall.exe"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\\\\AI Assistant"
  CreateShortcut "$SMPROGRAMS\\\\AI Assistant\\\\AI Assistant.lnk" "$INSTDIR\\\\AI Assistant.exe"
  CreateShortcut "$SMPROGRAMS\\\\AI Assistant\\\\Uninstall.lnk" "$INSTDIR\\\\uninstall.exe"
  CreateShortcut "$DESKTOP\\\\AI Assistant.lnk" "$INSTDIR\\\\AI Assistant.exe"
SectionEnd

Section "Start Menu Folder" 
  ; Already created above
SectionEnd

Section "Auto Start"
  WriteRegStr HKCU "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run" "AI Assistant" "$INSTDIR\\\\AI Assistant.exe --minimized"
SectionEnd

Section "File Associations"
  ; Add file associations if needed
SectionEnd

Section "Uninstall"
  ; Remove registry entries
  DeleteRegKey HKLM "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\AI Assistant"
  DeleteRegKey HKLM "Software\\\\AI Assistant"
  DeleteRegValue HKCU "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run" "AI Assistant"
  
  ; Remove shortcuts
  Delete "$SMPROGRAMS\\\\AI Assistant\\\\*.*"
  RMDir "$SMPROGRAMS\\\\AI Assistant"
  Delete "$DESKTOP\\\\AI Assistant.lnk"
  
  ; Remove installation directory
  RMDir /r "$INSTDIR"
SectionEnd

Function .onInstSuccess
  ; Optional: Launch app after installation
  ; ExecShell "" "$INSTDIR\\\\AI Assistant.exe"
FunctionEnd
`;

    // Write NSIS script
    const nsisFilePath = path.join(this.distDir, 'installer.nsi');
    fs.writeFileSync(nsisFilePath, nsisScript);
    
    try {
      // Check if NSIS is available
      execSync('makensis -VERSION', { stdio: 'pipe' });
      
      console.log('🔧 Building installer with NSIS...');
      execSync(`makensis "${nsisFilePath}"`, { stdio: 'inherit' });
      
      // Clean up NSIS script
      fs.removeSync(nsisFilePath);
      
      console.log('✅ Windows installer created: AI_Assistant_Setup.exe');
      
    } catch (error) {
      console.log('⚠️  NSIS not available, using Electron Builder installer instead');
      this.fallbackInstaller();
    }
  }

  async fallbackInstaller() {
    // Copy Electron Builder's NSIS installer
    const electronInstaller = path.join(this.desktopDir, 'dist', 'AI Assistant Setup 1.0.0.exe');
    if (fs.existsSync(electronInstaller)) {
      fs.copySync(electronInstaller, path.join(this.distDir, 'AI_Assistant_Setup.exe'));
      console.log('✅ Using Electron Builder installer');
    }
  }

  async createPortableVersion() {
    console.log('\n💼 Creating portable version...');
    
    const portableDir = path.join(this.distDir, 'portable');
    const unpackedDir = path.join(this.desktopDir, 'dist', 'win-unpacked');
    
    if (fs.existsSync(unpackedDir)) {
      // Copy unpacked app to portable directory
      fs.copySync(unpackedDir, portableDir);
      
      // Create portable configuration
      const portableConfig = {
        portable: true,
        autoStart: false,
        dataDirectory: './data'
      };
      
      fs.writeJsonSync(path.join(portableDir, 'portable.json'), portableConfig, { spaces: 2 });
      
      // Create a batch file for easy launching
      const batchContent = `@echo off
echo Starting AI Assistant (Portable)...
cd /d "%~dp0"
start "" "AI Assistant.exe"
`;
      fs.writeFileSync(path.join(portableDir, 'Start AI Assistant.bat'), batchContent);
      
      console.log('✅ Portable version created');
    }
  }

  async createZipPackage() {
    console.log('\n📦 Creating ZIP package...');
    
    const unpackedDir = path.join(this.desktopDir, 'dist', 'win-unpacked');
    
    if (fs.existsSync(unpackedDir)) {
      const output = fs.createWriteStream(path.join(this.distDir, 'AI_Assistant_Portable.zip'));
      const archive = archiver('zip', { zlib: { level: 9 } });
      
      return new Promise((resolve, reject) => {
        output.on('close', () => {
          console.log('✅ ZIP package created: AI_Assistant_Portable.zip');
          resolve();
        });
        
        archive.on('error', (err) => {
          reject(err);
        });
        
        archive.pipe(output);
        archive.directory(unpackedDir, 'AI Assistant');
        archive.finalize();
      });
    }
  }

  showBuildSummary() {
    console.log('\n📊 Windows Build Summary');
    console.log('======================');
    
    const files = fs.readdirSync(this.distDir);
    
    console.log('Generated files:');
    files.forEach(file => {
      const filePath = path.join(this.distDir, file);
      const stats = fs.statSync(filePath);
      const size = (stats.size / (1024 * 1024)).toFixed(2);
      console.log(`  📄 ${file} (${size} MB)`);
    });
    
    console.log('\n🎯 Distribution Options:');
    console.log('  • AI_Assistant_Setup.exe - Standard installer with auto-start');
    console.log('  • Portable folder - No installation required');
    console.log('  • AI_Assistant_Portable.zip - Compressed portable version');
    
    console.log('\n🚀 Next Steps:');
    console.log('  1. Test the installer on a clean Windows machine');
    console.log('  2. Upload to GitHub Releases');
    console.log('  3. Create digital signature for trust (recommended)');
  }
}

// CLI interface
if (require.main === module) {
  const builder = new WindowsBuilder();
  builder.build().catch(console.error);
}

module.exports = WindowsBuilder;
