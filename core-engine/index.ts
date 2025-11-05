// Core Engine - Python-Centric Architecture
// Only contains lightweight system integration and service client

export { SystemIntegration } from './system-integration.js';
export { PluginManager } from './plugin-manager.js';
export { BlockchainManager } from './blockchain-engine/blockchain-manager.js';
export { ServiceClient } from './service-client.js';
export { Logger } from './utils/logger.js';
export { ConfigManager } from './utils/config.js';
export { ServiceMonitor } from './utils/service-monitor.js';

// Simple core engine that focuses on system integration
export class CoreEngine {
    private systemIntegration: SystemIntegration;
    private pluginManager: PluginManager;
    private blockchainManager: BlockchainManager;
    private serviceClient: ServiceClient;
    private serviceMonitor: ServiceMonitor;
    private logger: Logger;

    constructor() {
        this.logger = new Logger('CoreEngine');
        this.systemIntegration = new SystemIntegration();
        this.pluginManager = new PluginManager();
        this.blockchainManager = new BlockchainManager();
        this.serviceClient = new ServiceClient();
        this.serviceMonitor = new ServiceMonitor();
    }

    async initialize(): Promise<void> {
        this.logger.info('Initializing Core Engine (Python-Centric)...');
        
        // Initialize service client first (connects to Python services)
        await this.serviceClient.initialize();
        
        // Initialize other lightweight components
        await this.systemIntegration.initialize();
        await this.pluginManager.initialize();
        await this.blockchainManager.initialize();
        await this.serviceMonitor.startMonitoring();
        
        this.logger.info('Core Engine initialized successfully');
    }

    // System integration methods
    getSystemIntegration(): SystemIntegration {
        return this.systemIntegration;
    }

    // Plugin management
    getPluginManager(): PluginManager {
        return this.pluginManager;
    }

    // Blockchain features
    getBlockchainManager(): BlockchainManager {
        return this.blockchainManager;
    }

    // Service client for AI/voice processing (delegates to Python)
    getServiceClient(): ServiceClient {
        return this.serviceClient;
    }

    // Service monitoring
    getServiceMonitor(): ServiceMonitor {
        return this.serviceMonitor;
    }

    // Simple delegation methods to Python services
    async processCommand(prompt: string, context: any = {}): Promise<any> {
        return await this.serviceClient.processAI({
            prompt,
            context
        });
    }

    async processVoice(audioData: ArrayBuffer, language: string = 'en-US'): Promise<any> {
        return await this.serviceClient.processVoiceCommand({
            audioData,
            language
        });
    }

    async shutdown(): Promise<void> {
        this.logger.info('Shutting down Core Engine...');
        this.serviceMonitor.stopMonitoring();
        await this.pluginManager.shutdown();
        this.logger.info('Core Engine shutdown complete');
    }
}
