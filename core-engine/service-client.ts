import { Logger } from './utils/logger.js';
import { EventEmitter } from 'events';

export interface AIRequest {
    prompt: string;
    context?: Record<string, any>;
    modelPreference?: string;
}

export interface AIResponse {
    text: string;
    modelUsed: string;
    tokensUsed: number;
    confidence: number;
    processingTime: number;
}

export interface VoiceCommandRequest {
    audioData: ArrayBuffer;
    language?: string;
}

export interface VoiceCommandResponse {
    transcript: string;
    intent: string;
    confidence: number;
    entities: Record<string, any>;
    action: string;
    parameters: Record<string, any>;
}

export class ServiceClient {
    private logger: Logger;
    private eventEmitter: EventEmitter;
    private baseUrl: string;
    private isConnected: boolean = false;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.logger = new Logger('ServiceClient');
        this.eventEmitter = new EventEmitter();
        this.baseUrl = baseUrl;
    }

    async initialize(): Promise<void> {
        try {
            // Test connection
            const response = await fetch(`${this.baseUrl}/health`);
            if (!response.ok) {
                throw new Error('AI Gateway not available');
            }
            
            this.isConnected = true;
            this.logger.info('Connected to AI Gateway successfully');
        } catch (error) {
            this.logger.error('Failed to connect to AI Gateway:', error);
            throw error;
        }
    }

    // Unified AI Processing
    async processAI(request: AIRequest): Promise<AIResponse> {
        const response = await this._makeRequest('/v1/ai/process', {
            prompt: request.prompt,
            context: request.context || {},
            model_preference: request.modelPreference
        });

        return {
            text: response.text,
            modelUsed: response.model_used,
            tokensUsed: response.tokens_used,
            confidence: response.confidence,
            processingTime: response.processing_time
        };
    }

    // Voice Command Processing
    async processVoiceCommand(request: VoiceCommandRequest): Promise<VoiceCommandResponse> {
        const base64Audio = Buffer.from(request.audioData).toString('base64');
        
        const response = await this._makeRequest('/v1/voice/command', {
            audio_data: base64Audio,
            language: request.language || 'en-US'
        });

        return {
            transcript: response.transcript,
            intent: response.intent,
            confidence: response.confidence,
            entities: response.entities,
            action: response.action,
            parameters: response.parameters
        };
    }

    // Direct Speech-to-Text
    async transcribeAudio(audioData: ArrayBuffer, language: string = 'en-US'): Promise<any> {
        const base64Audio = Buffer.from(audioData).toString('base64');
        return await this._makeRequest('/v1/voice/transcribe', {
            audio_data: base64Audio,
            language: language
        });
    }

    // Text-to-Speech
    async synthesizeSpeech(text: string, voice: string = 'default'): Promise<ArrayBuffer> {
        const response = await this._makeRequest('/v1/voice/synthesize', {
            text: text,
            voice: voice
        });

        // Convert base64 back to ArrayBuffer
        return Buffer.from(response.audio_data, 'base64');
    }

    // System Commands
    async executeSystemCommand(command: string, parameters: Record<string, any> = {}): Promise<any> {
        return await this._makeRequest('/v1/system/execute', {
            command: command,
            parameters: parameters
        });
    }

    // Get available models
    async getAvailableModels(): Promise<any[]> {
        const response = await this._makeRequest('/v1/models', {}, 'GET');
        return response.models;
    }

    // Health check
    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }

    private async _makeRequest(endpoint: string, data: any, method: string = 'POST'): Promise<any> {
        if (!this.isConnected) {
            throw new Error('Service client not connected to AI Gateway');
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: method === 'POST' ? JSON.stringify(data) : undefined
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Service request failed: ${response.status} - ${errorText}`);
        }

        return await response.json();
    }

    // Event handling
    on(event: string, callback: (...args: any[]) => void): void {
        this.eventEmitter.on(event, callback);
    }

    off(event: string, callback: (...args: any[]) => void): void {
        this.eventEmitter.off(event, callback);
    }
}
