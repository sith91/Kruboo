import { Logger } from '../utils/logger.js';
import { ConfigManager } from '../utils/config.js';

export interface VoiceCommand {
    text: string;
    intent: string;
    confidence: number;
    entities: { [key: string]: string };
    action: string;
    parameters: any;
}

export class AdvancedSpeechRecognition {
    private logger: Logger;
    private config: ConfigManager;
    private recognition: any;
    private isListening: boolean = false;
    private commands: Map<string, Function> = new Map();
    private wakeWordDetector: any;

    constructor() {
        this.logger = new Logger('AdvancedSpeechRecognition');
        this.config = ConfigManager.getInstance();
        this.initializeCommands();
    }

    async initialize(): Promise<void> {
        this.logger.info('Initializing advanced speech recognition');
        
        if (this.isBrowserSpeechAvailable()) {
            await this.initializeBrowserRecognition();
        } else {
            await this.initializeExternalRecognition();
        }

        this.initializeWakeWordDetection();
    }

    private initializeCommands(): void {
        // System commands
        this.commands.set('open_app', this.handleOpenApp.bind(this));
        this.commands.set('close_app', this.handleCloseApp.bind(this));
        this.commands.set('search_web', this.handleWebSearch.bind(this));
        this.commands.set('system_info', this.handleSystemInfo.bind(this));
        this.commands.set('file_operation', this.handleFileOperation.bind(this));
        
        // Productivity commands
        this.commands.set('create_reminder', this.handleCreateReminder.bind(this));
        this.commands.set('schedule_meeting', this.handleScheduleMeeting.bind(this));
        this.commands.set('send_message', this.handleSendMessage.bind(this));
        
        // Media commands
        this.commands.set('play_media', this.handlePlayMedia.bind(this));
        this.commands.set('control_playback', this.handleControlPlayback.bind(this));
    }

    private async initializeBrowserRecognition(): Promise<void> {
        const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
        
        if (!SpeechRecognition) {
            throw new Error('Browser speech recognition not available');
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = this.config.getVoiceConfig().language;

        // Configure for better accuracy
        this.recognition.maxAlternatives = 3;
        
        if (this.config.getVoiceConfig().noiseCancellation) {
            this.recognition.noiseSuppression = true;
            this.recognition.echoCancellation = true;
        }

        this.setupRecognitionEvents();
    }

    private async initializeExternalRecognition(): Promise<void> {
        // Integration with external speech recognition services
        // This could be Azure Speech Services, Google Cloud Speech, etc.
        this.logger.info('Using external speech recognition service');
        
        // Placeholder for external service integration
        this.recognition = {
            start: () => console.log('External recognition started'),
            stop: () => console.log('External recognition stopped')
        };
    }

    private initializeWakeWordDetection(): void {
        const wakeWord = this.config.getVoiceConfig().wakeWord;
        this.logger.info(`Wake word detection initialized: "${wakeWord}"`);
        
        // In a real implementation, this would use a proper wake word detection library
        // like Porcupine or Snowboy
        this.wakeWordDetector = {
            start: () => {
                this.logger.debug('Wake word detection active');
            },
            stop: () => {
                this.logger.debug('Wake word detection stopped');
            }
        };
    }

    private setupRecognitionEvents(): void {
        this.recognition.onstart = () => {
            this.logger.info('Speech recognition started');
            this.isListening = true;
        };

        this.recognition.onend = () => {
            this.logger.info('Speech recognition ended');
            this.isListening = false;
        };

        this.recognition.onerror = (event: any) => {
            this.logger.error(`Speech recognition error: ${event.error}`);
            this.isListening = false;
        };

        this.recognition.onresult = (event: any) => {
            this.handleRecognitionResult(event);
        };
    }

    private handleRecognitionResult(event: any): void {
        const results = event.results;
        const latestResult = results[results.length - 1];
        const alternatives = latestResult[0].transcript;

        this.logger.debug(`Speech recognized: "${alternatives}"`);

        if (latestResult.isFinal) {
            this.processFinalTranscript(alternatives);
        } else {
            this.processInterimTranscript(alternatives);
        }
    }

    private async processFinalTranscript(transcript: string): Promise<void> {
        this.logger.info(`Final transcript: ${transcript}`);

        try {
            const command = await this.analyzeCommand(transcript);
            
            if (command.confidence > 0.7) {
                await this.executeCommand(command);
            } else {
                this.logger.warn(`Low confidence command: ${command.intent} (${command.confidence})`);
                // Fallback to AI processing
                await this.fallbackToAI(transcript);
            }

        } catch (error) {
            this.logger.error(`Command processing failed: ${error}`);
            await this.fallbackToAI(transcript);
        }
    }

    private processInterimTranscript(transcript: string): void {
        // Emit interim results for real-time feedback
        this.emitRecognitionEvent({
            type: 'interim',
            transcript: transcript,
            isFinal: false
        });
    }

    private async analyzeCommand(transcript: string): Promise<VoiceCommand> {
        const lowerTranscript = transcript.toLowerCase().trim();
        
        // Intent recognition patterns
        const patterns = [
            {
                intent: 'open_app',
                patterns: [/open (.+)/, /launch (.+)/, /start (.+)/],
                action: 'open_app',
                extractor: (match: RegExpMatchArray) => ({ appName: match[1] })
            },
            {
                intent: 'search_web',
                patterns: [/search for (.+)/, /find (.+)/, /look up (.+)/],
                action: 'search_web',
                extractor: (match: RegExpMatchArray) => ({ query: match[1] })
            },
            {
                intent: 'system_info',
                patterns: [/system info/, /what's running/, /show processes/],
                action: 'system_info',
                extractor: () => ({})
            },
            {
                intent: 'create_reminder',
                patterns: [/remind me to (.+)/, /set reminder for (.+)/],
                action: 'create_reminder',
                extractor: (match: RegExpMatchArray) => ({ task: match[1] })
            },
            {
                intent: 'play_media',
                patterns: [/play (.+)/, /start music/, /play song/],
                action: 'play_media',
                extractor: (match: RegExpMatchArray) => ({ media: match[1] || 'music' })
            }
        ];

        for (const pattern of patterns) {
            for (const regex of pattern.patterns) {
                const match = lowerTranscript.match(regex);
                if (match) {
                    return {
                        text: transcript,
                        intent: pattern.intent,
                        confidence: this.calculateConfidence(transcript, match),
                        entities: pattern.extractor(match),
                        action: pattern.action,
                        parameters: pattern.extractor(match)
                    };
                }
            }
        }

        // No pattern matched, use AI for intent analysis
        return await this.analyzeWithAI(transcript);
    }

    private async analyzeWithAI(transcript: string): Promise<VoiceCommand> {
        // Use AI to analyze complex or ambiguous commands
        const aiResponse = await this.sendToAIForAnalysis(transcript);
        
        return {
            text: transcript,
            intent: aiResponse.intent || 'unknown',
            confidence: aiResponse.confidence || 0.5,
            entities: aiResponse.entities || {},
            action: aiResponse.action || 'ai_process',
            parameters: aiResponse.parameters || {}
        };
    }

    private async sendToAIForAnalysis(transcript: string): Promise<any> {
        // This would integrate with the AI engine
        const prompt = `Analyze this voice command and return JSON with:
- intent: the main intent (open_app, search_web, system_info, etc.)
- confidence: confidence score 0-1
- entities: extracted entities like app names, queries, etc.
- action: specific action to take
- parameters: any parameters needed

Command: "${transcript}"`;

        // Placeholder - would integrate with actual AI
        return {
            intent: 'ai_process',
            confidence: 0.8,
            action: 'ai_process',
            parameters: { transcript }
        };
    }

    private calculateConfidence(transcript: string, match: RegExpMatchArray): number {
        // Simple confidence calculation based on match quality
        const baseConfidence = 0.8;
        const lengthBonus = Math.min(transcript.length / 100, 0.2);
        return Math.min(baseConfidence + lengthBonus, 0.95);
    }

    private async executeCommand(command: VoiceCommand): Promise<void> {
        this.logger.info(`Executing command: ${command.intent}`, command.parameters);

        const commandHandler = this.commands.get(command.action);
        if (commandHandler) {
            await commandHandler(command.parameters);
        } else {
            this.logger.warn(`No handler for command: ${command.action}`);
            await this.fallbackToAI(command.text);
        }

        this.emitRecognitionEvent({
            type: 'command_executed',
            command: command.intent,
            parameters: command.parameters,
            confidence: command.confidence
        });
    }

    private async fallbackToAI(transcript: string): Promise<void> {
        this.logger.info(`Falling back to AI processing for: ${transcript}`);
        
        this.emitRecognitionEvent({
            type: 'ai_fallback',
            transcript: transcript
        });

        // This would send to the main AI engine for processing
    }

    // Command handlers
    private async handleOpenApp(params: any): Promise<void> {
        const { appName } = params;
        this.logger.info(`Opening application: ${appName}`);
        
        // This would integrate with system application launcher
        await window.electronAPI.openApplication(appName);
    }

    private async handleWebSearch(params: any): Promise<void> {
        const { query } = params;
        this.logger.info(`Searching web for: ${query}`);
        
        // This would open browser or perform search
        await window.electronAPI.processAIRequest({
            type: 'web_search',
            query: query
        });
    }

    private async handleSystemInfo(params: any): Promise<void> {
        this.logger.info('Getting system information');
        
        const systemInfo = await window.electronAPI.getSystemInfo();
        this.emitRecognitionEvent({
            type: 'system_info',
            data: systemInfo
        });
    }

    private async handleCreateReminder(params: any): Promise<void> {
        const { task } = params;
        this.logger.info(`Creating reminder: ${task}`);
        
        await window.electronAPI.processAIRequest({
            type: 'create_reminder',
            task: task
        });
    }

    private async handlePlayMedia(params: any): Promise<void> {
        const { media } = params;
        this.logger.info(`Playing media: ${media}`);
        
        await window.electronAPI.processAIRequest({
            type: 'play_media',
            media: media
        });
    }

    private emitRecognitionEvent(event: any): void {
        // Emit event to main process or other components
        if (typeof window !== 'undefined' && (window as any).electronAPI) {
            (window as any).electronAPI.send('voice:recognition-event', event);
        }
    }

    async startListening(): Promise<void> {
        if (this.isListening) {
            return;
        }

        try {
            if (this.recognition && typeof this.recognition.start === 'function') {
                this.recognition.start();
            }
            
            if (this.wakeWordDetector) {
                this.wakeWordDetector.start();
            }

            this.isListening = true;
        } catch (error) {
            this.logger.error('Failed to start listening:', error);
            throw error;
        }
    }

    async stopListening(): Promise<void> {
        if (!this.isListening) {
            return;
        }

        try {
            if (this.recognition && typeof this.recognition.stop === 'function') {
                this.recognition.stop();
            }
            
            if (this.wakeWordDetector) {
                this.wakeWordDetector.stop();
            }

            this.isListening = false;
        } catch (error) {
            this.logger.error('Failed to stop listening:', error);
            throw error;
        }
    }

    private isBrowserSpeechAvailable(): boolean {
        return typeof window !== 'undefined' && (
            'webkitSpeechRecognition' in window || 
            'SpeechRecognition' in window
        );
    }

    getListeningState(): boolean {
        return this.isListening;
    }

    addCustomCommand(intent: string, handler: Function): void {
        this.commands.set(intent, handler);
        this.logger.info(`Custom command added: ${intent}`);
    }

    removeCustomCommand(intent: string): void {
        this.commands.delete(intent);
        this.logger.info(`Custom command removed: ${intent}`);
    }
}
