// core-engine/system-integration/system-monitor.ts
import os from 'os';
import { exec } from 'child_process';
import { promisify } from 'util';
import { EventEmitter } from 'events';

const execAsync = promisify(exec);

export interface SystemInfo {
  cpu: {
    usage: number;
    cores: number;
    model: string;
    speed: number;
  };
  memory: {
    total: number;
    free: number;
    used: number;
    percentage: number;
  };
  disk: {
    total: number;
    free: number;
    used: number;
    percentage: number;
  };
  processes: ProcessInfo[];
  uptime: number;
  platform: string;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu: number;
  memory: number;
  command: string;
}

export interface AlertRule {
  id: string;
  metric: 'cpu' | 'memory' | 'disk' | 'process';
  condition: 'gt' | 'lt' | 'eq';
  threshold: number;
  message: string;
  enabled: boolean;
}

export class SystemMonitor extends EventEmitter {
  private monitoring: boolean = false;
  private alertRules: AlertRule[] = [];
  private monitoringInterval: NodeJS.Timeout | null = null;

  // Process management
  async getRunningProcesses(): Promise<ProcessInfo[]> {
    if (process.platform === 'win32') {
      return this.getWindowsProcesses();
    } else {
      return this.getUnixProcesses();
    }
  }

  async killProcess(pid: number): Promise<void> {
    try {
      process.kill(pid);
    } catch (error) {
      throw new Error(`Failed to kill process ${pid}: ${error.message}`);
    }
  }

  // System information
  async getSystemInfo(): Promise<SystemInfo> {
    const [cpuUsage, processes] = await Promise.all([
      this.getCpuUsage(),
      this.getRunningProcesses()
    ]);

    return {
      cpu: {
        usage: cpuUsage,
        cores: os.cpus().length,
        model: os.cpus()[0].model,
        speed: os.cpus()[0].speed
      },
      memory: {
        total: os.totalmem(),
        free: os.freemem(),
        used: os.totalmem() - os.freemem(),
        percentage: ((os.totalmem() - os.freemem()) / os.totalmem()) * 100
      },
      disk: await this.getDiskUsage(),
      processes: processes.slice(0, 50), // Top 50 processes
      uptime: os.uptime(),
      platform: `${os.platform()} ${os.release()}`
    };
  }

  // Resource monitoring with alerts
  startMonitoring(intervalMs: number = 5000): void {
    this.monitoring = true;
    this.monitoringInterval = setInterval(async () => {
      try {
        const systemInfo = await this.getSystemInfo();
        this.checkAlerts(systemInfo);
        this.emit('monitor-update', systemInfo);
      } catch (error) {
        this.emit('monitor-error', error);
      }
    }, intervalMs);
  }

  stopMonitoring(): void {
    this.monitoring = false;
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
  }

  // Alert management
  addAlertRule(rule: AlertRule): void {
    this.alertRules.push(rule);
  }

  removeAlertRule(ruleId: string): void {
    this.alertRules = this.alertRules.filter(rule => rule.id !== ruleId);
  }

  private async checkAlerts(systemInfo: SystemInfo): Promise<void> {
    for (const rule of this.alertRules) {
      if (!rule.enabled) continue;

      let value: number;
      switch (rule.metric) {
        case 'cpu':
          value = systemInfo.cpu.usage;
          break;
        case 'memory':
          value = systemInfo.memory.percentage;
          break;
        case 'disk':
          value = systemInfo.disk.percentage;
          break;
        default:
          continue;
      }

      const shouldAlert = this.evaluateCondition(value, rule.condition, rule.threshold);
      if (shouldAlert) {
        this.emit('alert', {
          rule,
          value,
          message: rule.message,
          timestamp: new Date()
        });
      }
    }
  }

  private evaluateCondition(value: number, condition: string, threshold: number): boolean {
    switch (condition) {
      case 'gt': return value > threshold;
      case 'lt': return value < threshold;
      case 'eq': return Math.abs(value - threshold) < 0.1;
      default: return false;
    }
  }

  private async getCpuUsage(): Promise<number> {
    return new Promise((resolve) => {
      const start = os.cpus();
      
      setTimeout(() => {
        const end = os.cpus();
        let totalIdle = 0, totalTick = 0;

        for (let i = 0; i < start.length; i++) {
          const startCPU = start[i];
          const endCPU = end[i];
          
          const idle = endCPU.times.idle - startCPU.times.idle;
          const total = Object.values(endCPU.times).reduce((a, b) => a + b) - 
                       Object.values(startCPU.times).reduce((a, b) => a + b);
          
          totalIdle += idle;
          totalTick += total;
        }

        const usage = 100 - (totalIdle / totalTick) * 100;
        resolve(Math.round(usage * 100) / 100);
      }, 1000);
    });
  }

  private async getUnixProcesses(): Promise<ProcessInfo[]> {
    try {
      const { stdout } = await execAsync('ps -eo pid,pcpu,pmem,comm,args --no-headers');
      return stdout.split('\n')
        .filter(line => line.trim())
        .map(line => {
          const [pid, cpu, memory, command, ...args] = line.trim().split(/\s+/);
          return {
            pid: parseInt(pid),
            name: command,
            cpu: parseFloat(cpu),
            memory: parseFloat(memory),
            command: args.join(' ')
          };
        })
        .sort((a, b) => b.cpu - a.cpu);
    } catch (error) {
      console.error('Error getting processes:', error);
      return [];
    }
  }
}
