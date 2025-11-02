import { Logger } from '@ai-assistant/core';

export class VoiceTrainingManager {
    private logger: Logger;
    private isTraining: boolean = false;
    private trainingPhrases: string[] = [
        "Hello assistant",
        "Open my browser",
        "What's the weather today",
        "Set a reminder for tomorrow",
        "Search for artificial intelligence",
        "Play some music",
        "Tell me a joke",
        "How's my schedule looking",
        "Send an email",
        "Goodbye assistant"
    ];
    private currentPhraseIndex: number = 0;
    private trainingData: any[] = [];

    constructor() {
        this.logger = new Logger('VoiceTraining');
    }

    async startTraining(): Promise<void> {
        if (this.isTraining) {
            this.logger.warn('Training already in progress');
            return;
        }

        this.isTraining = true;
        this.currentPhraseIndex = 0;
        this.trainingData = [];

        this.logger.info('Starting voice training session');

        // Show training UI
        this.showTrainingUI();
        
        // Start with first phrase
        await this.presentNextPhrase();
    }

    async stopTraining(): Promise<void> {
        if (!this.isTraining) {
            return;
        }

        this.isTraining = false;
        this.logger.info('Voice training stopped');

        // Hide training UI
        this.hideTrainingUI();

        // Save training data
        await this.saveTrainingData();
    }

    private async presentNextPhrase(): Promise<void> {
        if (!this.isTraining || this.currentPhraseIndex >= this.trainingPhrases.length) {
            await this.completeTraining();
            return;
        }

        const phrase = this.trainingPhrases[this.currentPhraseIndex];
        this.updateTrainingUI(phrase, this.currentPhraseIndex + 1, this.trainingPhrases.length);

        // Start listening for this phrase
        await this.startPhraseCapture(phrase);
    }

    private async startPhraseCapture(phrase: string): Promise<void> {
        this.logger.info(`Capturing phrase: ${phrase}`);

        // Show recording UI
        this.showRecordingUI();

        try {
            // Start voice recording
            await window.electronAPI.startListening();
            
            // Set timeout for phrase capture (5 seconds)
            setTimeout(async () => {
                if (this.isTraining) {
                    await this.captureComplete(phrase, 'timeout');
                }
            }, 5000);

        } catch (error) {
            this.logger.error('Failed to start phrase capture:', error);
            await this.captureComplete(phrase, 'error');
        }
    }

    async handleVoiceInput(transcript: string, confidence: number): Promise<void> {
        if (!this.isTraining) return;

        const expectedPhrase = this.trainingPhrases[this.currentPhraseIndex].toLowerCase();
        const actualPhrase = transcript.toLowerCase();

        // Calculate similarity (simple implementation)
        const similarity = this.calculateSimilarity(expectedPhrase, actualPhrase);
        
        this.logger.debug(`Voice input similarity: ${similarity} (expected: "${expectedPhrase}", got: "${actualPhrase}")`);

        if (similarity > 0.7) { // Good match
            await this.captureComplete(transcript, 'success', confidence, similarity);
        } else {
            // Show feedback for poor match
            this.showFeedback(`Please try again: "${this.trainingPhrases[this.currentPhraseIndex]}"`, 'warning');
        }
    }

    private async captureComplete(
        phrase: string, 
        status: 'success' | 'timeout' | 'error',
        confidence?: number,
        similarity?: number
    ): Promise<void> {
        // Stop listening
        await window.electronAPI.stopListening();
        
        // Hide recording UI
        this.hideRecordingUI();

        // Store training data
        this.trainingData.push({
            phrase: this.trainingPhrases[this.currentPhraseIndex],
            captured: phrase,
            status,
            confidence,
            similarity,
            timestamp: new Date().toISOString()
        });

        // Show feedback
        if (status === 'success') {
            this.showFeedback('Great! Phrase captured successfully.', 'success');
            this.currentPhraseIndex++;
            
            // Brief pause before next phrase
            setTimeout(() => {
                this.presentNextPhrase();
            }, 1500);
        } else if (status === 'timeout') {
            this.showFeedback('No voice detected. Please try again.', 'warning');
            // Retry same phrase
            setTimeout(() => {
                this.presentNextPhrase();
            }, 2000);
        } else {
            this.showFeedback('Error capturing voice. Please try again.', 'error');
            // Retry same phrase
            setTimeout(() => {
                this.presentNextPhrase();
            }, 2000);
        }
    }

    private async completeTraining(): Promise<void> {
        this.isTraining = false;
        
        // Calculate overall accuracy
        const successfulCaptures = this.trainingData.filter(d => d.status === 'success');
        const accuracy = (successfulCaptures.length / this.trainingPhrases.length) * 100;

        this.logger.info(`Voice training completed with ${accuracy.toFixed(1)}% accuracy`);

        // Show completion UI
        this.showCompletionUI(accuracy);

        // Save final training data
        await this.saveTrainingData();

        // Send training data to main process for processing
        await window.electronAPI.processAIRequest({
            type: 'voice_training_data',
            data: this.trainingData,
            accuracy
        });
    }

    private calculateSimilarity(str1: string, str2: string): number {
        // Simple similarity calculation using Levenshtein distance
        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;
        
        if (longer.length === 0) return 1.0;
        
        const distance = this.levenshteinDistance(longer, shorter);
        return (longer.length - distance) / longer.length;
    }

    private levenshteinDistance(str1: string, str2: string): number {
        const matrix = Array(str2.length + 1).fill(null).map(() => Array(str1.length + 1).fill(null));

        for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
        for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;

        for (let j = 1; j <= str2.length; j++) {
            for (let i = 1; i <= str1.length; i++) {
                const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
                matrix[j][i] = Math.min(
                    matrix[j][i - 1] + 1, // deletion
                    matrix[j - 1][i] + 1, // insertion
                    matrix[j - 1][i - 1] + indicator // substitution
                );
            }
        }

        return matrix[str2.length][str1.length];
    }

    private showTrainingUI(): void {
        // Create training overlay
        const overlay = document.createElement('div');
        overlay.id = 'voiceTrainingOverlay';
        overlay.innerHTML = `
            <div class="voice-training-modal">
                <div class="training-header">
                    <h2>Voice Training</h2>
                    <button class="close-btn" id="closeTraining">×</button>
                </div>
                <div class="training-content">
                    <div class="progress-section">
                        <div class="progress-bar">
                            <div class="progress-fill" id="trainingProgressFill"></div>
                        </div>
                        <div class="progress-text" id="trainingProgressText">Preparing...</div>
                    </div>
                    <div class="phrase-section">
                        <div class="current-phrase" id="currentPhrase"></div>
                        <div class="phrase-instruction">Please say the phrase clearly</div>
                    </div>
                    <div class="feedback-section">
                        <div class="feedback-message" id="feedbackMessage"></div>
                    </div>
                    <div class="recording-indicator hidden" id="recordingIndicator">
                        <div class="pulse-animation"></div>
                        <span>Listening...</span>
                    </div>
                </div>
                <div class="training-footer">
                    <button class="btn btn-secondary" id="skipPhrase">Skip Phrase</button>
                    <button class="btn btn-primary" id="startTraining">Start Training</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Add event listeners
        document.getElementById('closeTraining')?.addEventListener('click', () => {
            this.stopTraining();
        });

        document.getElementById('skipPhrase')?.addEventListener('click', () => {
            this.skipCurrentPhrase();
        });

        document.getElementById('startTraining')?.addEventListener('click', () => {
            this.presentNextPhrase();
        });

        // Add styles
        this.addTrainingStyles();
    }

    private hideTrainingUI(): void {
        const overlay = document.getElementById('voiceTrainingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    private updateTrainingUI(phrase: string, current: number, total: number): void {
        const progressFill = document.getElementById('trainingProgressFill');
        const progressText = document.getElementById('trainingProgressText');
        const currentPhrase = document.getElementById('currentPhrase');
        const startBtn = document.getElementById('startTraining');

        if (progressFill) {
            progressFill.style.width = `${(current / total) * 100}%`;
        }

        if (progressText) {
            progressText.textContent = `Progress: ${current} of ${total}`;
        }

        if (currentPhrase) {
            currentPhrase.textContent = `"${phrase}"`;
        }

        if (startBtn) {
            startBtn.textContent = current === 1 ? 'Start Training' : 'Continue';
        }
    }

    private showRecordingUI(): void {
        const recordingIndicator = document.getElementById('recordingIndicator');
        if (recordingIndicator) {
            recordingIndicator.classList.remove('hidden');
        }
    }

    private hideRecordingUI(): void {
        const recordingIndicator = document.getElementById('recordingIndicator');
        if (recordingIndicator) {
            recordingIndicator.classList.add('hidden');
        }
    }

    private showFeedback(message: string, type: 'success' | 'warning' | 'error'): void {
        const feedbackMessage = document.getElementById('feedbackMessage');
        if (feedbackMessage) {
            feedbackMessage.textContent = message;
            feedbackMessage.className = `feedback-message ${type}`;
        }
    }

    private showCompletionUI(accuracy: number): void {
        const overlay = document.getElementById('voiceTrainingOverlay');
        if (overlay) {
            overlay.innerHTML = `
                <div class="voice-training-modal completion">
                    <div class="training-header">
                        <h2>Training Complete! 🎉</h2>
                    </div>
                    <div class="training-content">
                        <div class="completion-stats">
                            <div class="accuracy-circle">
                                <div class="accuracy-value">${accuracy.toFixed(1)}%</div>
                                <div class="accuracy-label">Accuracy</div>
                            </div>
                            <div class="completion-details">
                                <p>Your voice model has been trained successfully.</p>
                                <p>The assistant will now better understand your voice commands.</p>
                            </div>
                        </div>
                    </div>
                    <div class="training-footer">
                        <button class="btn btn-primary" id="finishTraining">Finish</button>
                    </div>
                </div>
            `;

            document.getElementById('finishTraining')?.addEventListener('click', () => {
                this.hideTrainingUI();
            });
        }
    }

    private async skipCurrentPhrase(): Promise<void> {
        this.trainingData.push({
            phrase: this.trainingPhrases[this.currentPhraseIndex],
            captured: null,
            status: 'skipped',
            timestamp: new Date().toISOString()
        });

        this.currentPhraseIndex++;
        await this.presentNextPhrase();
    }

    private async saveTrainingData(): Promise<void> {
        try {
            // Save to local storage or send to main process
            localStorage.setItem('voiceTrainingData', JSON.stringify(this.trainingData));
            
            // Update voice recognition accuracy in settings
            const successfulCaptures = this.trainingData.filter(d => d.status === 'success');
            const accuracy = (successfulCaptures.length / this.trainingPhrases.length) * 100;
            
            await window.electronAPI.processAIRequest({
                type: 'update_voice_accuracy',
                accuracy: Math.round(accuracy)
            });

        } catch (error) {
            this.logger.error('Failed to save training data:', error);
        }
    }

    private addTrainingStyles(): void {
        const style = document.createElement('style');
        style.textContent = `
            #voiceTrainingOverlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                backdrop-filter: blur(5px);
            }

            .voice-training-modal {
                background: white;
                border-radius: 12px;
                padding: 24px;
                width: 90%;
                max-width: 500px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            }

            .training-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }

            .training-header h2 {
                margin: 0;
                color: #1e293b;
            }

            .close-btn {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #64748b;
            }

            .close-btn:hover {
                color: #475569;
            }

            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
                overflow: hidden;
                margin-bottom: 8px;
            }

            .progress-fill {
                height: 100%;
                background: #3b82f6;
                border-radius: 4px;
                transition: width 0.3s ease;
                width: 0%;
            }

            .progress-text {
                text-align: center;
                color: #64748b;
                font-size: 14px;
            }

            .phrase-section {
                text-align: center;
                margin: 30px 0;
            }

            .current-phrase {
                font-size: 24px;
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 8px;
            }

            .phrase-instruction {
                color: #64748b;
                font-size: 14px;
            }

            .feedback-section {
                text-align: center;
                margin: 20px 0;
                min-height: 40px;
            }

            .feedback-message {
                padding: 12px;
                border-radius: 6px;
                font-weight: 500;
            }

            .feedback-message.success {
                background: #dcfce7;
                color: #166534;
                border: 1px solid #bbf7d0;
            }

            .feedback-message.warning {
                background: #fef3c7;
                color: #92400e;
                border: 1px solid #fde68a;
            }

            .feedback-message.error {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fecaca;
            }

            .recording-indicator {
                text-align: center;
                margin: 20px 0;
            }

            .pulse-animation {
                width: 40px;
                height: 40px;
                background: #ef4444;
                border-radius: 50%;
                margin: 0 auto 8px;
                animation: pulse 1.5s infinite;
            }

            .training-footer {
                display: flex;
                justify-content: space-between;
                margin-top: 20px;
            }

            .completion .accuracy-circle {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: linear-gradient(135deg, #10b981, #3b82f6);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                margin: 0 auto 20px;
            }

            .accuracy-value {
                font-size: 28px;
                font-weight: 700;
            }

            .accuracy-label {
                font-size: 14px;
                opacity: 0.9;
            }

            .completion-details {
                text-align: center;
                color: #64748b;
            }

            .hidden {
                display: none;
            }

            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.1); opacity: 0.7; }
                100% { transform: scale(1); opacity: 1; }
            }
        `;

        document.head.appendChild(style);
    }
}

// Export singleton instance
export const voiceTrainingManager = new VoiceTrainingManager();
