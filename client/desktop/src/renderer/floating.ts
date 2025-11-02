class FloatingAssistant {
    private orb: HTMLElement;
    private pulse: HTMLElement;
    private transcriptOverlay: HTMLElement;
    private transcriptText: HTMLElement;
    private isDragging = false;
    private dragOffset = { x: 0, y: 0 };

    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.setupDragAndDrop();
    }

    private initializeElements(): void {
        this.orb = document.getElementById('assistantOrb')!;
        this.pulse = document.getElementById('orbPulse')!;
        this.transcriptOverlay = document.getElementById('transcriptOverlay')!;
        this.transcriptText = document.getElementById('transcriptText')!;
    }

    private setupEventListeners(): void {
        // Click to toggle main window
        this.orb.addEventListener('click', (e) => {
            if (!this.isDragging) {
                window.electronAPI.toggleMainWindow();
            }
        });

        // Double click to start/stop listening
        this.orb.addEventListener('dblclick', () => {
            this.toggleListening();
        });

        // Context menu for settings
        this.orb.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showContextMenu(e.clientX, e.clientY);
        });

        // Listen for voice activity from main process
        window.electronAPI.onVoiceActivity((event, data) => {
            this.handleVoiceActivity(data);
        });

        // Listen for AI responses
        window.electronAPI.onAIResponse((event, data) => {
            this.handleAIResponse(data);
        });
    }

    private setupDragAndDrop(): void {
        this.orb.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.dragOffset.x = e.clientX - this.orb.getBoundingClientRect().left;
            this.dragOffset.y = e.clientY - this.orb.getBoundingClientRect().top;
            
            this.orb.style.cursor = 'grabbing';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                const x = e.clientX - this.dragOffset.x;
                const y = e.clientY - this.dragOffset.y;
                
                window.electronAPI.setFloatingPosition(x, y);
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.orb.style.cursor = 'move';
            }
        });
    }

    private async toggleListening(): Promise<void> {
        const isListening = this.orb.classList.contains('listening');
        
        if (isListening) {
            await window.electronAPI.stopListening();
            this.orb.classList.remove('listening');
            this.pulse.classList.remove('active');
        } else {
            await window.electronAPI.startListening();
            this.orb.classList.add('listening');
            this.pulse.classList.add('active');
        }
    }

    private handleVoiceActivity(data: any): void {
        if (data.isListening) {
            this.showTranscript(data.transcript || 'Listening...');
        } else if (data.transcript) {
            this.showTranscript(data.transcript);
            setTimeout(() => this.hideTranscript(), 3000);
        }
    }

    private handleAIResponse(data: any): void {
        if (data.success) {
            this.orb.classList.add('processing');
            setTimeout(() => {
                this.orb.classList.remove('processing');
            }, 2000);
        }
    }

    private showTranscript(text: string): void {
        this.transcriptText.textContent = text;
        this.transcriptOverlay.classList.add('visible');
    }

    private hideTranscript(): void {
        this.transcriptOverlay.classList.remove('visible');
    }

    private showContextMenu(x: number, y: number): void {
        // Simple context menu implementation
        const menu = document.createElement('div');
        menu.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 0;
            border-radius: 8px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            z-index: 10000;
            min-width: 150px;
        `;

        const menuItems = [
            { label: 'Settings', action: () => this.openSettings() },
            { label: 'Voice Training', action: () => this.startVoiceTraining() },
            { label: 'Quit', action: () => this.quitApp() }
        ];

        menuItems.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.textContent = item.label;
            menuItem.style.cssText = `
                padding: 8px 16px;
                cursor: pointer;
                font-size: 14px;
            `;
            menuItem.addEventListener('mouseenter', () => {
                menuItem.style.background = 'rgba(255, 255, 255, 0.1)';
            });
            menuItem.addEventListener('mouseleave', () => {
                menuItem.style.background = 'transparent';
            });
            menuItem.addEventListener('click', item.action);
            menu.appendChild(menuItem);
        });

        document.body.appendChild(menu);

        // Remove menu when clicking elsewhere
        const removeMenu = () => {
            document.body.removeChild(menu);
            document.removeEventListener('click', removeMenu);
        };
        setTimeout(() => document.addEventListener('click', removeMenu));
    }

    private openSettings(): void {
        window.electronAPI.toggleMainWindow();
        // Navigate to settings page in main window
    }

    private startVoiceTraining(): void {
        // Start voice training process
        console.log('Starting voice training...');
    }

    private quitApp(): void {
        if (confirm('Are you sure you want to quit AI Assistant?')) {
            window.close();
        }
    }
}

// Initialize the floating assistant when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FloatingAssistant();
});
