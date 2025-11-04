#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { program } = require('commander');

// Initialize CLI
program
  .name('build')
  .description('AI Assistant Build Tool')
  .version('1.0.0');

program
  .command('all')
  .description('Build all platforms')
  .action(buildAll);

program
  .command('win')
  .description('Build for Windows')
  .action(() => buildPlatform('win'));

program
  .command('mac')
  .description('Build for macOS')
  .action(() => buildPlatform('mac'));

program
  .command('linux')
  .description('Build for Linux')
  .action(() => buildPlatform('linux'));

program
  .command('dev')
  .description('Development build')
  .action(buildDev);

program.parse();

// Build functions
async function buildAll() {
  console.log('🚀 Building AI Assistant for all platforms...\n');
  
  try {
    // Clean and setup
    cleanDist();
    
    // Build core engine
    await buildCore();
    
    // Build all platforms
    await buildPlatform('win');
    await buildPlatform('mac');
    await buildPlatform('linux');
    
    // Create installers
    await createInstallers();
    
    console.log('\n✅ Build completed successfully!');
    console.log('📦 Installers available in: dist/releases/');
    
  } catch (error) {
    console.error('❌ Build failed:', error);
    process.exit(1);
  }
}

async function buildPlatform(platform) {
  console.log(`\n📦 Building for ${platform.toUpperCase()}...`);
  
  const desktopPath = path.join(__dirname, 'client/desktop');
  
  // Build steps
  execSync('npm run build:renderer', { cwd: desktopPath, stdio: 'inherit' });
  execSync('npm run build:main', { cwd: desktopPath, stdio: 'inherit' });
  
  // Platform-specific build
  const commands = {
    win: 'npx electron-builder --win --x64',
    mac: 'npx electron-builder --mac --x64 --arm64', 
    linux: 'npx electron-builder --linux --x64'
  };
  
  execSync(commands[platform], { cwd: desktopPath, stdio: 'inherit' });
}

async function buildCore() {
  console.log('🔨 Building core engine...');
  execSync('npm run build', { 
    cwd: path.join(__dirname, 'core-engine'),
    stdio: 'inherit'
  });
}

async function buildDev() {
  console.log('🔧 Creating development build...');
  
  // Build core
  await buildCore();
  
  // Build desktop app (no packaging)
  const desktopPath = path.join(__dirname, 'client/desktop');
  execSync('npm run build:renderer', { cwd: desktopPath, stdio: 'inherit' });
  execSync('npm run build:main', { cwd: desktopPath, stdio: 'inherit' });
  
  console.log('✅ Development build ready! Run: npm run dev');
}

function cleanDist() {
  console.log('🧹 Cleaning previous builds...');
  const distPath = path.join(__dirname, 'dist');
  if (fs.existsSync(distPath)) {
    fs.rmSync(distPath, { recursive: true });
  }
  fs.mkdirSync(distPath, { recursive: true });
}

async function createInstallers() {
  console.log('📋 Creating installers package...');
  
  const releasesDir = path.join(__dirname, 'dist', 'releases');
  fs.mkdirSync(releasesDir, { recursive: true });
  
  // Copy platform builds
  const platforms = [
    { src: 'client/desktop/dist/win-unpacked', dest: 'windows' },
    { src: 'client/desktop/dist/mac', dest: 'macos' }, 
    { src: 'client/desktop/dist/linux-unpacked', dest: 'linux' }
  ];
  
  for (const platform of platforms) {
    const source = path.join(__dirname, platform.src);
    if (fs.existsSync(source)) {
      const target = path.join(releasesDir, platform.dest);
      copyFolderSync(source, target);
    }
  }
  
  createReadme(releasesDir);
}

function copyFolderSync(source, target) {
  if (!fs.existsSync(target)) {
    fs.mkdirSync(target, { recursive: true });
  }
  
  const files = fs.readdirSync(source);
  for (const file of files) {
    const sourcePath = path.join(source, file);
    const targetPath = path.join(target, file);
    
    if (fs.lstatSync(sourcePath).isDirectory()) {
      copyFolderSync(sourcePath, targetPath);
    } else {
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

function createReadme(releasesDir) {
  const readme = `# AI Assistant - Installation Files

## Choose your platform:

### 🪟 Windows
- Run \`AI Assistant Setup.exe\` for installation
- Or use \`AI Assistant Portable.exe\` for no installation

### 🍎 macOS  
- Open \`AI Assistant.dmg\` and drag to Applications
- Or use \`AI Assistant.zip\` for compressed version

### 🐧 Linux
- \`ai-assistant-x.x.x.AppImage\` - Run without installation
- \`ai-assistant_x.x.x_amd64.deb\` - Debian/Ubuntu package
- \`ai-assistant-x.x.x.x86_64.rpm\` - Red Hat/Fedora package

## First Run
1. The app starts in system tray (look for the AI icon)
2. Use Ctrl+Shift+A to open the main window
3. Configure AI API keys in Settings for full functionality

## Support
Visit https://github.com/your-repo/ai-assistant for documentation and support.
`;
  
  fs.writeFileSync(path.join(releasesDir, 'INSTALL.md'), readme);
}
