export interface AIConfig {
  openai: {
    apiKey?: string;
    baseURL?: string;
  };
  deepseek: {
    apiKey?: string;
    baseURL?: string;
  };
}

export interface VoiceConfig {
  wakeWord: string;
  language: string;
  speechRate: number;
}

export interface BlockchainConfig {
  enabled: boolean;
  storage: 'ipfs' | 'arweave' | 'local';
}

export class ConfigManager {
  private static instance: ConfigManager;
  private config: {
    ai: AIConfig;
    voice: VoiceConfig;
    blockchain: BlockchainConfig;
  };

  private constructor() {
    this.config = {
      ai: {
        openai: {
          apiKey: process.env.OPENAI_API_KEY,
          baseURL: process.env.OPENAI_BASE_URL
        },
        deepseek: {
          apiKey: process.env.DEEPSEEK_API_KEY,
          baseURL: process.env.DEEPSEEK_BASE_URL
        }
      },
      voice: {
        wakeWord: 'assistant',
        language: 'en',
        speechRate: 1.0
      },
      blockchain: {
        enabled: false,
        storage: 'local'
      }
    };
  }

  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  getAIConfig(): AIConfig {
    return this.config.ai;
  }

  getVoiceConfig(): VoiceConfig {
    return this.config.voice;
  }

  getBlockchainConfig(): BlockchainConfig {
    return this.config.blockchain;
  }

  updateConfig(newConfig: Partial<typeof this.config>): void {
    this.config = { ...this.config, ...newConfig };
  }
}
