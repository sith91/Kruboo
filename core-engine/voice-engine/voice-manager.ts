import { Logger } from '../utils/logger.js';
import { EventEmitter } from 'events';
import { VoiceCapture, AudioChunk } from './voice-capture.js';
import { ServiceClient } from '../service-client.js';

export interface VoiceManagerConfig {
    autoStart: boolean;
    wakeWordEnabled: boolean;
    continuousListening: boolean;
    language: string;
}

export class VoiceManager extends EventEmitter {
    private logger: Logger;
    private voiceCapture: VoiceCapture;
    private serviceClient: ServiceClient;
    private config: VoiceManagerConfig;
    private isListening: boolean = false;

    constructor(serviceClient: ServiceClient, config?: Partial<VoiceManagerConfig>) {
        super();
        this.logger = new Logger('VoiceManager');
        this.serviceClient = serviceClient;
        this.voiceCapture = new VoiceCapture();
        this.config = {
            autoStart: false,
            wakeWordEnabled: true,
            continuousListening: false,
            language: 'en-US',
            ...config
        };

        this.setupEventListeners();
    }

    async initialize(): Promise<void> {
        this.logger.info('Initializing Voice Manager...');
        
        try {
            await this.voiceCapture.initialize();
            
            if (this.config.autoStart) {
                await this.startListening();
            }
            
            this.logger.info('Voice Manager initialized successfully');
        } catch (error) {
            this.logger.error('Failed to initialize Voice Manager:', error);
            throw error;
        }
    }

    async startListening(): Promise<void> {
        if (this.isListening) {
            return;
        }

        try {
            this.isListening = true;
            this.emit('listening-started');
            this.logger.info('Voice listening started');
            
        } catch (error) {
            this.logger.error('Failed to start listening:', error);
            this.isListening = false;
            throw error;
        }
    }

    async stopListening(): Promise<void> {
        if (!this.isListening) {
            return;
        }

        try {
            await this.voiceCapture.stopRecording();
            this.isListening = false;
            this.emit('listening-stopped');
            this.logger.info('Voice listening stopped');
        } catch (error) {
            this.logger.error('Error stopping listening:', error);
        }
    }

    async startRecording(): Promise<void> {
        if (!this.isListening) {
            throw new Error('Voice listening not active');
        }

        try {
            await this.voiceCapture.startRecording();
            this.emit('recording-started');
        } catch (error) {
            this.logger.error('Failed to start recording:', error);
            throw error;
        }
    }

    async stopRecording(): Promise<void> {
        try {
            await this.voiceCapture.stopRecording();
        } catch (error) {
            this.logger.error('Error stopping recording:', error);
        }
    }

    async processAudio(audioData: ArrayBuffer): Promise<any> {
        try {
            // Send audio to Python service for processing
            const result = await this.serviceClient.processVoiceCommand({
                audioData: audioData,
                language: this.config.language
            });

            this.emit('voice-processed', result);
            return result;

        } catch (error) {
            this.logger.error('Audio processing failed:', error);
            this.emit('processing-error', error);
            throw error;
        }
    }

    async textToSpeech(text: string, voice: string = 'default'): Promise<ArrayBuffer> {
        try {
            const audioData = await this.serviceClient.synthesizeSpeech(text, voice);
            this.emit('speech-synthesized', { text, voice });
            return audioData;
        } catch (error) {
            this.logger.error('Text-to-speech failed:', error);
            throw error;
        }
    }

    private setupEventListeners(): void {
        // Voice capture events
        this.voiceCapture.on('recording-started', () => {
            this.emit('recording-started');
        });

        this.voiceCapture.on('recording-stopped', () => {
            this.emit('recording-stopped');
        });

        this.voiceCapture.on('recording-complete', async (audioData: any) => {
            this.emit('recording-complete', audioData);
            
            // Auto-process recording when complete
            if (this.config.continuousListening) {
                try {
                    const result = await this.processAudio(audioData.data);
                    this.emit('voice-command', result);
                } catch (error) {
                    this.logger.error('Auto-processing failed:', error);
                }
            }
        });

        this.voiceCapture.on('audio-chunk', (chunk: any) => {
            this.emit('audio-chunk', chunk);
        });
    }

    updateConfig(newConfig: Partial<VoiceManagerConfig>): void {
        this.config = { ...this.config, ...newConfig };
        this.logger.info('Voice manager configuration updated');
    }

    getConfig(): VoiceManagerConfig {
        return { ...this.config };
    }

    isListeningActive(): boolean {
        return this.isListening;
    }

    async destroy(): Promise<void> {
        await this.stopListening();
        await this.voiceCapture.destroy();
        this.logger.info('Voice Manager destroyed');
    }
}
