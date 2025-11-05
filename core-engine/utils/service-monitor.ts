import { Logger } from './logger.js';
import { ServiceClient } from '../service-client.js';

export interface ServiceStatus {
    name: string;
    url: string;
    status: 'healthy' | 'unhealthy' | 'unknown';
    lastCheck: Date;
    responseTime: number;
}

export class ServiceMonitor {
    private logger: Logger;
    private serviceClient: ServiceClient;
    private services: Map<string, ServiceStatus> = new Map();
    private checkInterval: NodeJS.Timeout | null = null;
    private isMonitoring: boolean = false;

    constructor() {
        this.logger = new Logger('ServiceMonitor');
        this.serviceClient = new ServiceClient();
        
        // Initialize services to monitor
        this.services.set('ai-gateway', {
            name: 'AI Gateway',
            url: 'http://localhost:8000',
            status: 'unknown',
            lastCheck: new Date(),
            responseTime: 0
        });
    }

    async startMonitoring(): Promise<void> {
        if (this.isMonitoring) {
            return;
        }

        this.logger.info('Starting service monitoring...');
        
        // Initial health check
        await this.checkAllServices();
        
        // Start periodic monitoring
        this.checkInterval = setInterval(() => {
            this.checkAllServices();
        }, 30000); // Check every 30 seconds
        
        this.isMonitoring = true;
        this.logger.info('Service monitoring started');
    }

    stopMonitoring(): void {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        
        this.isMonitoring = false;
        this.logger.info('Service monitoring stopped');
    }

    async checkAllServices(): Promise<void> {
        for (const [name, service] of this.services) {
            await this.checkService(name, service);
        }
    }

    async checkService(name: string, service: ServiceStatus): Promise<void> {
        const startTime = Date.now();
        
        try {
            const response = await fetch(`${service.url}/health`, {
                signal: AbortSignal.timeout(5000)
            });
            
            const responseTime = Date.now() - startTime;
            
            if (response.ok) {
                service.status = 'healthy';
                service.responseTime = responseTime;
            } else {
                service.status = 'unhealthy';
            }
            
        } catch (error) {
            service.status = 'unhealthy';
            service.responseTime = 0;
        }
        
        service.lastCheck = new Date();
        this.services.set(name, service);
    }

    getServiceStatus(serviceName: string): ServiceStatus | undefined {
        return this.services.get(serviceName);
    }

    getAllServiceStatus(): Map<string, ServiceStatus> {
        return new Map(this.services);
    }

    areServicesHealthy(): boolean {
        return Array.from(this.services.values()).every(service => 
            service.status === 'healthy'
        );
    }

    getUnhealthyServices(): ServiceStatus[] {
        return Array.from(this.services.values()).filter(service => 
            service.status !== 'healthy'
        );
    }

    isMonitoringActive(): boolean {
        return this.isMonitoring;
    }
}
