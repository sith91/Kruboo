const { app, BrowserWindow, ipcMain, screen, Menu, systemPreferences, Tray, nativeImage } = require('electron');
const path = require('path');

let mainWindow;
let orbWindow;
let settingsWindow;
let tray = null;

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
