const { app, dialog, BrowserWindow, ipcMain, screen, Menu, systemPreferences, Tray, nativeImage } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Prevent EPIPE errors on stdout and stderr from crashing the app (e.g., when parent process closes the pipe)
process.stdout.on('error', (err) => {
  if (err.code === 'EPIPE') {
    // Ignore EPIPE errors
  }
});
process.stderr.on('error', (err) => {
  if (err.code === 'EPIPE') {
    // Ignore EPIPE errors
  }
});
process.on('uncaughtException', (err) => {
  if (err.code === 'EPIPE') {
    // Ignore EPIPE errors gracefully
    return;
  }
  console.error('Uncaught Exception:', err);
});

let mainWindow;
let orbWindow;
let settingsWindow;
let tray = null;
let backendProcess = null;
let backendPort = 8000;

const net = require('net');

function getFreePort(startPort = 8000) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.on('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(getFreePort(startPort + 1));
      } else {
        resolve(startPort);
      }
    });
    server.listen(startPort, '0.0.0.0', () => {
      server.close(() => {
        resolve(startPort);
      });
    });
  });
}

// ── Backend Auto-Launch ────────────────────────────────────────────────────
function startBackend() {
  // In packaged app: use the bundled PyInstaller binary from extraResources
  // In dev mode: use start_backend.sh
  const isPackaged = app.isPackaged;

  let backendExe, backendArgs, backendCwd;

  if (isPackaged) {
    // Bundled binary lives at Contents/Resources/kruboo_backend/kruboo_backend
    const resourcesPath = process.resourcesPath;
    backendExe = path.join(resourcesPath, 'kruboo_backend', 'kruboo_backend');
    backendArgs = [];
    backendCwd = path.join(resourcesPath, 'kruboo_backend');
  } else {
    // Dev mode: run via shell script with venv
    backendExe = '/bin/bash';
    backendArgs = [path.join(__dirname, '..', 'start_backend.sh')];
    backendCwd = path.join(__dirname, '..');
  }

  // Fallback: check if executable exists, show dialog if missing
  const checkPath = isPackaged ? backendExe : backendArgs[0];
  if (!fs.existsSync(checkPath)) {
    console.error(`[Backend] Executable not found: ${checkPath}`);
    dialog.showErrorBox(
      'Backend Missing',
      `The Python backend executable/launcher could not be found at:\n${checkPath}\n\nPlease build the backend first.`
    );
    return;
  }

  console.log(`[Backend] Starting on port ${backendPort}: ${backendExe}`);

  backendProcess = spawn(backendExe, backendArgs, {
    cwd: backendCwd,
    env: {
      ...process.env,
      LLAMA_NO_METAL: '1',
      GGML_NO_METAL: '1',
      GGML_METAL_PATH_RESOURCES: '',
      GPT4ALL_BACKEND: 'cpu',
      PORT: backendPort.toString(),
    },
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  backendProcess.stdout.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.warn('[Backend ERR]', d.toString().trim()));

  backendProcess.on('exit', (code) => {
    console.warn(`[Backend] Exited with code ${code}. Restarting in 3s...`);
    if (!app.isQuitting) setTimeout(startBackend, 3000);
  });
}

app.isQuitting = false;
app.on('before-quit', () => {
  app.isQuitting = true;
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
});

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 950,
    height: 750,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    titleBarStyle: 'hiddenInset',
    vibrancy: 'sidebar',
    visualEffectState: 'active',
    backgroundColor: '#00000000',
    transparent: true,
    frame: false
  });

  mainWindow.loadFile('index.html');
}

function createSettingsWindow() {
    settingsWindow = new BrowserWindow({
        width: 600,
        height: 700,
        show: false,
        frame: false,
        transparent: true,
        vibrancy: 'sidebar',
        visualEffectState: 'active',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    settingsWindow.loadFile('settings.html');
}

function createOrbWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  
  orbWindow = new BrowserWindow({
    width: 250,
    height: 250,
    x: Math.floor((width - 250) / 2),
    y: 20,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  orbWindow.loadFile('orb.html');
}

function createTray() {
  try {
    const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
    let icon = nativeImage.createFromPath(iconPath);
    icon = icon.resize({ width: 18, height: 18 });
    icon.setTemplateImage(true);
    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
      { label: 'Show Orb', click: () => { if (orbWindow) orbWindow.show(); } },
      { label: 'Hide Orb', click: () => { if (orbWindow) orbWindow.hide(); } },
      { label: 'Toggle Chat', click: () => { 
          if (mainWindow.isVisible()) mainWindow.hide();
          else { mainWindow.show(); mainWindow.focus(); }
      } },
      { type: 'separator' },
      { label: 'Settings', click: () => { if (settingsWindow) settingsWindow.show(); } },
      { type: 'separator' },
      { label: 'Quit Kruboo', click: () => { app.quit(); } }
    ]);

    tray.setToolTip('Kruboo AI Assistant');
    tray.setContextMenu(contextMenu);
  } catch (err) {
    console.error('Failed to create Tray:', err);
  }
}

app.whenReady().then(async () => {
  // Find a free port dynamically starting from 8000
  backendPort = await getFreePort(8000);
  console.log(`[Main] Using dynamic backend port: ${backendPort}`);

  // Register synchronous IPC listener for renderer windows
  ipcMain.on('get-backend-port', (event) => {
    event.returnValue = backendPort;
  });

  // ---- Auto Update ----
  if (!app.isPackaged) {
    console.log('Skipping auto-updates in dev mode');
  } else {
    autoUpdater.checkForUpdatesAndNotify();
    autoUpdater.on('update-available', info => {
      console.log('Update available:', info.version);
    });
    autoUpdater.on('update-downloaded', info => {
      console.log('Update downloaded; will install now');
      autoUpdater.quitAndInstall();
    });
    autoUpdater.on('error', err => {
      console.error('Auto-updater error:', err);
    });
  }
    // Start the Python backend first (auto-restarts on crash)
    startBackend();

    if (process.platform === 'darwin') {
      try {
        const status = systemPreferences.getMediaAccessStatus('microphone');
        console.log('Current microphone status:', status);
        if (status !== 'granted') {
          const result = await systemPreferences.askForMediaAccess('microphone');
          console.log('Microphone access result:', result);
        }
      } catch (err) {
        console.error('Failed to request microphone access:', err);
      }
    }

    // Set permission request handler for the default session
    // This allows the renderer window to get permission for the microphone
    const { session } = require('electron');
    session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
        const url = webContents.getURL();
        console.log(`Permission requested: ${permission} from ${url}`);
        
        if (permission === 'media' || permission === 'audio-capture') {
            return callback(true);
        }
        callback(false);
    });

    createMainWindow();
    createSettingsWindow();
    createOrbWindow();
    createTray();

    // Register Global Hotkeys
    const { globalShortcut } = require('electron');
    
    // Command+Shift+Space: Toggle Main Chat Window
    globalShortcut.register('Command+Shift+Space', () => {
        if (!mainWindow || mainWindow.isDestroyed()) createMainWindow();
        if (mainWindow.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow.show();
            mainWindow.focus();
        }
    });

    // Command+Shift+V: Trigger Voice Listening (Orb)
    globalShortcut.register('Command+Shift+V', () => {
        if (!orbWindow || orbWindow.isDestroyed()) createOrbWindow();
        orbWindow.show();
        orbWindow.webContents.send('trigger-voice-listen');
    });

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
        createSettingsWindow();
        createOrbWindow();
    }
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// IPC Handlers
ipcMain.handle('ask-ai', async (event, requestData) => {
    try {
        const response = await fetch('http://127.0.0.1:8000/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error("IPC Ask-AI Error:", error);
        return { success: false, error: error.message };
    }
});

let streamingAbortController = null;

ipcMain.on('abort-ai-stream', () => {
    if (streamingAbortController) {
        streamingAbortController.abort();
        streamingAbortController = null;
    }
});

ipcMain.on('ask-ai-stream', async (event, requestData) => {
    if (streamingAbortController) streamingAbortController.abort();
    streamingAbortController = new AbortController();
    
    try {
        const response = await fetch('http://127.0.0.1:8000/stream_query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData),
            signal: streamingAbortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            if (event.sender.isDestroyed()) break;

            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const data = JSON.parse(line);
                        if (!event.sender.isDestroyed()) {
                            event.reply('ai-stream-token', data);
                        }
                    } catch (e) {
                         // Likely partial JSON chunk, ignore for now
                    }
                }
            }
        }
    } catch (error) {
        if (!event.sender.isDestroyed()) {
            event.reply('ai-stream-error', error.message);
        }
    }
});

ipcMain.on('toggle-main-window', () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
        createMainWindow();
        mainWindow.show();
        return;
    }
    if (mainWindow.isVisible()) mainWindow.hide();
    else {
        mainWindow.show();
        mainWindow.focus();
    }
});

ipcMain.on('hide-orb-window', () => { if (orbWindow) orbWindow.hide(); });
ipcMain.on('show-orb-window', () => { if (orbWindow) orbWindow.show(); });
ipcMain.on('open-settings-window', () => { if (settingsWindow) { settingsWindow.show(); settingsWindow.focus(); } });
ipcMain.on('close-settings-window', () => { if (settingsWindow) settingsWindow.hide(); });
ipcMain.on('settings-updated', () => {
    if (orbWindow && !orbWindow.isDestroyed()) orbWindow.webContents.send('refresh-settings');
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('refresh-settings');
});

ipcMain.on('trigger-action', (event, action) => {
    if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('execute-action', action);
    }
});

// ---- Persona IPC Handlers ----
const { getPersonas, savePersona, deletePersona, setActivePersona, getActivePersona } = require('./src/services/store');

ipcMain.handle('persona-get-all', async () => {
  try {
    return await getPersonas();
  } catch (e) {
    console.error('Error getting personas', e);
    return [];
  }
});

ipcMain.handle('persona-get-active', async () => {
  try {
    return await getActivePersona();
  } catch (e) {
    console.error('Error getting active persona', e);
    return null;
  }
});

ipcMain.handle('persona-set-active', async (event, id) => {
  try {
    await setActivePersona(id);
    return true;
  } catch (e) {
    console.error('Error setting active persona', e);
    return false;
  }
});

ipcMain.handle('persona-save', async (event, persona) => {
  try {
    await savePersona(persona);
    return true;
  } catch (e) {
    console.error('Error saving persona', e);
    return false;
  }
});

ipcMain.handle('persona-delete', async (event, id) => {
  try {
    await deletePersona(id);
    return true;
  } catch (e) {
    console.error('Error deleting persona', e);
    return false;
  }
});

ipcMain.on('set-orb-status', (event, status) => {
    if (!tray) return;
    const neutralPath = path.join(__dirname, 'assets', 'tray-icon.png');
    const micPath = path.join(__dirname, 'assets', 'tray-mic.png');
    
    let imgPath = neutralPath;
    if (status === 'listening' || status === 'thinking') {
        imgPath = micPath;
    }
    
    let icon = nativeImage.createFromPath(imgPath);
    icon = icon.resize({ width: 18, height: 18 });
    icon.setTemplateImage(true);
    tray.setImage(icon);
});

ipcMain.handle('run-command', async (event, cmd) => {
  const { exec } = require('child_process');
  
  // Security Sanitization
  const lower = cmd.toLowerCase().trim();
  const dangerousPatterns = [
    /\brm\b/,        // rm command
    /\bsudo\b/,      // privilege escalation
    /\bcurl\b/,      // downloading scripts
    /\bwget\b/,      // downloading scripts
    /\bchmod\b/,     // permission modification
    /\bchown\b/,     // ownership modification
    /[>|]/           // redirection or piping
  ];

  const isDangerous = dangerousPatterns.some(pattern => pattern.test(lower));
  if (isDangerous) {
    return {
      success: false,
      error: "Security Exception: This command contains restricted patterns (rm, sudo, curl, wget, chmod, redirection, or piping) and has been blocked for safety.",
      stdout: "",
      stderr: ""
    };
  }

  return new Promise((resolve) => {
    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        resolve({ success: false, error: error.message, stdout, stderr });
      } else {
        resolve({ success: true, stdout, stderr });
      }
    });
  });
});

// Propose commands based on simple keyword matching
ipcMain.handle('propose-commands', async (event, userRequest) => {
  const lower = userRequest.toLowerCase();
  const suggestions = [];
  if (lower.includes('install python')) {
    suggestions.push('brew install python');
  }
  if (lower.includes('list') && lower.includes('file')) {
    suggestions.push('ls -la');
  }
  if (lower.includes('show') && lower.includes('directory')) {
    suggestions.push('pwd');
  }
  if (lower.includes('who am i') || lower.includes('identity')) {
    suggestions.push('whoami');
  }
  if (lower.includes('delete') && lower.includes('file')) {
    suggestions.push('rm <filepath>');
  }
  // fallback: return all allowed commands
  if (suggestions.length === 0) {
    suggestions.push(...['ls -la', 'pwd', 'whoami', 'brew install python', 'rm <filepath>']);
  }
  return suggestions;
});
