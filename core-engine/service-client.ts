import { Logger } from './utils/logger.js';
import { EventEmitter } from 'events';

export interface AIRequest {
    prompt: string;
    context?: Record<string, any>;
    modelPreference?: string;
    maxTokens?: number;
    temperature?: number;
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

export interface SystemCommandRequest {
    command: string;
    parameters?: Record<string, any>;
}

export interface SystemCommandResponse {
    success: boolean;
    result: any;
    message: string;
}

export interface ServiceStatus {
    healthy: boolean;
    providers: any[];
    connected: boolean;
    timestamp: string;
}

export class ServiceClient {
    private logger: Logger;
    private eventEmitter: EventEmitter;
    private baseUrl: string;
    private isConnected: boolean = false;
    private retryCount: number = 0;
    private maxRetries: number = 3;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.logger = new Logger('ServiceClient');
        this.eventEmitter = new EventEmitter();
        this.baseUrl = baseUrl;
    }

    async initialize(): Promise<void> {
        try {
            this.logger.info(`Connecting to AI Gateway at ${this.baseUrl}...`);
            
            // Test connection with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(`${this.baseUrl}/health`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`AI Gateway responded with status: ${response.status}`);
            }
            
            const health = await response.json();
            this.isConnected = true;
            this.retryCount = 0;
            
            this.logger.info('Connected to AI Gateway successfully');
            this.logger.info(`Available providers: ${Object.keys(health.providers).join(', ')}`);
            
            this.eventEmitter.emit('connected');
            
        } catch (error) {
            this.logger.error('Failed to connect to AI Gateway:', error);
            
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                this.logger.info(`Retrying connection in 5 seconds... (${this.retryCount}/${this.maxRetries})`);
                
                setTimeout(() => this.initialize(), 5000);
            } else {
                throw new Error(`Unable to connect to AI Gateway after ${this.maxRetries} attempts`);
            }
        }
    }

    // Unified AI Processing
    async processAI(request: AIRequest): Promise<AIResponse> {
        const response = await this.makeRequest('/v1/ai/process', {
            prompt: request.prompt,
            context: request.context || {},
            model_preference: request.modelPreference,
            max_tokens: request.maxTokens || 1000,
            temperature: request.temperature || 0.7
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
        const base64Audio = this.arrayBufferToBase64(request.audioData);
        
        const response = await this.makeRequest('/v1/voice/command', {
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
        const base64Audio = this.arrayBufferToBase64(audioData);
        return await this.makeRequest('/v1/voice/transcribe', {
            audio_data: base64Audio,
            language: language
        });
    }

    // Text-to-Speech
    async synthesizeSpeech(text: string, voice: string = 'default'): Promise<ArrayBuffer> {
        const response = await this.makeRequest('/v1/voice/synthesize', {
            text: text,
            voice: voice
        });

        return this.base64ToArrayBuffer(response.audio_data);
    }

    // System Commands
    async executeSystemCommand(command: string, parameters: Record<string, any> = {}): Promise<SystemCommandResponse> {
        const response = await this.makeRequest('/v1/system/execute', {
            command: command,
            parameters: parameters
        });

        return {
            success: response.success,
            result: response.result,
            message: response.message
        };
    }

    // Get available models
    async getAvailableModels(): Promise<any[]> {
        const response = await this.makeRequest('/v1/models', {}, 'GET');
        return response.models;
    }

    // Health check
    async healthCheck(): Promise<ServiceStatus> {
        try {
            const response = await this.makeRequest('/health', {}, 'GET');
            return {
                healthy: response.status === 'healthy',
                providers: response.providers || {},
                connected: true,
                timestamp: response.timestamp
            };
        } catch (error) {
            return {
                healthy: false,
                providers: [],
                connected: false,
                timestamp: new Date().toISOString()
            };
        }
    }

    // Provider-specific health check
    async getProvidersHealth(): Promise<any> {
        return await this.makeRequest('/health/providers', {}, 'GET');
    }

    private async makeRequest(endpoint: string, data: any, method: string = 'POST'): Promise<any> {
        if (!this.isConnected) {
            throw new Error('Service client not connected to AI Gateway');
        }

        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const response = await fetch(url, {
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

        } catch (error) {
            this.logger.error(`Service request to ${endpoint} failed:`, error);
            
            // Check if it's a connection error
            if (error.message.includes('fetch') || error.message.includes('network')) {
                this.isConnected = false;
                this.eventEmitter.emit('disconnected');
            }
            
            throw error;
        }
    }

    private arrayBufferToBase64(buffer: ArrayBuffer): string {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    private base64ToArrayBuffer(base64: string): ArrayBuffer {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }

    // Connection status
    getConnectionStatus(): boolean {
        return this.isConnected;
    }

    // Event handling
    on(event: string, callback: (...args: any[]) => void): void {
        this.eventEmitter.on(event, callback);
    }

    off(event: string, callback: (...args: any[]) => void): void {
        this.eventEmitter.off(event, callback);
    }

    // Reconnect manually
    async reconnect(): Promise<void> {
        this.logger.info('Manual reconnection requested');
        await this.initialize();
    }
}
