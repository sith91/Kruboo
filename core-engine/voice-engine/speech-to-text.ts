import { Logger } from '../utils/logger.js';
import { ConfigManager } from '../utils/config.js';

export interface SpeechRecognitionResult {
    text: string;
    confidence: number;
    isFinal: boolean;
}

export class SpeechToTextEngine {
    private logger: Logger;
    private config: ConfigManager;
    private isListening: boolean = false;
    private recognition: any = null;

    constructor() {
        this.logger = new Logger('SpeechToText');
        this.config = ConfigManager.getInstance();
    }

    async initialize(): Promise<void> {
        this.logger.info('Initializing speech recognition engine');
        
        // Check if browser speech recognition is available
        if (this.isSpeechRecognitionAvailable()) {
            this.setupBrowserRecognition();
        } else {
            this.logger.warn('Browser speech recognition not available, using fallback');
            this.setupFallbackRecognition();
        }
    }

    async startListening(): Promise<void> {
        if (this.isListening) {
            this.logger.warn('Already listening');
            return;
        }

        this.isListening = true;
        this.logger.info('Starting speech recognition');

        if (this.recognition && typeof this.recognition.start === 'function') {
            try {
                this.recognition.start();
            } catch (error) {
                this.logger.error('Failed to start recognition:', error);
            }
        }
    }

    async stopListening(): Promise<void> {
        if (!this.isListening) {
            return;
        }

        this.isListening = false;
        this.logger.info('Stopping speech recognition');

        if (this.recognition && typeof this.recognition.stop === 'function') {
            try {
                this.recognition.stop();
            } catch (error) {
                this.logger.error('Failed to stop recognition:', error);
            }
        }
    }

    private isSpeechRecognitionAvailable(): boolean {
        return typeof window !== 'undefined' && (
            'webkitSpeechRecognition' in window ||
            'SpeechRecognition' in window
        );
    }

    private setupBrowserRecognition(): void {
        const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
        
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = this.config.getVoiceConfig().language;

            this.recognition.onstart = () => {
                this.logger.debug('Speech recognition started');
            };

            this.recognition.onresult = (event: any) => {
                this.handleRecognitionResult(event);
            };

            this.recognition.onerror = (event: any) => {
                this.logger.error('Speech recognition error:', event.error);
            };

            this.recognition.onend = () => {
                this.logger.debug('Speech recognition ended');
                this.isListening = false;
            };
        }
    }

    private setupFallbackRecognition(): void {
        // Implement fallback recognition method
        this.logger.info('Setting up fallback speech recognition');
    }

    private handleRecognitionResult(event: any): void {
        let finalText = '';
        let interimText = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalText += transcript;
            } else {
                interimText += transcript;
            }
        }

        // Emit results to main process
        if (finalText) {
            this.emitRecognitionResult({
                text: finalText.trim(),
                confidence: 0.9,
                isFinal: true
            });
        } else if (interimText) {
            this.emitRecognitionResult({
                text: interimText.trim(),
                confidence: 0.5,
                isFinal: false
            });
        }
    }

    private emitRecognitionResult(result: SpeechRecognitionResult): void {
        // This would emit to the main process via IPC
        console.log('Speech recognition result:', result);
        
        // In Electron, we'd use ipcRenderer to send to main process
        if (typeof window !== 'undefined' && (window as any).electronAPI) {
            (window as any).electronAPI.send('voice:recognition-result', result);
        }
    }
}
