import { Logger } from '../utils/logger.js';
import { ConfigManager } from '../utils/config.js';

export interface PrivacySettings {
    dataRetention: 'immediate' | 'day' | 'week' | 'month' | 'never';
    voiceData: boolean;
    conversationHistory: boolean;
    usageAnalytics: boolean;
    thirdPartySharing: boolean;
    blockchainVerification: boolean;
}

export interface DataConsent {
    feature: string;
    allowed: boolean;
    timestamp: Date;
    purpose: string;
}

export class PrivacyManager {
    private logger: Logger;
    private config: ConfigManager;
    private privacySettings: PrivacySettings;
    private dataConsents: Map<string, DataConsent> = new Map();
    private encryptionKey: CryptoKey | null = null;

    constructor() {
        this.logger = new Logger('PrivacyManager');
        this.config = ConfigManager.getInstance();
        this.privacySettings = this.getDefaultPrivacySettings();
        this.initializeEncryption();
    }

    private getDefaultPrivacySettings(): PrivacySettings {
        return {
            dataRetention: 'week',
            voiceData: false,
            conversationHistory: true,
            usageAnalytics: true,
            thirdPartySharing: false,
            blockchainVerification: false
        };
    }

    private async initializeEncryption(): Promise<void> {
        try {
            // Generate or load encryption key for local data
            this.encryptionKey = await this.getOrCreateEncryptionKey();
            this.logger.info('Encryption initialized');
        } catch (error) {
            this.logger.error('Failed to initialize encryption:', error);
        }
    }

    private async getOrCreateEncryptionKey(): Promise<CryptoKey> {
        // Try to load existing key from secure storage
        const storedKey = localStorage.getItem('encryption_key');
        
        if (storedKey) {
            // Import existing key
            const keyData = Uint8Array.from(atob(storedKey), c => c.charCodeAt(0));
            return await crypto.subtle.importKey(
                'raw',
                keyData,
                { name: 'AES-GCM' },
                false,
                ['encrypt', 'decrypt']
            );
        } else {
            // Generate new key
            const key = await crypto.subtle.generateKey(
                { name: 'AES-GCM', length: 256 },
                true,
                ['encrypt', 'decrypt']
            );

            // Export and store the key
            const exported = await crypto.subtle.exportKey('raw', key);
            const keyString = btoa(String.fromCharCode(...new Uint8Array(exported)));
            localStorage.setItem('encryption_key', keyString);

            return key;
        }
    }

    async encryptData(data: any): Promise<{ encrypted: ArrayBuffer; iv: Uint8Array }> {
        if (!this.encryptionKey) {
            throw new Error('Encryption not initialized');
        }

        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(JSON.stringify(data));
        
        const iv = crypto.getRandomValues(new Uint8Array(12));
        
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            this.encryptionKey,
            dataBuffer
        );

        return { encrypted, iv };
    }

    async decryptData(encrypted: ArrayBuffer, iv: Uint8Array): Promise<any> {
        if (!this.encryptionKey) {
            throw new Error('Encryption not initialized');
        }

        const decrypted = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv },
            this.encryptionKey,
            encrypted
        );

        const decoder = new TextDecoder();
        return JSON.parse(decoder.decode(decrypted));
    }

    updatePrivacySettings(settings: Partial<PrivacySettings>): void {
        this.privacySettings = { ...this.privacySettings, ...settings };
        this.logger.info('Privacy settings updated', settings);
        
        // Apply settings immediately
        this.applyPrivacySettings();
    }

    getPrivacySettings(): PrivacySettings {
        return { ...this.privacySettings };
    }

    private applyPrivacySettings(): void {
        // Apply data retention policy
        this.applyDataRetentionPolicy();
        
        // Apply consent settings
        this.applyConsentSettings();
        
        // Apply blockchain verification if enabled
        if (this.privacySettings.blockchainVerification) {
            this.enableBlockchainVerification();
        }
    }

    private applyDataRetentionPolicy(): void {
        const retentionPeriods = {
            immediate: 0,
            day: 24 * 60 * 60 * 1000,
            week: 7 * 24 * 60 * 60 * 1000,
            month: 30 * 24 * 60 * 60 * 1000,
            never: Infinity
        };

        const retentionTime = retentionPeriods[this.privacySettings.dataRetention];
        this.logger.info(`Applying data retention policy: ${this.privacySettings.dataRetention}`);
        
        // This would actually clean up old data based on the retention policy
        setTimeout(() => {
            this.cleanupOldData(retentionTime);
        }, 0);
    }

    private async cleanupOldData(maxAge: number): Promise<void> {
        try {
            // Clean up various types of data based on privacy settings
            if (!this.privacySettings.voiceData) {
                await this.cleanupVoiceData();
            }

            if (!this.privacySettings.conversationHistory) {
                await this.cleanupConversationHistory();
            }

            if (maxAge !== Infinity) {
                await this.cleanupDataOlderThan(maxAge);
            }

            this.logger.info('Data cleanup completed');
        } catch (error) {
            this.logger.error('Data cleanup failed:', error);
        }
    }

    private async cleanupVoiceData(): Promise<void> {
        // Clean up voice recordings and transcripts
        const voiceDataKeys = Object.keys(localStorage).filter(key => 
            key.startsWith('voice_') || key.startsWith('recording_')
        );

        voiceDataKeys.forEach(key => localStorage.removeItem(key));
        this.logger.info(`Cleaned up ${voiceDataKeys.length} voice data items`);
    }

    private async cleanupConversationHistory(): Promise<void> {
        // Clean up conversation history
        const conversationKeys = Object.keys(localStorage).filter(key => 
            key.startsWith('conversation_') || key.startsWith('chat_')
        );

        conversationKeys.forEach(key => localStorage.removeItem(key));
        this.logger.info(`Cleaned up ${conversationKeys.length} conversation items`);
    }

    private async cleanupDataOlderThan(maxAge: number): Promise<void> {
        const now = Date.now();
        let cleanedCount = 0;

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('timestamp_')) {
                const timestamp = parseInt(localStorage.getItem(key) || '0');
                if (now - timestamp > maxAge) {
                    // Remove the associated data
                    const dataKey = key.replace('timestamp_', '');
                    localStorage.removeItem(dataKey);
                    localStorage.removeItem(key);
                    cleanedCount++;
                }
            }
        }

        this.logger.info(`Cleaned up ${cleanedCount} items older than ${maxAge}ms`);
    }

    private applyConsentSettings(): void {
        // Update consents based on privacy settings
        this.updateConsent('voice_data', this.privacySettings.voiceData, 
            'Store and process voice recordings');
        
        this.updateConsent('conversation_history', this.privacySettings.conversationHistory,
            'Store conversation history for improvement');
        
        this.updateConsent('usage_analytics', this.privacySettings.usageAnalytics,
            'Collect usage analytics for product improvement');
        
        this.updateConsent('third_party_sharing', this.privacySettings.thirdPartySharing,
            'Share anonymized data with third parties');
    }

    private updateConsent(feature: string, allowed: boolean, purpose: string): void {
        this.dataConsents.set(feature, {
            feature,
            allowed,
            timestamp: new Date(),
            purpose
        });
    }

    private enableBlockchainVerification(): void {
        this.logger.info('Blockchain verification enabled');
        
        // This would integrate with actual blockchain services
        // for data integrity verification
    }

    async requestConsent(feature: string, purpose: string): Promise<boolean> {
        const existingConsent = this.dataConsents.get(feature);
        
        if (existingConsent) {
            return existingConsent.allowed;
        }

        // In a real app, this would show a proper consent dialog
        const allowed = confirm(`Allow ${purpose}?`);
        
        this.updateConsent(feature, allowed, purpose);
        return allowed;
    }

    getDataConsents(): DataConsent[] {
        return Array.from(this.dataConsents.values());
    }

    async exportUserData(): Promise<Blob> {
        try {
            const exportData = {
                version: '1.0',
                exportDate: new Date().toISOString(),
                privacySettings: this.privacySettings,
                consents: this.getDataConsents(),
                // Add other user data here
                conversations: this.exportConversations(),
                voiceData: this.exportVoiceData(),
                settings: this.exportSettings()
            };

            const encrypted = await this.encryptData(exportData);
            return new Blob([JSON.stringify(encrypted)], { 
                type: 'application/json' 
            });

        } catch (error) {
            this.logger.error('Failed to export user data:', error);
            throw error;
        }
    }

    async deleteAllUserData(): Promise<void> {
        try {
            this.logger.info('Deleting all user data');
            
            // Clear all local storage except essential settings
            const keysToKeep = ['encryption_key', 'privacy_settings'];
            
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && !keysToKeep.includes(key)) {
                    localStorage.removeItem(key);
                }
            }

            // Reset privacy settings to defaults
            this.privacySettings = this.getDefaultPrivacySettings();
            this.dataConsents.clear();

            this.logger.info('All user data deleted successfully');
        } catch (error) {
            this.logger.error('Failed to delete user data:', error);
            throw error;
        }
    }

    private exportConversations(): any[] {
        // Export conversation history
        return [];
    }

    private exportVoiceData(): any[] {
        // Export voice data (if consent allows)
        if (!this.privacySettings.voiceData) {
            return [];
        }
        return [];
    }

    private exportSettings(): any {
        // Export user settings
        return {};
    }

    // Blockchain integration for data verification
    async anchorDataToBlockchain(data: any, description: string): Promise<string> {
        if (!this.privacySettings.blockchainVerification) {
            throw new Error('Blockchain verification not enabled');
        }

        try {
            // Create data hash
            const dataString = JSON.stringify(data);
            const encoder = new TextEncoder();
            const dataBuffer = encoder.encode(dataString);
            const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

            // In a real implementation, this would send the hash to a blockchain
            // For now, we'll simulate it
            const transactionId = this.simulateBlockchainTransaction(hashHex, description);
            
            this.logger.info(`Data anchored to blockchain: ${transactionId}`);
            return transactionId;

        } catch (error) {
            this.logger.error('Failed to anchor data to blockchain:', error);
            throw error;
        }
    }

    private simulateBlockchainTransaction(hash: string, description: string): string {
        // Simulate blockchain transaction
        const timestamp = Date.now();
        return `0x${hash.substring(0, 16)}${timestamp.toString(16)}`;
    }

    async verifyDataWithBlockchain(data: any, transactionId: string): Promise<boolean> {
        try {
            // Verify data against blockchain record
            const dataString = JSON.stringify(data);
            const encoder = new TextEncoder();
            const dataBuffer = encoder.encode(dataString);
            const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

            // In a real implementation, this would verify against the blockchain
            // For now, we'll simulate verification
            const expectedHash = transactionId.substring(2, 34); // Extract hash from simulated transaction ID
            return hashHex.startsWith(expectedHash);

        } catch (error) {
            this.logger.error('Failed to verify data with blockchain:', error);
            return false;
        }
    }
}
