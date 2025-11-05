import { Logger } from './utils/logger.js';
import { exec } from 'child_process';
import { promisify } from 'util';
import { readdir, readFile, stat } from 'fs/promises';
import { join, basename } from 'path';

const execAsync = promisify(exec);

export interface ApplicationInfo {
    name: string;
    path: string;
    version?: string;
    isRunning: boolean;
    pid?: number;
}

export interface SystemInfo {
    platform: string;
    arch: string;
    version: string;
    memory: {
        total: number;
        used: number;
        free: number;
        usage: number;
    };
    cpu: {
        usage: number;
        cores: number;
        model: string;
    };
}

export interface FileInfo {
    path: string;
    name: string;
    size: number;
    created: Date;
    modified: Date;
    isDirectory: boolean;
    isFile: boolean;
}

export class SystemIntegration {
    private logger: Logger;

    constructor() {
        this.logger = new Logger('SystemIntegration');
    }

    async initialize(): Promise<void> {
        this.logger.info('System Integration initialized');
    }

    // Application Management
    async launchApplication(appName: string): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.info(`Launching application: ${appName}`);

            let command: string;

            if (process.platform === 'win32') {
                command = `start "" "${appName}"`;
            } else if (process.platform === 'darwin') {
                command = `open -a "${appName}"`;
            } else {
                command = appName;
            }

            await execAsync(command);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to launch application ${appName}:`, error);
            return { success: false, error: error.message };
        }
    }

    async closeApplication(appName: string): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.info(`Closing application: ${appName}`);

            let command: string;

            if (process.platform === 'win32') {
                command = `taskkill /IM "${appName}.exe" /F`;
            } else if (process.platform === 'darwin') {
                command = `pkill -f "${appName}"`;
            } else {
                command = `pkill -f "${appName}"`;
            }

            await execAsync(command);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to close application ${appName}:`, error);
            return { success: false, error: error.message };
        }
    }

    async getRunningProcesses(): Promise<any[]> {
        try {
            const command = process.platform === 'win32' 
                ? 'tasklist /FO CSV /NH'
                : 'ps -eo pid,comm,pcpu,pmem --no-headers';

            const { stdout } = await execAsync(command);
            return this.parseProcessList(stdout);
        } catch (error) {
            this.logger.error('Failed to get running processes:', error);
            return [];
        }
    }

    // System Information
    async getSystemInfo(): Promise<SystemInfo> {
        const os = require('os');
        
        const totalMemory = os.totalmem();
        const freeMemory = os.freemem();
        const usedMemory = totalMemory - freeMemory;

        return {
            platform: process.platform,
            arch: process.arch,
            version: process.version,
            memory: {
                total: totalMemory,
                used: usedMemory,
                free: freeMemory,
                usage: (usedMemory / totalMemory) * 100
            },
            cpu: {
                usage: 0, // Would need to calculate
                cores: os.cpus().length,
                model: os.cpus()[0]?.model || 'Unknown'
            }
        };
    }

    // File System Operations
    async searchFiles(directory: string, pattern: string): Promise<string[]> {
        try {
            const { execSync } = require('child_process');
            let command: string;

            if (process.platform === 'win32') {
                command = `dir "${directory}\\${pattern}" /s /b`;
            } else {
                command = `find "${directory}" -name "${pattern}" 2>/dev/null`;
            }

            const stdout = execSync(command).toString();
            return stdout.split('\n').filter(line => line.trim());
        } catch (error) {
            this.logger.error(`File search failed for ${pattern}:`, error);
            return [];
        }
    }

    async getFileInfo(path: string): Promise<FileInfo> {
        try {
            const stats = await stat(path);
            return {
                path,
                name: basename(path),
                size: stats.size,
                created: stats.birthtime,
                modified: stats.mtime,
                isDirectory: stats.isDirectory(),
                isFile: stats.isFile()
            };
        } catch (error) {
            this.logger.error(`Failed to get file info for ${path}:`, error);
            throw error;
        }
    }

    // Utility Methods
    async openFile(path: string): Promise<{ success: boolean; error?: string }> {
        try {
            const { shell } = require('electron');
            await shell.openPath(path);
            return { success: true };
        } catch (error) {
            this.logger.error(`Failed to open file ${path}:`, error);
            return { success: false, error: error.message };
        }
    }

    async showInFileManager(path: string): Promise<{ success: boolean; error?: string }> {
        try {
            const { shell } = require('electron');
            await shell.showItemInFolder(path);
            return { success: true };
        } catch (error) {
            this.logger.error(`Failed to show in file manager ${path}:`, error);
            return { success: false, error: error.message };
        }
    }

    private parseProcessList(output: string): any[] {
        const processes: any[] = [];
        const lines = output.split('\n').filter(line => line.trim());

        if (process.platform === 'win32') {
            for (const line of lines) {
                const match = line.match(/"([^"]+)","([^"]+)","([^"]+)"/);
                if (match) {
                    processes.push({
                        name: match[1],
                        pid: parseInt(match[2]),
                        memory: match[3]
                    });
                }
            }
        } else {
            for (const line of lines) {
                const parts = line.trim().split(/\s+/);
                if (parts.length >= 4) {
                    processes.push({
                        pid: parseInt(parts[0]),
                        name: parts[1],
                        cpu: parseFloat(parts[2]),
                        memory: parseFloat(parts[3])
                    });
                }
            }
        }

        return processes;
    }
}
