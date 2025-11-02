import { Tray, Menu, nativeImage, app, BrowserWindow } from 'electron';
import { join } from 'path';
import { Logger } from '@ai-assistant/core';

export class TrayManager {
    private tray: Tray | null = null;
    private logger: Logger;
    private mainWindow: BrowserWindow;
    private floatingWindow: BrowserWindow;

    constructor(mainWindow: BrowserWindow, floatingWindow: BrowserWindow) {
        this.logger = new Logger('TrayManager');
        this.mainWindow = mainWindow;
        this.floatingWindow = floatingWindow;
    }

    async initialize(): Promise<void> {
        try {
            // Create tray icon
            const iconPath = join(__dirname, '../../assets/tray-icon.png');
            let trayImage = nativeImage.createFromPath(iconPath);
            
            // Fallback if icon doesn't exist
            if (trayImage.isEmpty()) {
                trayImage = nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=');
            }

            // Resize for tray
            trayImage = trayImage.resize({ width: 16, height: 16 });

            this.tray = new Tray(trayImage);
            this.setupTrayMenu();
            this.setupTrayEvents();

            this.logger.info('System tray initialized');
        } catch (error) {
            this.logger.error('Failed to initialize system tray:', error);
        }
    }

    private setupTrayMenu(): void {
        if (!this.tray) return;

        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'Show Assistant',
                click: () => {
                    this.showMainWindow();
                }
            },
            {
                label: 'Quick Actions',
                submenu: [
                    {
                        label: 'Start Listening',
                        click: () => {
                            this.startVoiceListening();
                        }
                    },
                    {
                        label: 'Open Recent',
                        click: () => {
                            this.openRecentFiles();
                        }
                    },
                    {
                        label: 'System Info',
                        click: () => {
                            this.showSystemInfo();
                        }
                    }
                ]
            },
            { type: 'separator' },
            {
                label: 'Voice Settings',
                click: () => {
                    this.showVoiceSettings();
                }
            },
            {
                label: 'AI Models',
                click: () => {
                    this.showAIModels();
                }
            },
            { type: 'separator' },
            {
                label: 'Plugins',
                click: () => {
                    this.showPlugins();
                }
            },
            {
                label: 'About',
                click: () => {
                    this.showAbout();
                }
            },
            { type: 'separator' },
            {
                label: 'Quit AI Assistant',
                click: () => {
                    this.quitApplication();
                }
            }
        ]);

        this.tray.setContextMenu(contextMenu);
        this.tray.setToolTip('AI Assistant\nClick to show menu');
    }

    private setupTrayEvents(): void {
        if (!this.tray) return;

        // Single click to toggle main window
        this.tray.on('click', () => {
            this.toggleMainWindow();
        });

        // Double click to start listening
        this.tray.on('double-click', () => {
            this.startVoiceListening();
        });

        // Right click already handled by context menu
    }

    private toggleMainWindow(): void {
        if (this.mainWindow.isVisible()) {
            this.mainWindow.hide();
        } else {
            this.showMainWindow();
        }
    }

    private showMainWindow(): void {
        this.mainWindow.show();
        this.mainWindow.focus();
        
        // Ensure it's not minimized
        if (this.mainWindow.isMinimized()) {
            this.mainWindow.restore();
        }
    }

    private async startVoiceListening(): Promise<void> {
        try {
            // Send IPC message to start listening
            this.mainWindow.webContents.send('tray:start-listening');
            this.floatingWindow.webContents.send('tray:start-listening');
            
            // Show floating window if hidden
            if (!this.floatingWindow.isVisible()) {
                this.floatingWindow.show();
            }

            this.logger.info('Voice listening started from tray');
        } catch (error) {
            this.logger.error('Failed to start voice listening:', error);
        }
    }

    private openRecentFiles(): void {
        this.mainWindow.webContents.send('tray:open-recent');
        this.showMainWindow();
    }

    private showSystemInfo(): void {
        this.mainWindow.webContents.send('tray:show-system-info');
        this.showMainWindow();
    }

    private showVoiceSettings(): void {
        this.mainWindow.webContents.send('tray:show-voice-settings');
        this.showMainWindow();
    }

    private showAIModels(): void {
        this.mainWindow.webContents.send('tray:show-ai-models');
        this.showMainWindow();
    }

    private showPlugins(): void {
        this.mainWindow.webContents.send('tray:show-plugins');
        this.showMainWindow();
    }

    private showAbout(): void {
        this.mainWindow.webContents.send('tray:show-about');
        this.showMainWindow();
    }

    private quitApplication(): void {
        // Save state and quit
        this.mainWindow.webContents.send('app:quitting');
        
        setTimeout(() => {
            app.quit();
        }, 100);
    }

    updateTrayIcon(iconType: 'normal' | 'listening' | 'processing' | 'error'): void {
        if (!this.tray) return;

        const icons = {
            normal: '🟢',
            listening: '🎤',
            processing: '🔄',
            error: '🔴'
        };

        // In a real app, you'd use actual icon files
        this.tray.setToolTip(`AI Assistant - ${iconType.charAt(0).toUpperCase() + iconType.slice(1)}`);
    }

    destroy(): void {
        if (this.tray) {
            this.tray.destroy();
            this.tray = null;
        }
    }
}
