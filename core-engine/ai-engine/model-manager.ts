import { Logger } from '../utils/logger.js';
import { ConfigManager } from '../utils/config.js';
import { OpenAIAdapter } from './adapters/openai.js';
import { DeepSeekAdapter } from './adapters/deepseek.js';
import { LocalModelAdapter } from './adapters/local-model.js';

export interface ModelConfig {
    name: string;
    type: 'cloud' | 'local';
    capabilities: string[];
    costPerToken?: number;
    maxTokens: number;
    enabled: boolean;
    priority: number;
}

export interface ModelResponse {
    text: string;
    model: string;
    tokens: number;
    cost?: number;
    latency: number;
    confidence: number;
}

export class ModelManager {
    private logger: Logger;
    private config: ConfigManager;
    private models: Map<string, any> = new Map();
    private activeModels: ModelConfig[] = [];
    private modelWeights: Map<string, number> = new Map();

    constructor() {
        this.logger = new Logger('ModelManager');
        this.config = ConfigManager.getInstance();
        this.initializeModels();
    }

    private initializeModels(): void {
        // Register available models
        this.models.set('deepseek', new DeepSeekAdapter());
        this.models.set('openai', new OpenAIAdapter());
        this.models.set('local', new LocalModelAdapter());

        // Configure active models based on settings
        this.updateActiveModels();
    }

    private updateActiveModels(): void {
        this.activeModels = [
            {
                name: 'deepseek',
                type: 'cloud',
                capabilities: ['reasoning', 'coding', 'analysis'],
                costPerToken: 0.0000001,
                maxTokens: 32768,
                enabled: true,
                priority: 10
            },
            {
                name: 'openai',
                type: 'cloud',
                capabilities: ['creative', 'conversational', 'analysis'],
                costPerToken: 0.00000015,
                maxTokens: 16384,
                enabled: true,
                priority: 8
            },
            {
                name: 'local',
                type: 'local',
                capabilities: ['general', 'privacy'],
                maxTokens: 4096,
                enabled: true,
                priority: 5
            }
        ].filter(model => model.enabled);

        // Initialize model weights based on priority
        this.activeModels.forEach(model => {
            this.modelWeights.set(model.name, model.priority);
        });
    }

    async processRequest(prompt: string, context: any = {}): Promise<ModelResponse> {
        const startTime = Date.now();
        
        try {
            // Select appropriate model based on request type and context
            const selectedModel = await this.selectModel(prompt, context);
            
            this.logger.info(`Using model: ${selectedModel.name} for request`);

            // Process the request
            const response = await selectedModel.adapter.process({
                prompt,
                context,
                modelPreference: selectedModel.name
            });

            const latency = Date.now() - startTime;

            // Calculate cost if applicable
            let cost = undefined;
            if (selectedModel.config.costPerToken) {
                cost = response.tokensUsed * selectedModel.config.costPerToken;
            }

            // Update model performance metrics
            await this.updateModelPerformance(selectedModel.name, latency, response.confidence);

            return {
                text: response.text,
                model: selectedModel.name,
                tokens: response.tokensUsed,
                cost,
                latency,
                confidence: response.confidence
            };

        } catch (error) {
            this.logger.error(`Model processing failed: ${error}`);
            
            // Fallback to next available model
            return await this.fallbackProcess(prompt, context, startTime);
        }
    }

    private async selectModel(prompt: string, context: any): Promise<{ name: string; adapter: any; config: ModelConfig }> {
        // Get user preference if set
        const userPreference = context.modelPreference || this.config.getAIConfig().preferredModel;
        
        if (userPreference && this.models.has(userPreference)) {
            const adapter = this.models.get(userPreference);
            const config = this.activeModels.find(m => m.name === userPreference);
            if (config && await adapter.isAvailable()) {
                return { name: userPreference, adapter, config };
            }
        }

        // Auto-select based on request type and model capabilities
        const requestType = this.analyzeRequestType(prompt, context);
        const availableModels = await this.getAvailableModels();

        // Find best model for the request type
        const bestModel = this.findBestModelForRequest(requestType, availableModels);
        
        if (bestModel) {
            return bestModel;
        }

        // Fallback to first available model
        if (availableModels.length > 0) {
            return availableModels[0];
        }

        throw new Error('No AI models available');
    }

    private analyzeRequestType(prompt: string, context: any): string {
        const lowerPrompt = prompt.toLowerCase();

        // Analyze prompt to determine best model type
        if (lowerPrompt.includes('code') || lowerPrompt.includes('program') || lowerPrompt.includes('algorithm')) {
            return 'coding';
        } else if (lowerPrompt.includes('creative') || lowerPrompt.includes('write') || lowerPrompt.includes('story')) {
            return 'creative';
        } else if (lowerPrompt.includes('analyze') || lowerPrompt.includes('compare') || lowerPrompt.includes('research')) {
            return 'analysis';
        } else if (context.sensitive || lowerPrompt.includes('private') || lowerPrompt.includes('confidential')) {
            return 'privacy';
        } else {
            return 'general';
        }
    }

    private findBestModelForRequest(requestType: string, availableModels: any[]): any {
        const modelCapabilities: { [key: string]: string[] } = {
            'deepseek': ['coding', 'analysis', 'reasoning'],
            'openai': ['creative', 'conversational', 'analysis'],
            'local': ['privacy', 'general']
        };

        // Score each model based on capabilities and performance
        const scoredModels = availableModels.map(model => {
            let score = model.config.priority;
            
            // Boost score for matching capabilities
            const capabilities = modelCapabilities[model.name] || [];
            if (capabilities.includes(requestType)) {
                score += 5;
            }

            // Consider recent performance
            const performance = this.modelWeights.get(model.name) || 1;
            score *= performance;

            return { ...model, score };
        });

        // Return highest scoring model
        scoredModels.sort((a, b) => b.score - a.score);
        return scoredModels[0];
    }

    private async getAvailableModels(): Promise<any[]> {
        const available: any[] = [];

        for (const [name, adapter] of this.models) {
            const config = this.activeModels.find(m => m.name === name);
            if (config && await adapter.isAvailable()) {
                available.push({ name, adapter, config });
            }
        }

        return available;
    }

    private async fallbackProcess(prompt: string, context: any, startTime: number): Promise<ModelResponse> {
        this.logger.warn('Primary model failed, trying fallback...');

        const availableModels = await this.getAvailableModels();
        
        for (const model of availableModels) {
            try {
                const response = await model.adapter.process({
                    prompt,
                    context,
                    modelPreference: model.name
                });

                const latency = Date.now() - startTime;

                return {
                    text: response.text,
                    model: model.name,
                    tokens: response.tokensUsed,
                    latency,
                    confidence: response.confidence
                };

            } catch (error) {
                this.logger.error(`Fallback model ${model.name} also failed: ${error}`);
                continue;
            }
        }

        throw new Error('All AI models failed to process request');
    }

    private async updateModelPerformance(modelName: string, latency: number, confidence: number): Promise<void> {
        // Update model weights based on performance
        const currentWeight = this.modelWeights.get(modelName) || 1;
        
        // Calculate performance score (lower latency and higher confidence are better)
        const latencyScore = Math.max(0, 1 - (latency / 10000)); // Normalize latency
        const confidenceScore = confidence;
        const performanceScore = (latencyScore + confidenceScore) / 2;

        // Update weight with smoothing
        const newWeight = currentWeight * 0.9 + performanceScore * 0.1;
        this.modelWeights.set(modelName, newWeight);

        this.logger.debug(`Updated model ${modelName} weight to ${newWeight.toFixed(3)}`);
    }

    async getModelStatistics(): Promise<any> {
        const stats: any = {};

        for (const [name, weight] of this.modelWeights) {
            const config = this.activeModels.find(m => m.name === name);
            stats[name] = {
                weight: weight.toFixed(3),
                enabled: config?.enabled || false,
                priority: config?.priority || 0,
                capabilities: config?.capabilities || []
            };
        }

        return stats;
    }

    async testAllModels(prompt: string): Promise<any[]> {
        const results = [];

        for (const [name, adapter] of this.models) {
            try {
                const startTime = Date.now();
                const response = await adapter.process({ prompt });
                const latency = Date.now() - startTime;

                results.push({
                    model: name,
                    success: true,
                    response: response.text,
                    latency,
                    tokens: response.tokensUsed,
                    confidence: response.confidence
                });

            } catch (error) {
                results.push({
                    model: name,
                    success: false,
                    error: error.message
                });
            }
        }

        return results;
    }
}
