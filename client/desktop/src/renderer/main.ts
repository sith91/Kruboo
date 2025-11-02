class MainWindowApp {
    private currentTab: string = 'dashboard';
    private settings: any = {};

    constructor() {
        this.initializeApp();
    }

    private async initializeApp(): Promise<void> {
        this.setupNavigation();
        this.setupEventListeners();
        this.loadSettings();
        this.loadRecentActivity();
        
        // Initialize with dashboard
        this.showTab('dashboard');
    }

    private setupNavigation(): void {
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const tab = item.getAttribute('data-tab');
                if (tab) {
                    this.showTab(tab);
                    this.setActiveNavItem(item);
                }
            });
        });
    }

    private setupEventListeners(): void {
        // Voice training button
        document.getElementById('voiceTrainingBtn')?.addEventListener('click', () => {
            this.startVoiceTraining();
        });

        // Quick action button
        document.getElementById('quickActionBtn')?.addEventListener('click', () => {
            this.showQuickActions();
        });

        // Settings changes
        this.setupSettingsListeners();

        // Model selection
        this.setupModelSelection();
    }

    private setupSettingsListeners(): void {
        // Speech rate slider
        const speechRateSlider = document.getElementById('speechRate') as HTMLInputElement;
        const speechRateValue = document.getElementById('speechRateValue') as HTMLElement;
        
        speechRateSlider?.addEventListener('input', (e) => {
            const value = (e.target as HTMLInputElement).value;
            if (speechRateValue) {
                speechRateValue.textContent = `${value}x`;
            }
            this.saveSetting('speechRate', parseFloat(value));
        });

        // Speech pitch slider
        const speechPitchSlider = document.getElementById('speechPitch') as HTMLInputElement;
        const speechPitchValue = document.getElementById('speechPitchValue') as HTMLElement;
        
        speechPitchSlider?.addEventListener('input', (e) => {
            const value = (e.target as HTMLInputElement).value;
            if (speechPitchValue) {
                speechPitchValue.textContent = value;
            }
            this.saveSetting('speechPitch', parseFloat(value));
        });

        // Toggle settings
        const toggles = document.querySelectorAll('input[type="checkbox"]');
        toggles.forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const target = e.target as HTMLInputElement;
                this.saveSetting(target.id, target.checked);
            });
        });

        // Select settings
        const selects = document.querySelectorAll('select');
        selects.forEach(select => {
            select.addEventListener('change', (e) => {
                const target = e.target as HTMLSelectElement;
                this.saveSetting(target.id, target.value);
            });
        });
    }

    private setupModelSelection(): void {
        const modelCards = document.querySelectorAll('.model-card');
        
        modelCards.forEach(card => {
            card.addEventListener('click', () => {
                // Remove active class from all cards
                modelCards.forEach(c => c.classList.remove('active'));
                // Add active class to clicked card
                card.classList.add('active');
                
                const model = card.getAttribute('data-model');
                this.saveSetting('selectedModel', model);
            });
        });
    }

    private showTab(tabName: string): void {
        // Hide all tab contents
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(tab => tab.classList.remove('active'));

        // Show selected tab content
        const selectedTab = document.getElementById(tabName);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }

        // Update content title
        const contentTitle = document.getElementById('contentTitle');
        if (contentTitle) {
            contentTitle.textContent = this.getTabTitle(tabName);
        }

        this.currentTab = tabName;
    }

    private setActiveNavItem(activeItem: Element): void {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => item.classList.remove('active'));
        activeItem.classList.add('active');
    }

    private getTabTitle(tabName: string): string {
        const titles: { [key: string]: string } = {
            dashboard: 'Dashboard',
            voice: 'Voice Settings',
            ai: 'AI Models',
            privacy: 'Privacy & Security',
            plugins: 'Plugins',
            system: 'System Settings'
        };
        return titles[tabName] || 'Settings';
    }

    private async loadSettings(): Promise<void> {
        try {
            // In a real app, this would load from electron store or backend
            this.settings = {
                wakeWord: 'assistant',
                language: 'en',
                continuousListening: false,
                noiseCancellation: true,
                speechRate: 1.0,
                speechPitch: 1.0,
                selectedModel: 'deepseek',
                autoModelSelection: true
            };

            this.applySettingsToUI();
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    private applySettingsToUI(): void {
        // Apply settings to form elements
        Object.keys(this.settings).forEach(key => {
            const element = document.getElementById(key) as HTMLInputElement | HTMLSelectElement;
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = this.settings[key];
                } else {
                    element.value = this.settings[key];
                }
            }
        });

        // Update slider values
        const speechRateValue = document.getElementById('speechRateValue');
        if (speechRateValue) {
            speechRateValue.textContent = `${this.settings.speechRate}x`;
        }

        const speechPitchValue = document.getElementById('speechPitchValue');
        if (speechPitchValue) {
            speechPitchValue.textContent = this.settings.speechPitch.toString();
        }

        // Set active model card
        const activeModelCard = document.querySelector(`[data-model="${this.settings.selectedModel}"]`);
        if (activeModelCard) {
            activeModelCard.classList.add('active');
        }
    }

    private saveSetting(key: string, value: any): void {
        this.settings[key] = value;
        // In a real app, this would save to electron store or backend
        console.log('Saving setting:', key, value);
        
        // Notify main process about setting change
        if (window.electronAPI) {
            window.electronAPI.processAIRequest({
                type: 'setting_update',
                key,
                value
            });
        }
    }

    private async startVoiceTraining(): Promise<void> {
        const trainingProgress = document.getElementById('trainingProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const startTrainingBtn = document.getElementById('startTrainingBtn') as HTMLButtonElement;

        if (trainingProgress && progressFill && progressText && startTrainingBtn) {
            startTrainingBtn.disabled = true;
            trainingProgress.classList.remove('hidden');

            // Simulate training progress
            for (let i = 0; i <= 100; i += 10) {
                progressFill.style.width = `${i}%`;
                progressText.textContent = `Training... ${i}%`;
                await this.delay(500);
            }

            progressText.textContent = 'Training completed successfully!';
            startTrainingBtn.disabled = false;
            
            // Hide progress after delay
            setTimeout(() => {
                trainingProgress.classList.add('hidden');
            }, 2000);
        }
    }

    private async loadRecentActivity(): Promise<void> {
        const activityList = document.getElementById('activityList');
        if (!activityList) return;

        // Mock activity data
        const activities = [
            { icon: '🎤', text: 'Voice command processed: "Open Chrome"', time: '2 minutes ago' },
            { icon: '🔍', text: 'Web search: "AI trends 2024"', time: '15 minutes ago' },
            { icon: '📧', text: 'Email drafted using voice', time: '1 hour ago' },
            { icon: '🎵', text: 'Music playback started', time: '2 hours ago' },
            { icon: '🔧', text: 'System optimization performed', time: '3 hours ago' }
        ];

        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${activity.icon}</div>
                <div class="activity-content">
                    <div class="activity-text">${activity.text}</div>
                    <div class="activity-time">${activity.time}</div>
                </div>
            </div>
        `).join('');
    }

    private showQuickActions(): void {
        // Implement quick actions menu
        console.log('Showing quick actions...');
    }

    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize the main window app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MainWindowApp();
});
