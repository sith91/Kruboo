import { CoreEngine, ServiceClient } from '@ai-assistant/core';
import { SimpleIPCHandler } from './src/main/simple-ipc-handler.js';

class DesktopApp {
    private coreEngine: CoreEngine;
    private ipcHandler: SimpleIPCHandler;

    constructor() {
        this.coreEngine = new CoreEngine();
        this.setupApp();
    }

    private async setupApp(): Promise<void> {
        app.whenReady().then(async () => {
            // Initialize core engine (which initializes service client)
            await this.coreEngine.initialize();
            
            // Setup simplified IPC handlers
            this.ipcHandler = new SimpleIPCHandler(this.coreEngine.getServiceClient());
            this.ipcHandler.setupHandlers();
            
            // Create windows
            this.createMainWindow();
            this.createFloatingWindow();
            
            this.logger.info('Desktop app initialized with Python-centric architecture');
        });

        // ... rest of app lifecycle
    }

    // Remove complex service connector setup
    // Remove duplicate AI processing logic
    // Keep only window management and system integration
}
