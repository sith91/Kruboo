export { AIEngineController } from './ai-engine/controller.js';
export { ConfigManager } from './utils/config.js';
export { Logger } from './utils/logger.js';

// Initialize core engine
export class CoreEngine {
  private aiEngine: AIEngineController;

  constructor() {
    this.aiEngine = new AIEngineController();
  }

  async initialize(): Promise<void> {
    console.log('🚀 AI Assistant Core Engine Initializing...');
    // Additional initialization logic will go here
  }

  getAIEngine(): AIEngineController {
    return this.aiEngine;
  }
}
