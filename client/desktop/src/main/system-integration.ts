import { app, shell, dialog, powerMonitor } from 'electron';
import { exec, spawn } from 'child_process';
import { promisify } from 'util';
import { readdir, readFile, writeFile, stat } from 'fs/promises';
import { join, basename } from 'path';
import { Logger } from '@ai-assistant/core';

const execAsync = promisify(exec);

export interface ApplicationInfo {
    name: string;
    path: string;
    version?: string;
    isRunning: boolean;
    pid?: number;
}

export interface SystemPerformance {
    cpu: {
        usage: number;
        cores: number;
        model: string;
    };
    memory: {
        total: number;
        used: number;
        free: number;
        usage: number;
    };
    disk: {
        total: number;
        used: number;
        free: number;
        usage: number;
    };
    network: {
        interfaces: any[];
    };
}

export class SystemIntegration {
    private logger: Logger;
    private runningProcesses: Map<number, string> = new Map();

    constructor() {
        this.logger = new Logger('SystemIntegration');
        this.initializeSystemMonitoring();
    }

    private initializeSystemMonitoring(): void {
        // Monitor system events
        powerMonitor.on('suspend', () => {
            this.logger.info('System suspending');
            this.emitSystemEvent('suspend');
        });

        powerMonitor.on('resume', () => {
            this.logger.info('System resuming');
            this.emitSystemEvent('resume');
        });

        powerMonitor.on('lock-screen', () => {
            this.logger.info('Screen locked');
            this.emitSystemEvent('lock_screen');
        });

        powerMonitor.on('unlock-screen', () => {
            this.logger.info('Screen unlocked');
            this.emitSystemEvent('unlock_screen');
        });

        // Periodic system monitoring
        setInterval(() => {
            this.monitorSystemPerformance();
        }, 5000);
    }

    async getInstalledApplications(): Promise<ApplicationInfo[]> {
        const applications: ApplicationInfo[] = [];
        const platform = process.platform;

        try {
            if (platform === 'win32') {
                await this.getWindowsApplications(applications);
            } else if (platform === 'darwin') {
                await this.getMacApplications(applications);
            } else if (platform === 'linux') {
                await this.getLinuxApplications(applications);
            }
        } catch (error) {
            this.logger.error('Failed to get installed applications:', error);
        }

        return applications;
    }

    private async getWindowsApplications(applications: ApplicationInfo[]): Promise<void> {
        try {
            // Common Windows program paths
            const programPaths = [
                process.env.PROGRAMFILES,
                process.env['PROGRAMFILES(X86)'],
                process.env.LOCALAPPDATA + '\\Programs'
            ].filter(Boolean);

            for (const programPath of programPaths) {
                if (!programPath) continue;

                try {
                    const items = await readdir(programPath);
                    for (const item of items) {
                        if (item.endsWith('.exe') || await this.isDirectory(join(programPath, item))) {
                            applications.push({
                                name: item.replace('.exe', ''),
                                path: join(programPath, item),
                                isRunning: false
                            });
                        }
                    }
                } catch (error) {
                    // Skip inaccessible directories
                    continue;
                }
            }
        } catch (error) {
            this.logger.error('Error scanning Windows applications:', error);
        }
    }

    private async getMacApplications(applications: ApplicationInfo[]): Promise<void> {
        try {
            const applicationsPath = '/Applications';
            const items = await readdir(applicationsPath);

            for (const item of items) {
                if (item.endsWith('.app')) {
                    applications.push({
                        name: item.replace('.app', ''),
                        path: join(applicationsPath, item),
                        isRunning: false
                    });
                }
            }
        } catch (error) {
            this.logger.error('Error scanning Mac applications:', error);
        }
    }

    private async getLinuxApplications(applications: ApplicationInfo[]): Promise<void> {
        try {
            // Common Linux application directories
            const appDirs = [
                '/usr/share/applications',
                '/usr/local/share/applications',
                process.env.HOME + '/.local/share/applications'
            ];

            for (const appDir of appDirs) {
                try {
                    const files = await readdir(appDir);
                    const desktopFiles = files.filter(f => f.endsWith('.desktop'));

                    for (const desktopFile of desktopFiles) {
                        try {
                            const content = await readFile(join(appDir, desktopFile), 'utf8');
                            const nameMatch = content.match(/Name=(.+)/);
                            const execMatch = content.match(/Exec=(.+)/);

                            if (nameMatch && execMatch) {
                                applications.push({
                                    name: nameMatch[1],
                                    path: execMatch[1].split(' ')[0], // Take first part of exec command
                                    isRunning: false
                                });
                            }
                        } catch (error) {
                            // Skip invalid desktop files
                            continue;
                        }
                    }
                } catch (error) {
                    // Skip inaccessible directories
                    continue;
                }
            }
        } catch (error) {
            this.logger.error('Error scanning Linux applications:', error);
        }
    }

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
            const processes = this.parseProcessList(stdout);
            
            this.runningProcesses.clear();
            processes.forEach(proc => {
                this.runningProcesses.set(proc.pid, proc.name);
            });

            return processes;
        } catch (error) {
            this.logger.error('Failed to get running processes:', error);
            return [];
        }
    }

    private parseProcessList(output: string): any[] {
        const processes: any[] = [];
        const lines = output.split('\n').filter(line => line.trim());

        if (process.platform === 'win32') {
            // Parse Windows tasklist CSV output
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
            // Parse Linux/Mac ps output
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

    async getSystemPerformance(): Promise<SystemPerformance> {
        try {
            const [cpuInfo, memoryInfo, diskInfo, networkInfo] = await Promise.all([
                this.getCPUInfo(),
                this.getMemoryInfo(),
                this.getDiskInfo(),
                this.getNetworkInfo()
            ]);

            return {
                cpu: cpuInfo,
                memory: memoryInfo,
                disk: diskInfo,
                network: networkInfo
            };
        } catch (error) {
            this.logger.error('Failed to get system performance:', error);
            throw error;
        }
    }

    private async getCPUInfo(): Promise<any> {
        try {
            let command: string;
            if (process.platform === 'win32') {
                command = 'wmic cpu get loadpercentage,numberofcores,name /value';
            } else {
                command = "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'";
            }

            const { stdout } = await execAsync(command);
            
            // Parse output based on platform
            if (process.platform === 'win32') {
                const lines = stdout.split('\n').filter(line => line.trim());
                const loadMatch = lines.find(line => line.startsWith('LoadPercentage='));
                const coresMatch = lines.find(line => line.startsWith('NumberOfCores='));
                const nameMatch = lines.find(line => line.startsWith('Name='));

                return {
                    usage: loadMatch ? parseFloat(loadMatch.split('=')[1]) : 0,
                    cores: coresMatch ? parseInt(coresMatch.split('=')[1]) : 1,
                    model: nameMatch ? nameMatch.split('=')[1] : 'Unknown'
                };
            } else {
                const usage = parseFloat(stdout.trim()) || 0;
                const cores = require('os').cpus().length;
                const model = require('os').cpus()[0]?.model || 'Unknown';

                return { usage, cores, model };
            }
        } catch (error) {
            this.logger.error('Failed to get CPU info:', error);
            return { usage: 0, cores: 1, model: 'Unknown' };
        }
    }

    private async getMemoryInfo(): Promise<any> {
        try {
            const os = require('os');
            const totalMemory = os.totalmem();
            const freeMemory = os.freemem();
            const usedMemory = totalMemory - freeMemory;

            return {
                total: totalMemory,
                used: usedMemory,
                free: freeMemory,
                usage: (usedMemory / totalMemory) * 100
            };
        } catch (error) {
            this.logger.error('Failed to get memory info:', error);
            return { total: 0, used: 0, free: 0, usage: 0 };
        }
    }

    private async getDiskInfo(): Promise<any> {
        try {
            const { execSync } = require('child_process');
            let command: string;

            if (process.platform === 'win32') {
                command = 'wmic logicaldisk get size,freespace,caption';
            } else {
                command = 'df -k /';
            }

            const stdout = execSync(command).toString();
            
            // Simple implementation - in production, use a proper disk usage library
            const os = require('os');
            const total = 100 * 1024 * 1024 * 1024; // Placeholder
            const free = 30 * 1024 * 1024 * 1024;   // Placeholder
            const used = total - free;

            return {
                total,
                used,
                free,
                usage: (used / total) * 100
            };
        } catch (error) {
            this.logger.error('Failed to get disk info:', error);
            return { total: 0, used: 0, free: 0, usage: 0 };
        }
    }

    private async getNetworkInfo(): Promise<any> {
        try {
            const os = require('os');
            const interfaces = os.networkInterfaces();

            return {
                interfaces: Object.keys(interfaces).map(name => ({
                    name,
                    addresses: interfaces[name].map((addr: any) => ({
                        address: addr.address,
                        family: addr.family,
                        internal: addr.internal
                    }))
                }))
            };
        } catch (error) {
            this.logger.error('Failed to get network info:', error);
            return { interfaces: [] };
        }
    }

    async openFile(path: string): Promise<{ success: boolean; error?: string }> {
        try {
            await shell.openPath(path);
            return { success: true };
        } catch (error) {
            this.logger.error(`Failed to open file ${path}:`, error);
            return { success: false, error: error.message };
        }
    }

    async showInFileManager(path: string): Promise<{ success: boolean; error?: string }> {
        try {
            await shell.showItemInFolder(path);
            return { success: true };
        } catch (error) {
            this.logger.error(`Failed to show in file manager ${path}:`, error);
            return { success: false, error: error.message };
        }
    }

    async createFile(path: string, content: string = ''): Promise<{ success: boolean; error?: string }> {
        try {
            await writeFile(path, content, 'utf8');
            return { success: true };
        } catch (error) {
            this.logger.error(`Failed to create file ${path}:`, error);
            return { success: false, error: error.message };
        }
    }

    async monitorSystemPerformance(): Promise<void> {
        try {
            const performance = await this.getSystemPerformance();
            
            // Check for alerts
            if (performance.cpu.usage > 80) {
                this.emitSystemEvent('high_cpu_usage', performance.cpu);
            }

            if (performance.memory.usage > 85) {
                this.emitSystemEvent('high_memory_usage', performance.memory);
            }

            if (performance.disk.usage > 90) {
                this.emitSystemEvent('low_disk_space', performance.disk);
            }

        } catch (error) {
            this.logger.error('System performance monitoring failed:', error);
        }
    }

    private emitSystemEvent(event: string, data?: any): void {
        // Emit system event to main process
        if (process.type === 'browser') {
            // In main process
            const { ipcMain } = require('electron');
            ipcMain.emit('system:event', { event, data });
        } else {
            // In renderer process
            if (typeof window !== 'undefined' && (window as any).electronAPI) {
                (window as any).electronAPI.send('system:event', { event, data });
            }
        }
    }

    private async isDirectory(path: string): Promise<boolean> {
        try {
            const stats = await stat(path);
            return stats.isDirectory();
        } catch (error) {
            return false;
        }
    }

    // File system operations
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

    async getFileInfo(path: string): Promise<any> {
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
}
