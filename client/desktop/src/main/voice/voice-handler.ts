import { app, ipcMain, BrowserWindow } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import { WebSocket } from 'ws';
import { Logger } from '@ai-assistant/core';
import { join } from 'path';

export class VoiceHandler {
    private logger: Logger;
    private voiceServiceProcess: ChildProcess | null = null;
    private voiceWebSocket: WebSocket | null = null;
    private isRecording: boolean = false;
    private audioStream: any = null;
    private mainWindow: BrowserWindow;

    constructor(mainWindow: BrowserWindow) {
        this.logger = new Logger('VoiceHandler');
        this.mainWindow = mainWindow;
        this.setupIPCHandlers();
    }

    private setupIPCHandlers(): void {
        // Voice training commands from renderer
        ipcMain.handle('voice-start-listening', async () => {
            return await this.startVoiceCapture();
        });

        ipcMain.handle('voice-stop-listening', async () => {
            return await this.stopVoiceCapture();
        });

        ipcMain.handle('voice-process-training-data', async (event, data) => {
            return await this.processTrainingData(data);
        });

        // Voice service management
        ipcMain.handle('voice-start-service', async () => {
            return await this.startVoiceService();
        });

        ipcMain.handle('voice-stop-service', async () => {
            return await this.stopVoiceService();
        });

        ipcMain.handle('voice-health-check', async () => {
            return await this.healthCheck();
        });
    }

    async startVoiceService(): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.info('Starting Python voice service...');

            const voiceServicePath = join(process.resourcesPath, 'services', 'voice-service', 'app.py');
            
            this.voiceServiceProcess = spawn('python', [voiceServicePath], {
                cwd: join(process.resourcesPath, 'services', 'voice-service'),
                stdio: ['pipe', 'pipe', 'pipe']
            });

            // Handle process output
            this.voiceServiceProcess.stdout?.on('data', (data) => {
                this.logger.info(`Voice Service: ${data.toString()}`);
            });

            this.voiceServiceProcess.stderr?.on('data', (data) => {
                this.logger.error(`Voice Service Error: ${data.toString()}`);
            });

            this.voiceServiceProcess.on('close', (code) => {
                this.logger.warn(`Voice service process exited with code ${code}`);
                this.voiceServiceProcess = null;
                this.voiceWebSocket = null;
            });

            // Wait for service to start
            await new Promise(resolve => setTimeout(resolve, 3000));

            // Connect to WebSocket
            await this.connectToVoiceWebSocket();

            this.logger.info('Python voice service started successfully');
            return { success: true };

        } catch (error) {
            this.logger.error('Failed to start voice service:', error);
            return { success: false, error: error.message };
        }
    }

    async stopVoiceService(): Promise<{ success: boolean; error?: string }> {
        try {
            if (this.voiceWebSocket) {
                this.voiceWebSocket.close();
                this.voiceWebSocket = null;
            }

            if (this.voiceServiceProcess) {
                this.voiceServiceProcess.kill();
                this.voiceServiceProcess = null;
            }

            this.logger.info('Voice service stopped');
            return { success: true };

        } catch (error) {
            this.logger.error('Failed to stop voice service:', error);
            return { success: false, error: error.message };
        }
    }

    private async connectToVoiceWebSocket(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.voiceWebSocket = new WebSocket('ws://localhost:8001/ws/command');

            this.voiceWebSocket.on('open', () => {
                this.logger.info('Connected to voice service WebSocket');
                resolve();
            });

            this.voiceWebSocket.on('message', (data) => {
                this.handleVoiceMessage(JSON.parse(data.toString()));
            });

            this.voiceWebSocket.on('error', (error) => {
                this.logger.error('Voice WebSocket error:', error);
                reject(error);
            });

            this.voiceWebSocket.on('close', () => {
                this.logger.info('Voice WebSocket disconnected');
                this.voiceWebSocket = null;
            });
        });
    }

    private handleVoiceMessage(message: any): void {
        this.logger.debug('Received voice message:', message);

        switch (message.type) {
            case 'transcription':
            case 'interim_transcription':
                this.mainWindow.webContents.send('voice-transcription', {
                    transcript: message.text,
                    confidence: message.confidence,
                    isFinal: message.is_final || false
                });
                break;

            case 'command_response':
                this.mainWindow.webContents.send('voice-command-response', {
                    transcript: message.transcript,
                    response: message.response,
                    audioResponse: message.audio_response,
                    intent: message.intent,
                    confidence: message.confidence
                });
                break;

            case 'error':
                this.mainWindow.webContents.send('voice-error', {
                    message: message.message
                });
                break;
        }
    }

    async startVoiceCapture(): Promise<{ success: boolean; error?: string }> {
        try {
            if (this.isRecording) {
                return { success: false, error: 'Already recording' };
            }

            if (!this.voiceWebSocket) {
                return { success: false, error: 'Voice service not connected' };
            }

            this.isRecording = true;
            
            // Initialize audio capture (platform-specific)
            await this.initializeAudioCapture();
            
            this.logger.info('Voice capture started');
            return { success: true };

        } catch (error) {
            this.logger.error('Failed to start voice capture:', error);
            return { success: false, error: error.message };
        }
    }

    async stopVoiceCapture(): Promise<{ success: boolean; error?: string }> {
        try {
            if (!this.isRecording) {
                return { success: true };
            }

            this.isRecording = false;
            await this.cleanupAudioCapture();
            
            this.logger.info('Voice capture stopped');
            return { success: true };

        } catch (error) {
            this.logger.error('Failed to stop voice capture:', error);
            return { success: false, error: error.message };
        }
    }

    private async initializeAudioCapture(): Promise<void> {
        // Platform-specific audio capture implementation
        // This is a simplified version - you'll need to implement based on your audio library
        
        try {
            // Example using microphone access (you might use node-microphone or similar)
            // For now, we'll set up a placeholder that sends audio chunks via WebSocket
            
            const { Mic } = await import('node-microphone'); // You'll need to install this
            
            this.audioStream = new Mic({
                rate: 16000,
                channels: 1,
                bitwidth: 16,
                device: 'default' // Platform-specific
            });

            const micStream = this.audioStream.startRecording();
            
            micStream.on('data', (audioChunk: Buffer) => {
                if (this.isRecording && this.voiceWebSocket) {
                    // Send audio chunk to voice service
                    this.voiceWebSocket.send(JSON.stringify({
                        type: 'audio_chunk',
                        audio_data: audioChunk.toString('base64'),
                        sample_rate: 16000,
                        language: 'en'
                    }));
                }
            });

            micStream.on('error', (error) => {
                this.logger.error('Audio capture error:', error);
                this.mainWindow.webContents.send('voice-error', {
                    message: 'Audio capture failed'
                });
            });

        } catch (error) {
            this.logger.error('Failed to initialize audio capture:', error);
            throw error;
        }
    }

    private async cleanupAudioCapture(): Promise<void> {
        if (this.audioStream) {
            this.audioStream.stopRecording();
            this.audioStream = null;
        }
    }

    async processTrainingData(trainingData: any): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.info('Processing voice training data:', trainingData);

            // Send training data to AI service for model improvement
            // This could be used to fine-tune voice recognition for the specific user
            
            // For now, just log and store the data
            const trainingResults = {
                timestamp: new Date().toISOString(),
                accuracy: trainingData.accuracy,
                totalPhrases: trainingData.data.length,
                successfulCaptures: trainingData.data.filter((d: any) => d.status === 'success').length,
                data: trainingData.data
            };

            // Store training results
            // You might want to save this to a file or database
            this.logger.info('Training results stored:', trainingResults);

            // Send to AI Gateway for processing
            await this.sendToAIGateway({
                type: 'voice_training_complete',
                data: trainingResults
            });

            return { success: true };

        } catch (error) {
            this.logger.error('Failed to process training data:', error);
            return { success: false, error: error.message };
        }
    }

    private async sendToAIGateway(data: any): Promise<void> {
        try {
            // Send training data to AI Gateway for analysis
            const response = await fetch('http://localhost:8000/v1/ai/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: `Process voice training data: ${JSON.stringify(data)}`,
                    context: {
                        source: 'voice_training',
                        type: 'training_analysis'
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`AI Gateway responded with ${response.status}`);
            }

            const result = await response.json();
            this.logger.info('AI Gateway processing complete:', result);

        } catch (error) {
            this.logger.error('Failed to send training data to AI Gateway:', error);
        }
    }

    async healthCheck(): Promise<{ 
        voiceService: boolean; 
        webSocket: boolean; 
        audioCapture: boolean;
        details: any;
    }> {
        const health = {
            voiceService: !!this.voiceServiceProcess,
            webSocket: !!(this.voiceWebSocket && this.voiceWebSocket.readyState === WebSocket.OPEN),
            audioCapture: this.isRecording,
            details: {}
        };

        // Check voice service HTTP health
        try {
            const response = await fetch('http://localhost:8001/health');
            if (response.ok) {
                health.details = await response.json();
            }
        } catch (error) {
            this.logger.warn('Voice service health check failed:', error);
        }

        return health;
    }
}
