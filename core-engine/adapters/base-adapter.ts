import { AIRequest, AIResponse } from '../controller.js';

export abstract class BaseAIAdapter {
  protected apiKey?: string;
  protected baseURL?: string;

  constructor(apiKey?: string, baseURL?: string) {
    this.apiKey = apiKey;
    this.baseURL = baseURL;
  }

  abstract process(request: AIRequest): Promise<AIResponse>;
  abstract isAvailable(): Promise<boolean>;

  protected validateConfig(): boolean {
    return !!this.apiKey;
  }
}
