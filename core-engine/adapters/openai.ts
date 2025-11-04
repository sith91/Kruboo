import { BaseAIAdapter } from './base-adapter.js';
import { AIRequest, AIResponse } from '../controller.js';
import { ConfigManager } from '../../utils/config.js';
import { Logger } from '../../utils/logger.js';

export class OpenAIAdapter extends BaseAIAdapter {
    private logger: Logger;
    private config: ConfigManager;

    constructor() {
        const config = ConfigManager.getInstance().getAIConfig().openai;
        super(config.apiKey, config.baseURL);
        this.logger = new Logger('OpenAIAdapter');
        this.config = ConfigManager.getInstance();
    }

    async process(request: AIRequest): Promise<AIResponse> {
        if (!this.validateConfig()) {
            throw new Error('OpenAI API key not configured');
        }

        const startTime = Date.now();
        
        try {
            const response = await this.makeAPICall(request);
            const latency = Date.now() - startTime;

            return {
                text: response.choices[0]?.message?.content || 'No response generated',
                modelUsed: response.model,
                tokensUsed: response.usage?.total_tokens || 0,
                confidence: 0.9,
                latency: latency
            };
        } catch (error) {
            this.logger.error(`OpenAI API call failed: ${error}`);
            throw error;
        }
    }

    private async makeAPICall(request: AIRequest): Promise<any> {
        const apiKey = this.config.getAIConfig().openai.apiKey;
        const baseURL = this.config.getAIConfig().openai.baseURL || 'https://api.openai.com/v1';

        const response = await fetch(`${baseURL}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: 'gpt-4',
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
                max_tokens: 2000,
                temperature: 0.7,
                top_p: 0.9
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`OpenAI API error: ${errorData.error?.message || response.statusText}`);
        }

        return await response.json();
    }

    private getSystemPrompt(context: any): string {
        const basePrompt = `You are a helpful AI assistant. You have access to various system capabilities including:
- Application control (open, close apps)
- File system operations
- Web search and research
- Task management
- Communication tools

Respond concisely and helpfully.`;

        if (context?.source === 'voice') {
            return basePrompt + '\n\nThis is a voice command, so keep responses brief and actionable.';
        }

        return basePrompt;
    }

    async isAvailable(): Promise<boolean> {
        if (!this.validateConfig()) {
            return false;
        }

        try {
            // Test API with a simple request
            const testResponse = await fetch('https://api.openai.com/v1/models', {
                headers: {
                    'Authorization': `Bearer ${this.config.getAIConfig().openai.apiKey}`
                }
            });
            return testResponse.ok;
        } catch (error) {
            return false;
        }
    }
}
