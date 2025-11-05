export interface AppConfig {
    aiGateway: {
        url: string;
        timeout: number;
    };
    voiceProcessor: {
        enabled: boolean;
        sampleRate: number;
    };
    blockchain: {
        enabled: boolean;
    };
    plugins: {
        autoLoad: boolean;
        directory: string;
    };
}

export class ConfigManager {
    private static instance: ConfigManager;
    private config: AppConfig;

    private constructor() {
        this.config = this.getDefaultConfig();
        this.loadFromEnvironment();
    }

    static getInstance(): ConfigManager {
        if (!ConfigManager.instance) {
            ConfigManager.instance = new ConfigManager();
        }
        return ConfigManager.instance;
    }

    getConfig(): AppConfig {
        return { ...this.config };
    }

    updateConfig(newConfig: Partial<AppConfig>): void {
        this.config = { ...this.config, ...newConfig };
    }

    getAIGatewayUrl(): string {
        return this.config.aiGateway.url;
    }

    isBlockchainEnabled(): boolean {
        return this.config.blockchain.enabled;
    }

    private getDefaultConfig(): AppConfig {
        return {
            aiGateway: {
                url: 'http://localhost:8000',
                timeout: 30000
            },
            voiceProcessor: {
                enabled: true,
                sampleRate: 16000
            },
            blockchain: {
                enabled: false
            },
            plugins: {
                autoLoad: true,
                directory: './plugins'
            }
        };
    }

    private loadFromEnvironment(): void {
        // Load configuration from environment variables
        if (process.env.AI_GATEWAY_URL) {
            this.config.aiGateway.url = process.env.AI_GATEWAY_URL;
        }
        
        if (process.env.BLOCKCHAIN_ENABLED) {
            this.config.blockchain.enabled = process.env.BLOCKCHAIN_ENABLED === 'true';
        }
    }
}
