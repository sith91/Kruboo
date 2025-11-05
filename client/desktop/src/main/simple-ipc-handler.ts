import { ipcMain } from 'electron';
import { ServiceClient } from '@ai-assistant/core';
import { Logger } from '@ai-assistant/core';

export class SimpleIPCHandler {
    private serviceClient: ServiceClient;
    private logger: Logger;

    constructor(serviceClient: ServiceClient) {
        this.serviceClient = serviceClient;
        this.logger = new Logger('SimpleIPCHandler');
    }

    setupHandlers(): void {
        this.logger.info('Setting up simplified IPC handlers');

        // Unified AI processing
        ipcMain.handle('ai:process', async (event, prompt: string, context: any = {}) => {
            try {
                const response = await this.serviceClient.processAI({ prompt, context });
                return { success: true, data: response };
            } catch (error) {
                this.logger.error('AI processing failed:', error);
                return { success: false, error: error.message };
            }
        });

        // Voice command processing
        ipcMain.handle('voice:process', async (event, audioData: ArrayBuffer, language: string = 'en-US') => {
            try {
                const response = await this.serviceClient.processVoiceCommand({ 
                    audioData, 
                    language 
                });
                return { success: true, data: response };
            } catch (error) {
                this.logger.error('Voice processing failed:', error);
                return { success: false, error: error.message };
            }
        });

        // Text-to-speech
        ipcMain.handle('voice:synthesize', async (event, text: string, voice: string = 'default') => {
            try {
                const audioBuffer = await this.serviceClient.synthesizeSpeech(text, voice);
                return { success: true, data: audioBuffer.toString('base64') };
            } catch (error) {
                this.logger.error('TTS failed:', error);
                return { success: false, error: error.message };
            }
        });

        // System commands
        ipcMain.handle('system:execute', async (event, command: string, parameters: any = {}) => {
            try {
                const response = await this.serviceClient.executeSystemCommand(command, parameters);
                return { success: true, data: response };
            } catch (error) {
                this.logger.error('System command failed:', error);
                return { success: false, error: error.message };
            }
        });

        // Service status
        ipcMain.handle('services:status', async () => {
            try {
                const isHealthy = await this.serviceClient.healthCheck();
                const models = await this.serviceClient.getAvailableModels();
                return { 
                    success: true, 
                    data: { 
                        healthy: isHealthy, 
                        models,
                        connected: true 
                    } 
                };
            } catch (error) {
                return { 
                    success: false, 
                    data: { 
                        healthy: false, 
                        models: [], 
                        connected: false 
                    } 
                };
            }
        });

        this.logger.info('Simplified IPC handlers setup completed');
    }
}
