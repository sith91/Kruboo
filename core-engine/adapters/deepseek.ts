import { BaseAIAdapter } from './base-adapter.js';
import { AIRequest, AIResponse } from '../controller.js';
import { ConfigManager } from '../../utils/config.js';

export class DeepSeekAdapter extends BaseAIAdapter {
  private config: ConfigManager;

  constructor() {
    const config = ConfigManager.getInstance().getAIConfig().deepseek;
    super(config.apiKey, config.baseURL);
    this.config = ConfigManager.getInstance();
  }

  async process(request: AIRequest): Promise<AIResponse> {
    if (!this.validateConfig()) {
      throw new Error('DeepSeek API key not configured');
    }

    // TODO: Implement actual DeepSeek API integration
    // For now, return mock response
    return {
      text: `This is a mock response from DeepSeek for: ${request.prompt}`,
      modelUsed: 'deepseek-chat',
      tokensUsed: 100,
      confidence: 0.9
    };
  }

  async isAvailable(): Promise<boolean> {
    return this.validateConfig();
  }
}
