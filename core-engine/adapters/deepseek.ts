import { BaseAIAdapter } from './base-adapter.js';
import { AIRequest, AIResponse } from '../controller.js';
import { ConfigManager } from '../../utils/config.js';
import { Logger } from '../../utils/logger.js';

export class DeepSeekAdapter extends BaseAIAdapter {
    private logger: Logger;
    private config: ConfigManager;

    constructor() {
        const config = ConfigManager.getInstance().getAIConfig().deepseek;
        super(config.apiKey, config.baseURL);
        this.logger = new Logger('DeepSeekAdapter');
        this.config = ConfigManager.getInstance();
    }

    async process(request: AIRequest): Promise<AIResponse> {
        if (!this.validateConfig()) {
            throw new Error('DeepSeek API key not configured');
        }

        const startTime = Date.now();
        
        try {
            const response = await this.makeAPICall(request);
            const latency = Date.now() - startTime;

            return {
                text: response.choices[0]?.message?.content || 'No response generated',
                modelUsed: response.model,
                tokensUsed: response.usage?.total_tokens || 0,
                confidence: 0.95, // DeepSeek typically has high confidence for coding
                latency: latency
            };
        } catch (error) {
            this.logger.error(`DeepSeek API call failed: ${error}`);
            throw error;
        }
    }

    private async makeAPICall(request: AIRequest): Promise<any> {
        const apiKey = this.config.getAIConfig().deepseek.apiKey;
        const baseURL = this.config.getAIConfig().deepseek.baseURL || 'https://api.deepseek.com/v1';

        const response = await fetch(`${baseURL}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: 'deepseek-chat',
                messages: [
                    {
                        role: 'system',
                        content: this.getSystemPrompt(request.context)
                    },
                    {
                        role: 'user',
                        content: request.prompt
                    }
                ],
                max_tokens: 4000,
                temperature: 0.7,
                stream: false
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`DeepSeek API error: ${errorData.error?.message || response.statusText}`);
        }

        return await response.json();
    }

    private getSystemPrompt(context: any): string {
        const basePrompt = `You are DeepSeek AI, specialized in reasoning, coding, and technical tasks. 
You have system integration capabilities for:
- Code analysis and generation
- Technical problem solving
- Complex reasoning tasks
- System automation

Provide detailed, technical responses when appropriate.`;

        if (context?.intent === 'coding') {
            return basePrompt + '\n\nFocus on providing clean, efficient code solutions.';
        }

        return basePrompt;
    }

    async isAvailable(): Promise<boolean> {
        if (!this.validateConfig()) {
            return false;
        }

        try {
            const response = await fetch('https://api.deepseek.com/v1/models', {
                headers: {
                    'Authorization': `Bearer ${this.config.getAIConfig().deepseek.apiKey}`
                }
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
}
