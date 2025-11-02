import { app, BrowserWindow, ipcMain, screen, globalShortcut } from 'electron';
import { join } from 'path';
import { CoreEngine } from '@ai-assistant/core';

class DesktopApp {
  private mainWindow: BrowserWindow | null = null;
  private floatingWindow: BrowserWindow | null = null;
  private coreEngine: CoreEngine;
  private voiceEngine: any;
  private trayManager: TrayManager;
  private autoStartManager: AutoStartManager;

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
      this.autoStartManager = new AutoStartManager();

  // Initialize tray manager
      this.trayManager = new TrayManager(this.mainWindow, this.floatingWindow);
      this.trayManager.initialize();
      
      this.coreEngine.initialize().then(() => {
        console.log('Core engine initialized');
      });

      const isFirstRun = !localStorage.getItem('hasRunBefore');
      if (isFirstRun) {
          setTimeout(() => {
              this.autoStartManager.showAutoStartPrompt();
              localStorage.setItem('hasRunBefore', 'true');
          }, 5000);
      }
      this.handleFirstRunAutoStart();
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

    //Tray IPC handlers
ipcMain.handle('tray:update-icon', (event, iconType) => {
    this.trayManager.updateTrayIcon(iconType);
});

    ipcMain.handle('window:set-floating-position', async (event, x, y) => {
      if (this.floatingWindow) {
        this.floatingWindow.setPosition(x, y);
      }
    });

    // Voice control IPC handlers
        ipcMain.handle('voice:start-listening', async () => {
            await this.voiceEngine.start();
            return { success: true };
        });

        ipcMain.handle('voice:stop-listening', async () => {
            await this.voiceEngine.stop();
            return { success: true };
        });

        // Voice recognition results
        ipcMain.on('voice:recognition-result', (event, result) => {
            this.handleVoiceRecognitionResult(result);
        });


      // Add auto-start IPC handlers
      ipcMain.handle('auto-start:enable', async () => {
          return await this.autoStartManager.enableAutoStart();
      });

      ipcMain.handle('auto-start:disable', async () => {
          return await this.autoStartManager.disableAutoStart();
      });

      ipcMain.handle('auto-start:status', async () => {
            return await this.autoStartManager.isAutoStartEnabled();
      });


    // Add voice training IPC handlers
ipcMain.handle('voice-training:start', async () => {
    // This would be handled in the renderer process
    return { success: true };
});

ipcMain.handle('voice-training:stop', async () => {
    // This would be handled in the renderer process
    return { success: true };
});

ipcMain.on('voice-training:data', (event, trainingData) => {
    // Process and store voice training data
    console.log('Voice training data received:', trainingData);
    
    // Update voice recognition model with new data
    // This would integrate with the actual voice engine
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

    private async setupVoiceEngine(): Promise<void> {
    try {
        // Initialize voice engine
        this.voiceEngine = {
            isListening: false,
            start: async () => {
                this.voiceEngine.isListening = true;
                this.floatingWindow?.webContents.send('voice:activity', {
                    isListening: true,
                    transcript: 'Listening...'
                });
            },
            stop: async () => {
                this.voiceEngine.isListening = false;
                this.floatingWindow?.webContents.send('voice:activity', {
                    isListening: false
                });
            }
        };

    } catch (error) {
        this.logger.error('Voice engine setup failed:', error);
    }
}

private async handleVoiceRecognitionResult(result: any): Promise<void> {
    this.logger.info(`Voice recognition: ${result.text} (confidence: ${result.confidence})`);
    
    // Send to floating window for display
    this.floatingWindow?.webContents.send('voice:activity', {
        transcript: result.text,
        isFinal: result.isFinal
    });

    // Process command if it's a final result
    if (result.isFinal && result.confidence > 0.7) {
        await this.processVoiceCommand(result.text);
    }
}

private async processVoiceCommand(command: string): Promise<void> {
    try {
        this.logger.info(`Processing voice command: ${command}`);
        
        // Send to AI engine for processing
        const response = await this.coreEngine.getAIEngine().processRequest({
            prompt: command,
            context: { source: 'voice' }
        });

        // Send response back to UI
        this.mainWindow?.webContents.send('ai:response', {
            success: true,
            command,
            response: response.text
        });

        this.floatingWindow?.webContents.send('ai:response', {
            success: true,
            command,
            response: response.text
        });

    } catch (error) {
        this.logger.error('Voice command processing failed:', error);
        
        this.mainWindow?.webContents.send('ai:response', {
            success: false,
            error: error.message
        });
    }
}
    
  }
}

new DesktopApp();
