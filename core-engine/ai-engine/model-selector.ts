import { AIRequest } from './controller.js';
import { OpenAIAdapter } from './adapters/openai.js';
import { DeepSeekAdapter } from './adapters/deepseek.js';

export interface AIModel {
  process(request: AIRequest): Promise<any>;
  isAvailable(): Promise<boolean>;
}

export class ModelSelector {
  private models: Map<string, AIModel> = new Map();

  constructor() {
    this.models.set('openai', new OpenAIAdapter());
    this.models.set('deepseek', new DeepSeekAdapter());
  }

  async selectModel(request: AIRequest): Promise<AIModel> {
    // Simple model selection logic - will be enhanced with cost, performance, capability factors
    for (const [name, model] of this.models) {
      if (await model.isAvailable()) {
        return model;
      }
    }
    
    throw new Error('No AI models available');
  }
}
