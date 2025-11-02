import { app, dialog } from 'electron';
import { exec } from 'child_process';
import { promisify } from 'util';
import { platform } from 'os';
import { Logger } from '@ai-assistant/core';

const execAsync = promisify(exec);

export class AutoStartManager {
    private logger: Logger;

    constructor() {
        this.logger = new Logger('AutoStartManager');
    }

    async enableAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const currentPlatform = platform();
            
            switch (currentPlatform) {
                case 'win32':
                    return await this.enableWindowsAutoStart();
                case 'darwin':
                    return await this.enableMacAutoStart();
                case 'linux':
                    return await this.enableLinuxAutoStart();
                default:
                    return { success: false, error: `Unsupported platform: ${currentPlatform}` };
            }
        } catch (error) {
            this.logger.error('Failed to enable auto-start:', error);
            return { success: false, error: error.message };
        }
    }

    async disableAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const currentPlatform = platform();
            
            switch (currentPlatform) {
                case 'win32':
                    return await this.disableWindowsAutoStart();
                case 'darwin':
                    return await this.disableMacAutoStart();
                case 'linux':
                    return await this.disableLinuxAutoStart();
                default:
                    return { success: false, error: `Unsupported platform: ${currentPlatform}` };
            }
        } catch (error) {
            this.logger.error('Failed to disable auto-start:', error);
            return { success: false, error: error.message };
        }
    }

    async isAutoStartEnabled(): Promise<boolean> {
        try {
            const currentPlatform = platform();
            
            switch (currentPlatform) {
                case 'win32':
                    return await this.isWindowsAutoStartEnabled();
                case 'darwin':
                    return await this.isMacAutoStartEnabled();
                case 'linux':
                    return await this.isLinuxAutoStartEnabled();
                default:
                    return false;
            }
        } catch (error) {
            this.logger.error('Failed to check auto-start status:', error);
            return false;
        }
    }

    private async enableWindowsAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const appPath = process.execPath;
            const appName = 'AI Assistant';
            
            const command = `reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "${appName}" /t REG_SZ /d "${appPath}" /f`;
            
            await execAsync(command);
            this.logger.info('Windows auto-start enabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async disableWindowsAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const appName = 'AI Assistant';
            const command = `reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "${appName}" /f`;
            
            await execAsync(command);
            this.logger.info('Windows auto-start disabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async isWindowsAutoStartEnabled(): Promise<boolean> {
        try {
            const appName = 'AI Assistant';
            const command = `reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "${appName}"`;
            
            await execAsync(command);
            return true;
        } catch (error) {
            return false;
        }
    }

    private async enableMacAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const appPath = app.getPath('exe');
            const plistContent = this.getMacLaunchAgentPlist();
            const plistPath = `${process.env.HOME}/Library/LaunchAgents/com.aiassistant.desktop.plist`;
            
            // Create LaunchAgents directory if it doesn't exist
            await execAsync(`mkdir -p ${process.env.HOME}/Library/LaunchAgents`);
            
            // Write plist file
            const fs = await import('fs');
            const { promisify } = await import('util');
            const writeFileAsync = promisify(fs.writeFile);
            
            await writeFileAsync(plistPath, plistContent);
            
            // Load the launch agent
            await execAsync(`launchctl load ${plistPath}`);
            
            this.logger.info('Mac auto-start enabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async disableMacAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const plistPath = `${process.env.HOME}/Library/LaunchAgents/com.aiassistant.desktop.plist`;
            
            // Unload the launch agent
            await execAsync(`launchctl unload ${plistPath}`);
            
            // Remove plist file
            await execAsync(`rm -f ${plistPath}`);
            
            this.logger.info('Mac auto-start disabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async isMacAutoStartEnabled(): Promise<boolean> {
        try {
            const plistPath = `${process.env.HOME}/Library/LaunchAgents/com.aiassistant.desktop.plist`;
            const command = `launchctl list | grep com.aiassistant.desktop`;
            
            await execAsync(command);
            return true;
        } catch (error) {
            return false;
        }
    }

    private async enableLinuxAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const appPath = process.execPath;
            const desktopFileContent = this.getLinuxDesktopFile();
            const desktopFilePath = `${process.env.HOME}/.config/autostart/ai-assistant.desktop`;
            
            // Create autostart directory if it doesn't exist
            await execAsync(`mkdir -p ${process.env.HOME}/.config/autostart`);
            
            // Write desktop file
            const fs = await import('fs');
            const { promisify } = await import('util');
            const writeFileAsync = promisify(fs.writeFile);
            
            await writeFileAsync(desktopFilePath, desktopFileContent);
            
            // Make it executable
            await execAsync(`chmod +x ${desktopFilePath}`);
            
            this.logger.info('Linux auto-start enabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async disableLinuxAutoStart(): Promise<{ success: boolean; error?: string }> {
        try {
            const desktopFilePath = `${process.env.HOME}/.config/autostart/ai-assistant.desktop`;
            await execAsync(`rm -f ${desktopFilePath}`);
            
            this.logger.info('Linux auto-start disabled');
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    private async isLinuxAutoStartEnabled(): Promise<boolean> {
        try {
            const desktopFilePath = `${process.env.HOME}/.config/autostart/ai-assistant.desktop`;
            const command = `test -f "${desktopFilePath}" && echo "exists"`;
            
            const result = await execAsync(command);
            return result.stdout.includes('exists');
        } catch (error) {
            return false;
        }
    }

    private getMacLaunchAgentPlist(): string {
        const appPath = app.getPath('exe');
        
        return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aiassistant.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>${appPath}</string>
        <string>--hidden</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>`;
    }

    private getLinuxDesktopFile(): string {
        const appPath = process.execPath;
        const appIcon = `${process.cwd()}/assets/icon.png`;
        
        return `[Desktop Entry]
Type=Application
Version=1.0
Name=AI Assistant
Comment=Privacy-first AI Assistant
Exec=${appPath} --hidden
Icon=${appIcon}
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true`;
    }

    async showAutoStartPrompt(): Promise<boolean> {
        const result = await dialog.showMessageBox({
            type: 'question',
            buttons: ['Yes', 'No', 'Ask Later'],
            defaultId: 0,
            title: 'Auto-start',
            message: 'Would you like AI Assistant to start automatically when you log in?',
            detail: 'This will help you get started quickly with voice commands.'
        });

        if (result.response === 0) { // Yes
            const enableResult = await this.enableAutoStart();
            if (enableResult.success) {
                return true;
            } else {
                await dialog.showMessageBox({
                    type: 'error',
                    title: 'Auto-start Error',
                    message: 'Failed to enable auto-start',
                    detail: enableResult.error
                });
            }
        }

        return false;
    }
}
