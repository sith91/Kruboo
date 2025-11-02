import { Logger } from '../utils/logger.js';
import { ConfigManager } from '../utils/config.js';
import { ModelSelector } from './model-selector.js';
import { ModelManager } from './model-manager.js';

export interface AIRequest {
  prompt: string;
  context?: any;
  modelPreference?: string;
}

export interface AIResponse {
  text: string;
  modelUsed: string;
  tokensUsed: number;
  confidence: number;
}

export class AIEngineController {
  private logger: Logger;
  private config: ConfigManager;
  private modelSelector: ModelSelector;

  constructor() {
    this.logger = new Logger('AIEngine');
    this.config = ConfigManager.getInstance();
    this.modelSelector = new ModelSelector();
  }

  async processRequest(request: AIRequest): Promise<AIResponse> {
    this.logger.info(`Processing request: ${request.prompt.substring(0, 50)}...`);

    try {
      const model = this.modelSelector.selectModel(request);
      const response = await model.process(request);
      
      this.logger.debug(`Model ${response.modelUsed} used with confidence ${response.confidence}`);
      return response;
    } catch (error) {
      this.logger.error(`AI processing failed: ${error}`);
      throw new Error(`AI processing failed: ${error}`);
    }
  }

  async analyzeIntent(text: string): Promise<any> {
    this.logger.info(`Analyzing intent for: ${text}`);
    
    // Basic intent analysis - will be expanded with NLP
    const intent = {
      action: this.extractAction(text),
      entities: this.extractEntities(text),
      confidence: 0.8
    };

    return intent;
  }

  private extractAction(text: string): string {
    const lowerText = text.toLowerCase();
    
    if (lowerText.includes('open') || lowerText.includes('launch')) return 'open_app';
    if (lowerText.includes('search') || lowerText.includes('find')) return 'search';
    if (lowerText.includes('what') || lowerText.includes('how')) return 'query';
    if (lowerText.includes('remind') || lowerText.includes('schedule')) return 'reminder';
    
    return 'general';
  }

  private extractEntities(text: string): string[] {
    // Simple entity extraction - will be replaced with proper NLP
    const entities: string[] = [];
    const words = text.toLowerCase().split(' ');
    
    const stopWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'];
    entities.push(...words.filter(word => !stopWords.includes(word) && word.length > 2));
    
    return entities;
  }
}

export class AIEngineController {
    private modelManager: ModelManager;

    constructor() {
        this.logger = new Logger('AIEngine');
        this.config = ConfigManager.getInstance();
        this.modelManager = new ModelManager();
    }

    async processRequest(request: AIRequest): Promise<AIResponse> {
        this.logger.info(`Processing request: ${request.prompt.substring(0, 50)}...`);

        try {
            const modelResponse = await this.modelManager.processRequest(request.prompt, request.context);
            
            return {
                text: modelResponse.text,
                modelUsed: modelResponse.model,
                tokensUsed: modelResponse.tokens,
                confidence: modelResponse.confidence
            };
        } catch (error) {
            this.logger.error(`AI processing failed: ${error}`);
            throw new Error(`AI processing failed: ${error}`);
        }
    }

    // Add method to get model statistics
    async getModelStats(): Promise<any> {
        return await this.modelManager.getModelStatistics();
    }

    // Add method to test all models
    async testModels(prompt: string): Promise<any[]> {
        return await this.modelManager.testAllModels(prompt);
    }
}
