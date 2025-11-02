import { app, BrowserWindow, ipcMain, screen, globalShortcut } from 'electron';
import { join } from 'path';
import { CoreEngine } from '@ai-assistant/core';

class DesktopApp {
  private mainWindow: BrowserWindow | null = null;
  private floatingWindow: BrowserWindow | null = null;
  private coreEngine: CoreEngine;

  constructor() {
    this.coreEngine = new CoreEngine();
    this.setupApp();
  }

  private setupApp(): void {
    app.whenReady().then(() => {
      this.createMainWindow();
      this.createFloatingWindow();
      this.setupIPC();
      this.setupGlobalShortcuts();
      
      this.coreEngine.initialize().then(() => {
        console.log('Core engine initialized');
      });
    });

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createMainWindow();
        this.createFloatingWindow();
      }
    });
  }

  private createMainWindow(): void {
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: join(__dirname, 'preload.js')
      },
      show: false,
      icon: join(__dirname, '../assets/icon.png')
    });

    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadURL('http://localhost:3000');
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(join(__dirname, 'renderer/index.html'));
    }

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });
  }

  private createFloatingWindow(): void {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    
    this.floatingWindow = new BrowserWindow({
      width: 80,
      height: 80,
      x: width - 100,
      y: height - 100,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: false,
      frame: false,
      transparent: true,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: join(__dirname, 'preload.js')
      },
      show: true
    });

    this.floatingWindow.loadFile(join(__dirname, 'renderer/floating.html'));

    // Make window draggable
    this.floatingWindow.setIgnoreMouseEvents(false);

    this.floatingWindow.on('closed', () => {
      this.floatingWindow = null;
    });
  }

  private setupIPC(): void {
    // Voice control IPC
    ipcMain.handle('voice:start-listening', async () => {
      return { success: true };
    });

    ipcMain.handle('voice:stop-listening', async () => {
      return { success: true };
    });

    // AI processing IPC
    ipcMain.handle('ai:process-request', async (event, request) => {
      try {
        const response = await this.coreEngine.getAIEngine().processRequest(request);
        return { success: true, data: response };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });

    // System control IPC
    ipcMain.handle('system:open-app', async (event, appName) => {
      return this.openApplication(appName);
    });

    ipcMain.handle('system:get-info', async () => {
      return this.getSystemInfo();
    });

    // Window control IPC
    ipcMain.handle('window:toggle-main', async () => {
      if (this.mainWindow) {
        if (this.mainWindow.isVisible()) {
          this.mainWindow.hide();
        } else {
          this.mainWindow.show();
          this.mainWindow.focus();
        }
      }
    });

    ipcMain.handle('window:set-floating-position', async (event, x, y) => {
      if (this.floatingWindow) {
        this.floatingWindow.setPosition(x, y);
      }
    });
  }

  private setupGlobalShortcuts(): void {
    globalShortcut.register('CommandOrControl+Shift+A', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
      }
    });

    globalShortcut.register('Escape', () => {
      if (this.mainWindow && this.mainWindow.isFocused()) {
        this.mainWindow.hide();
      }
    });
  }

  private async openApplication(appName: string): Promise<{ success: boolean; error?: string }> {
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);

      let command = '';
      
      if (process.platform === 'win32') {
        command = `start ${appName}`;
      } else if (process.platform === 'darwin') {
        command = `open -a "${appName}"`;
      } else {
        command = `${appName}`;
      }

      await execAsync(command);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private getSystemInfo(): any {
    return {
      platform: process.platform,
      arch: process.arch,
      version: process.version,
      memory: process.memoryUsage(),
      uptime: process.uptime()
    };
  }
}

new DesktopApp();
