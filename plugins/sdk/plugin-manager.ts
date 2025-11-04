import { Logger } from '@ai-assistant/core';

export interface PluginManifest {
    id: string;
    name: string;
    version: string;
    description: string;
    author: string;
    license: string;
    main: string;
    capabilities: string[];
    permissions: string[];
    config?: { [key: string]: any };
}

export interface PluginContext {
    logger: Logger;
    config: any;
    system: any;
    ai: any;
    voice: any;
}

export abstract class BasePlugin {
    public manifest: PluginManifest;
    public context: PluginContext;
    public isEnabled: boolean = false;

    constructor(manifest: PluginManifest, context: PluginContext) {
        this.manifest = manifest;
        this.context = context;
    }

    abstract initialize(): Promise<void>;
    abstract destroy(): Promise<void>;
    
    // Optional lifecycle methods
    async onEnable(): Promise<void> {}
    async onDisable(): Promise<void> {}
    async onConfigChange(newConfig: any): Promise<void> {}
}

export class PluginManager {
    private logger: Logger;
    private plugins: Map<string, BasePlugin> = new Map();
    private pluginContext: PluginContext;

    constructor() {
        this.logger = new Logger('PluginManager');
        this.pluginContext = this.createPluginContext();
    }

    private createPluginContext(): PluginContext {
        return {
            logger: new Logger('Plugin'),
            config: this.getConfigAPI(),
            system: this.getSystemAPI(),
            ai: this.getAIAPI(),
            voice: this.getVoiceAPI()
        };
    }

    async loadPlugin(pluginPath: string): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.info(`Loading plugin from: ${pluginPath}`);

            // Read plugin manifest
            const manifest = await this.readManifest(pluginPath);
            
            // Validate manifest
            const validation = this.validateManifest(manifest);
            if (!validation.isValid) {
                return { success: false, error: validation.errors.join(', ') };
            }

            // Load plugin module
            const pluginModule = await this.loadPluginModule(pluginPath, manifest);
            
            // Initialize plugin
            const plugin = new pluginModule(manifest, this.pluginContext);
            await plugin.initialize();

            // Register plugin
            this.plugins.set(manifest.id, plugin);
            plugin.isEnabled = true;

            this.logger.info(`Plugin loaded successfully: ${manifest.name} v${manifest.version}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to load plugin from ${pluginPath}:`, error);
            return { success: false, error: error.message };
        }
    }

    async unloadPlugin(pluginId: string): Promise<{ success: boolean; error?: string }> {
        try {
            const plugin = this.plugins.get(pluginId);
            if (!plugin) {
                return { success: false, error: 'Plugin not found' };
            }

            await plugin.destroy();
            this.plugins.delete(pluginId);

            this.logger.info(`Plugin unloaded: ${pluginId}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to unload plugin ${pluginId}:`, error);
            return { success: false, error: error.message };
        }
    }

    async enablePlugin(pluginId: string): Promise<{ success: boolean; error?: string }> {
        try {
            const plugin = this.plugins.get(pluginId);
            if (!plugin) {
                return { success: false, error: 'Plugin not found' };
            }

            await plugin.onEnable();
            plugin.isEnabled = true;

            this.logger.info(`Plugin enabled: ${pluginId}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to enable plugin ${pluginId}:`, error);
            return { success: false, error: error.message };
        }
    }

    async disablePlugin(pluginId: string): Promise<{ success: boolean; error?: string }> {
        try {
            const plugin = this.plugins.get(pluginId);
            if (!plugin) {
                return { success: false, error: 'Plugin not found' };
            }

            await plugin.onDisable();
            plugin.isEnabled = false;

            this.logger.info(`Plugin disabled: ${pluginId}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to disable plugin ${pluginId}:`, error);
            return { success: false, error: error.message };
        }
    }

    getPlugin(pluginId: string): BasePlugin | undefined {
        return this.plugins.get(pluginId);
    }

    getAllPlugins(): BasePlugin[] {
        return Array.from(this.plugins.values());
    }

    getEnabledPlugins(): BasePlugin[] {
        return this.getAllPlugins().filter(plugin => plugin.isEnabled);
    }

    private async readManifest(pluginPath: string): Promise<PluginManifest> {
        const { readFile } = await import('fs/promises');
        const manifestPath = require('path').join(pluginPath, 'plugin.json');
        
        const content = await readFile(manifestPath, 'utf8');
        return JSON.parse(content);
    }

    private validateManifest(manifest: PluginManifest): { isValid: boolean; errors: string[] } {
        const errors: string[] = [];
        const required = ['id', 'name', 'version', 'description', 'author', 'main', 'capabilities'];

        for (const field of required) {
            if (!manifest[field as keyof PluginManifest]) {
                errors.push(`Missing required field: ${field}`);
            }
        }

        // Validate version format
        if (manifest.version && !/^\d+\.\d+\.\d+$/.test(manifest.version)) {
            errors.push('Invalid version format. Use semantic versioning (e.g., 1.0.0)');
        }

        // Validate capabilities
        const validCapabilities = ['system', 'ai', 'voice', 'files', 'network', 'ui'];
        if (manifest.capabilities) {
            for (const capability of manifest.capabilities) {
                if (!validCapabilities.includes(capability)) {
                    errors.push(`Invalid capability: ${capability}. Valid: ${validCapabilities.join(', ')}`);
                }
            }
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    private async loadPluginModule(pluginPath: string, manifest: PluginManifest): Promise<any> {
        const mainPath = require('path').join(pluginPath, manifest.main);
        
        // In a real implementation, this would use a proper module loader
        // For now, we'll use a dynamic import (note: this has security implications)
        const module = await import(mainPath);
        return module.default || module;
    }

    private getConfigAPI(): any {
        return {
            get: (key: string) => {
                // Get plugin configuration
                return null;
            },
            set: (key: string, value: any) => {
                // Set plugin configuration
            },
            getAll: () => {
                // Get all plugin configuration
                return {};
            }
        };
    }

    private getSystemAPI(): any {
        return {
            executeCommand: (command: string) => {
                // Execute system command
            },
            getSystemInfo: () => {
                // Get system information
                return {};
            },
            openApplication: (appName: string) => {
                // Open application
            }
        };
    }

    private getAIAPI(): any {
        return {
            processRequest: (request: any) => {
                // Process AI request
                return {};
            },
            generateText: (prompt: string) => {
                // Generate text using AI
                return '';
            }
        };
    }

    private getVoiceAPI(): any {
        return {
            registerCommand: (pattern: string, handler: Function) => {
                // Register voice command
            },
            speak: (text: string) => {
                // Speak text
            }
        };
    }
}

// Example plugin implementation
export class ExamplePlugin extends BasePlugin {
    async initialize(): Promise<void> {
        this.context.logger.info(`Initializing plugin: ${this.manifest.name}`);
        
        // Register voice commands
        this.context.voice.registerCommand('hello', this.handleHelloCommand.bind(this));
        
        // Set up any necessary infrastructure
        this.context.logger.info('Example plugin initialized successfully');
    }

    async destroy(): Promise<void> {
        this.context.logger.info(`Destroying plugin: ${this.manifest.name}`);
        // Clean up resources
    }

    async onEnable(): Promise<void> {
        this.context.logger.info('Example plugin enabled');
    }

    async onDisable(): Promise<void> {
        this.context.logger.info('Example plugin disabled');
    }

    private async handleHelloCommand(params: any): Promise<void> {
        this.context.logger.info('Hello command received!');
        await this.context.voice.speak('Hello! How can I help you today?');
    }
}
