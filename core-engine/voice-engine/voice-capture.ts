import { Logger } from '../utils/logger.js';
import { EventEmitter } from 'events';

export interface AudioChunk {
    data: ArrayBuffer;
    sampleRate: number;
    channels: number;
    timestamp: number;
    format: string;
}

export interface VoiceCaptureConfig {
    sampleRate: number;
    channels: number;
    bufferSize: number;
    silenceThreshold: number;
    maxRecordingTime: number;
}

export class VoiceCapture extends EventEmitter {
    private logger: Logger;
    private config: VoiceCaptureConfig;
    private mediaRecorder: MediaRecorder | null = null;
    private stream: MediaStream | null = null;
    private isRecording: boolean = false;
    private recordingStartTime: number = 0;

    constructor(config?: Partial<VoiceCaptureConfig>) {
        super();
        this.logger = new Logger('VoiceCapture');
        this.config = {
            sampleRate: 16000,
            channels: 1,
            bufferSize: 4096,
            silenceThreshold: 0.01,
            maxRecordingTime: 30000, // 30 seconds
            ...config
        };
    }

    async initialize(): Promise<void> {
        this.logger.info('Initializing voice capture...');
        
        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: this.config.channels,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            this.logger.info('Voice capture initialized successfully');
            
        } catch (error) {
            this.logger.error('Failed to initialize voice capture:', error);
            throw new Error(`Microphone access denied: ${error.message}`);
        }
    }

    async startRecording(): Promise<void> {
        if (!this.stream) {
            throw new Error('Voice capture not initialized');
        }

        if (this.isRecording) {
            this.logger.warn('Recording already in progress');
            return;
        }

        try {
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            
            // Create media recorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            });

            const chunks: Blob[] = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                    
                    // Emit chunk for real-time processing
                    this.emit('audio-chunk', {
                        data: event.data,
                        timestamp: Date.now()
                    });
                }
            };

            this.mediaRecorder.onstop = async () => {
                if (chunks.length > 0) {
                    const blob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
                    const arrayBuffer = await blob.arrayBuffer();
                    
                    this.emit('recording-complete', {
                        data: arrayBuffer,
                        format: 'webm',
                        sampleRate: this.config.sampleRate,
                        duration: Date.now() - this.recordingStartTime
                    });
                }
                
                this.isRecording = false;
                this.emit('recording-stopped');
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.emit('recording-started');
            
            this.logger.info('Voice recording started');

            // Auto-stop after max recording time
            setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, this.config.maxRecordingTime);

        } catch (error) {
            this.logger.error('Failed to start recording:', error);
            this.isRecording = false;
            throw error;
        }
    }

    async stopRecording(): Promise<void> {
        if (!this.mediaRecorder || !this.isRecording) {
            return;
        }

        try {
            this.mediaRecorder.stop();
            this.logger.info('Voice recording stopped');
        } catch (error) {
            this.logger.error('Error stopping recording:', error);
            this.isRecording = false;
            this.emit('recording-stopped');
        }
    }

    isRecordingActive(): boolean {
        return this.isRecording;
    }

    getRecordingTime(): number {
        return this.isRecording ? Date.now() - this.recordingStartTime : 0;
    }

    async destroy(): Promise<void> {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        this.isRecording = false;
        this.logger.info('Voice capture destroyed');
    }

    updateConfig(newConfig: Partial<VoiceCaptureConfig>): void {
        this.config = { ...this.config, ...newConfig };
        this.logger.info('Voice capture configuration updated');
    }
}
