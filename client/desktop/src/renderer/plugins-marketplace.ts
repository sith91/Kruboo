import { Logger } from '@ai-assistant/core';

export interface Plugin {
    id: string;
    name: string;
    version: string;
    description: string;
    author: string;
    rating: number;
    downloads: number;
    category: string;
    tags: string[];
    compatible: boolean;
    installed: boolean;
    official: boolean;
    price: number; // 0 for free
    repository?: string;
    icon?: string;
}

export class PluginsMarketplace {
    private logger: Logger;
    private plugins: Plugin[] = [];
    private installedPlugins: Set<string> = new Set();
    private categories: string[] = [];

    constructor() {
        this.logger = new Logger('PluginsMarketplace');
        this.loadPlugins();
        this.loadInstalledPlugins();
    }

    async loadPlugins(): Promise<void> {
        try {
            // Mock plugin data - in real app, this would fetch from API
            this.plugins = [
                {
                    id: 'gmail-integration',
                    name: 'Gmail Integration',
                    version: '1.2.0',
                    description: 'Send and read emails using voice commands',
                    author: 'AI Assistant Team',
                    rating: 4.8,
                    downloads: 15420,
                    category: 'Communication',
                    tags: ['email', 'gmail', 'productivity'],
                    compatible: true,
                    installed: false,
                    official: true,
                    price: 0,
                    icon: '📧'
                },
                {
                    id: 'spotify-controller',
                    name: 'Spotify Controller',
                    version: '1.0.3',
                    description: 'Control Spotify playback with voice commands',
                    author: 'Music Labs',
                    rating: 4.6,
                    downloads: 8920,
                    category: 'Entertainment',
                    tags: ['music', 'spotify', 'playback'],
                    compatible: true,
                    installed: true,
                    official: false,
                    price: 0,
                    icon: '🎵'
                },
                {
                    id: 'smart-home',
                    name: 'Smart Home Control',
                    version: '2.1.0',
                    description: 'Control your smart home devices',
                    author: 'Home Automation Inc',
                    rating: 4.9,
                    downloads: 23450,
                    category: 'Home Automation',
                    tags: ['iot', 'smart home', 'automation'],
                    compatible: true,
                    installed: false,
                    official: false,
                    price: 4.99,
                    icon: '🏠'
                },
                {
                    id: 'code-assistant',
                    name: 'Code Assistant',
                    version: '1.5.0',
                    description: 'Advanced coding assistance and code generation',
                    author: 'Dev Tools Co',
                    rating: 4.7,
                    downloads: 18760,
                    category: 'Development',
                    tags: ['coding', 'programming', 'development'],
                    compatible: true,
                    installed: false,
                    official: false,
                    price: 0,
                    icon: '💻'
                },
                {
                    id: 'language-translator',
                    name: 'Real-time Translator',
                    version: '1.3.0',
                    description: 'Real-time voice translation for multiple languages',
                    author: 'AI Assistant Team',
                    rating: 4.8,
                    downloads: 21340,
                    category: 'Communication',
                    tags: ['translation', 'languages', 'multilingual'],
                    compatible: true,
                    installed: false,
                    official: true,
                    price: 0,
                    icon: '🌐'
                },
                {
                    id: 'fitness-tracker',
                    name: 'Fitness Assistant',
                    version: '1.1.0',
                    description: 'Track workouts and health metrics',
                    author: 'Health Tech',
                    rating: 4.4,
                    downloads: 5670,
                    category: 'Health & Fitness',
                    tags: ['fitness', 'health', 'workout'],
                    compatible: true,
                    installed: false,
                    official: false,
                    price: 2.99,
                    icon: '💪'
                }
            ];

            // Extract unique categories
            this.categories = [...new Set(this.plugins.map(p => p.category))];
            this.categories.sort();

            this.logger.info(`Loaded ${this.plugins.length} plugins across ${this.categories.length} categories`);

        } catch (error) {
            this.logger.error('Failed to load plugins:', error);
        }
    }

    async loadInstalledPlugins(): Promise<void> {
        try {
            // Load installed plugins from storage
            const installed = localStorage.getItem('installedPlugins');
            if (installed) {
                this.installedPlugins = new Set(JSON.parse(installed));
                
                // Update plugins installed status
                this.plugins.forEach(plugin => {
                    plugin.installed = this.installedPlugins.has(plugin.id);
                });
            }
        } catch (error) {
            this.logger.error('Failed to load installed plugins:', error);
        }
    }

    async installPlugin(pluginId: string): Promise<{ success: boolean; error?: string }> {
        try {
            const plugin = this.plugins.find(p => p.id === pluginId);
            if (!plugin) {
                return { success: false, error: 'Plugin not found' };
            }

            if (!plugin.compatible) {
                return { success: false, error: 'Plugin not compatible with your system' };
            }

            this.logger.info(`Installing plugin: ${plugin.name}`);

            // Simulate installation process
            await this.simulateInstallation(plugin);

            // Mark as installed
            this.installedPlugins.add(pluginId);
            plugin.installed = true;

            // Save to storage
            this.saveInstalledPlugins();

            // Notify main process
            await window.electronAPI.processAIRequest({
                type: 'plugin_installed',
                pluginId,
                pluginName: plugin.name
            });

            this.logger.info(`Plugin installed successfully: ${plugin.name}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to install plugin ${pluginId}:`, error);
            return { success: false, error: error.message };
        }
    }

    async uninstallPlugin(pluginId: string): Promise<{ success: boolean; error?: string }> {
        try {
            const plugin = this.plugins.find(p => p.id === pluginId);
            if (!plugin) {
                return { success: false, error: 'Plugin not found' };
            }

            this.logger.info(`Uninstalling plugin: ${plugin.name}`);

            // Simulate uninstallation process
            await this.simulateUninstallation(plugin);

            // Remove from installed set
            this.installedPlugins.delete(pluginId);
            plugin.installed = false;

            // Save to storage
            this.saveInstalledPlugins();

            // Notify main process
            await window.electronAPI.processAIRequest({
                type: 'plugin_uninstalled',
                pluginId,
                pluginName: plugin.name
            });

            this.logger.info(`Plugin uninstalled successfully: ${plugin.name}`);
            return { success: true };

        } catch (error) {
            this.logger.error(`Failed to uninstall plugin ${pluginId}:`, error);
            return { success: false, error: error.message };
        }
    }

    private async simulateInstallation(plugin: Plugin): Promise<void> {
        // Simulate download and installation time
        return new Promise(resolve => {
            setTimeout(resolve, 2000 + Math.random() * 3000);
        });
    }

    private async simulateUninstallation(plugin: Plugin): Promise<void> {
        // Simulate uninstallation time
        return new Promise(resolve => {
            setTimeout(resolve, 1000 + Math.random() * 2000);
        });
    }

    private saveInstalledPlugins(): void {
        localStorage.setItem('installedPlugins', JSON.stringify([...this.installedPlugins]));
    }

    searchPlugins(query: string, category?: string, installedOnly: boolean = false): Plugin[] {
        let results = this.plugins;

        // Filter by search query
        if (query) {
            const lowerQuery = query.toLowerCase();
            results = results.filter(plugin => 
                plugin.name.toLowerCase().includes(lowerQuery) ||
                plugin.description.toLowerCase().includes(lowerQuery) ||
                plugin.tags.some(tag => tag.toLowerCase().includes(lowerQuery)) ||
                plugin.author.toLowerCase().includes(lowerQuery)
            );
        }

        // Filter by category
        if (category && category !== 'all') {
            results = results.filter(plugin => plugin.category === category);
        }

        // Filter by installed status
        if (installedOnly) {
            results = results.filter(plugin => plugin.installed);
        }

        return results;
    }

    getCategories(): string[] {
        return this.categories;
    }

    getInstalledPlugins(): Plugin[] {
        return this.plugins.filter(plugin => plugin.installed);
    }

    getFeaturedPlugins(): Plugin[] {
        return this.plugins
            .filter(plugin => plugin.rating >= 4.5)
            .sort((a, b) => b.downloads - a.downloads)
            .slice(0, 6);
    }

    getPopularPlugins(): Plugin[] {
        return this.plugins
            .sort((a, b) => b.downloads - a.downloads)
            .slice(0, 12);
    }
}

export class PluginMarketplaceUI {
    private marketplace: PluginsMarketplace;
    private currentView: string = 'featured';
    private currentCategory: string = 'all';
    private searchQuery: string = '';

    constructor() {
        this.marketplace = new PluginsMarketplace();
        this.initializeUI();
    }

    private initializeUI(): void {
        this.renderMarketplace();
        this.setupEventListeners();
    }

    private renderMarketplace(): void {
        const pluginsTab = document.getElementById('plugins');
        if (!pluginsTab) return;

        pluginsTab.innerHTML = `
            <div class="plugins-marketplace">
                <div class="plugins-header">
                    <h2>Plugin Marketplace</h2>
                    <div class="plugins-controls">
                        <div class="search-box">
                            <input type="text" id="pluginSearch" placeholder="Search plugins..." class="search-input">
                            <span class="search-icon">🔍</span>
                        </div>
                        <div class="view-controls">
                            <button class="view-btn ${this.currentView === 'featured' ? 'active' : ''}" data-view="featured">
                                Featured
                            </button>
                            <button class="view-btn ${this.currentView === 'popular' ? 'active' : ''}" data-view="popular">
                                Popular
                            </button>
                            <button class="view-btn ${this.currentView === 'installed' ? 'active' : ''}" data-view="installed">
                                Installed
                            </button>
                        </div>
                    </div>
                </div>

                <div class="plugins-filters">
                    <div class="category-filter">
                        <label>Category:</label>
                        <select id="categoryFilter" class="filter-select">
                            <option value="all">All Categories</option>
                            ${this.marketplace.getCategories().map(cat => 
                                `<option value="${cat}" ${this.currentCategory === cat ? 'selected' : ''}>${cat}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="stats">
                        <span class="stat-item">
                            <strong>${this.marketplace.getInstalledPlugins().length}</strong> installed
                        </span>
                        <span class="stat-item">
                            <strong>${this.marketplace.plugins.length}</strong> available
                        </span>
                    </div>
                </div>

                <div class="plugins-grid" id="pluginsGrid">
                    <!-- Plugins will be rendered here -->
                </div>

                <div class="plugins-footer">
                    <p>Can't find what you're looking for? <a href="#" id="developPlugin">Develop your own plugin</a></p>
                </div>
            </div>
        `;

        this.renderPluginsGrid();
    }

    private renderPluginsGrid(): void {
        const pluginsGrid = document.getElementById('pluginsGrid');
        if (!pluginsGrid) return;

        let plugins: Plugin[] = [];

        switch (this.currentView) {
            case 'featured':
                plugins = this.marketplace.getFeaturedPlugins();
                break;
            case 'popular':
                plugins = this.marketplace.getPopularPlugins();
                break;
            case 'installed':
                plugins = this.marketplace.getInstalledPlugins();
                break;
            default:
                plugins = this.marketplace.searchPlugins(this.searchQuery, this.currentCategory);
        }

        if (plugins.length === 0) {
            pluginsGrid.innerHTML = `
                <div class="no-plugins">
                    <div class="no-plugins-icon">🔍</div>
                    <h3>No plugins found</h3>
                    <p>Try adjusting your search or filters</p>
                </div>
            `;
            return;
        }

        pluginsGrid.innerHTML = plugins.map(plugin => this.renderPluginCard(plugin)).join('');
    }

    private renderPluginCard(plugin: Plugin): string {
        return `
            <div class="plugin-card ${plugin.installed ? 'installed' : ''} ${plugin.official ? 'official' : ''}">
                <div class="plugin-header">
                    <div class="plugin-icon">${plugin.icon || '🔌'}</div>
                    <div class="plugin-info">
                        <h3 class="plugin-name">${plugin.name}</h3>
                        <div class="plugin-meta">
                            <span class="plugin-version">v${plugin.version}</span>
                            <span class="plugin-author">by ${plugin.author}</span>
                            ${plugin.official ? '<span class="official-badge">Official</span>' : ''}
                        </div>
                    </div>
                </div>

                <div class="plugin-description">
                    ${plugin.description}
                </div>

                <div class="plugin-tags">
                    ${plugin.tags.map(tag => `<span class="plugin-tag">${tag}</span>`).join('')}
                </div>

                <div class="plugin-stats">
                    <div class="plugin-rating">
                        <span class="rating-stars">${'⭐'.repeat(Math.floor(plugin.rating))}${plugin.rating % 1 >= 0.5 ? '½' : ''}</span>
                        <span class="rating-value">${plugin.rating.toFixed(1)}</span>
                    </div>
                    <div class="plugin-downloads">
                        📥 ${this.formatDownloads(plugin.downloads)}
                    </div>
                    <div class="plugin-category">
                        ${plugin.category}
                    </div>
                </div>

                <div class="plugin-actions">
                    ${plugin.price > 0 ? 
                        `<span class="plugin-price">$${plugin.price.toFixed(2)}</span>` : 
                        '<span class="plugin-price free">Free</span>'
                    }
                    <button class="btn ${plugin.installed ? 'btn-secondary' : 'btn-primary'} plugin-action-btn" 
                            data-plugin-id="${plugin.id}" 
                            data-action="${plugin.installed ? 'uninstall' : 'install'}">
                        ${plugin.installed ? 'Uninstall' : 'Install'}
                    </button>
                </div>

                ${!plugin.compatible ? 
                    '<div class="compatibility-warning">⚠️ Not compatible with your system</div>' : 
                    ''
                }
            </div>
        `;
    }

    private setupEventListeners(): void {
        // Search functionality
        const searchInput = document.getElementById('pluginSearch') as HTMLInputElement;
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = (e.target as HTMLInputElement).value;
                this.currentView = 'search';
                this.renderPluginsGrid();
            });
        }

        // View controls
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = (e.target as HTMLElement).getAttribute('data-view');
                if (view) {
                    this.currentView = view;
                    this.updateActiveView();
                    this.renderPluginsGrid();
                }
            });
        });

        // Category filter
        const categoryFilter = document.getElementById('categoryFilter') as HTMLSelectElement;
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.currentCategory = (e.target as HTMLSelectElement).value;
                this.renderPluginsGrid();
            });
        }

        // Plugin action buttons
        document.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('plugin-action-btn')) {
                const pluginId = target.getAttribute('data-plugin-id');
                const action = target.getAttribute('data-action');
                
                if (pluginId && action) {
                    this.handlePluginAction(pluginId, action);
                }
            }
        });

        // Develop plugin link
        const developLink = document.getElementById('developPlugin');
        if (developLink) {
            developLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showDevelopmentInfo();
            });
        }
    }

    private updateActiveView(): void {
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = document.querySelector(`[data-view="${this.currentView}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    }

    private async handlePluginAction(pluginId: string, action: string): Promise<void> {
        const button = document.querySelector(`[data-plugin-id="${pluginId}"]`) as HTMLButtonElement;
        if (!button) return;

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = action === 'install' ? 'Installing...' : 'Uninstalling...';

        try {
            let result;
            if (action === 'install') {
                result = await this.marketplace.installPlugin(pluginId);
            } else {
                result = await this.marketplace.uninstallPlugin(pluginId);
            }

            if (result.success) {
                // Update the UI
                this.renderPluginsGrid();
            } else {
                alert(`Failed to ${action} plugin: ${result.error}`);
                button.textContent = originalText;
                button.disabled = false;
            }

        } catch (error) {
            alert(`Error: ${error.message}`);
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    private showDevelopmentInfo(): void {
        // Show plugin development information
        alert(`Plugin Development Kit Coming Soon!\n\nWe're working on a comprehensive SDK for plugin development. Stay tuned for updates!`);
    }

    private formatDownloads(downloads: number): string {
        if (downloads >= 1000000) {
            return (downloads / 1000000).toFixed(1) + 'M';
        } else if (downloads >= 1000) {
            return (downloads / 1000).toFixed(1) + 'K';
        }
        return downloads.toString();
    }
}

// Add plugin marketplace styles
const pluginStyles = `
.plugins-marketplace {
    max-width: 1200px;
    margin: 0 auto;
}

.plugins-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
}

.plugins-controls {
    display: flex;
    gap: 16px;
    align-items: center;
}

.search-box {
    position: relative;
}

.search-input {
    padding: 8px 12px 8px 36px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    width: 250px;
}

.search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #64748b;
}

.view-controls {
    display: flex;
    background: #f1f5f9;
    border-radius: 6px;
    padding: 4px;
}

.view-btn {
    padding: 6px 12px;
    border: none;
    background: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.view-btn.active {
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.plugins-filters {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 16px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}

.category-filter {
    display: flex;
    align-items: center;
    gap: 8px;
}

.filter-select {
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
}

.stats {
    display: flex;
    gap: 16px;
}

.stat-item {
    color: #64748b;
    font-size: 14px;
}

.plugins-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
}

.plugin-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px;
    transition: all 0.2s ease;
}

.plugin-card:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.plugin-card.installed {
    border-left: 4px solid #10b981;
}

.plugin-card.official {
    border-top: 2px solid #3b82f6;
}

.plugin-header {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
}

.plugin-icon {
    font-size: 24px;
    width: 40px;
    height: 40px;
    background: #f1f5f9;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.plugin-info {
    flex: 1;
}

.plugin-name {
    margin: 0 0 4px 0;
    font-size: 16px;
    color: #1e293b;
}

.plugin-meta {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 12px;
    color: #64748b;
}

.official-badge {
    background: #3b82f6;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
}

.plugin-description {
    color: #475569;
    font-size: 14px;
    line-height: 1.4;
    margin-bottom: 12px;
}

.plugin-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
}

.plugin-tag {
    background: #f1f5f9;
    color: #475569;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
}

.plugin-stats {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 12px 0;
    border-top: 1px solid #f1f5f9;
    border-bottom: 1px solid #f1f5f9;
    font-size: 12px;
    color: #64748b;
}

.plugin-rating {
    display: flex;
    align-items: center;
    gap: 4px;
}

.rating-stars {
    font-size: 10px;
}

.plugin-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.plugin-price {
    font-weight: 600;
    color: #1e293b;
}

.plugin-price.free {
    color: #10b981;
}

.plugin-action-btn {
    padding: 6px 12px;
    font-size: 12px;
}

.compatibility-warning {
    background: #fef3c7;
    color: #92400e;
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-top: 8px;
    text-align: center;
}

.no-plugins {
    text-align: center;
    padding: 60px 20px;
    color: #64748b;
}

.no-plugins-icon {
    font-size: 48px;
    margin-bottom: 16px;
}

.plugins-footer {
    text-align: center;
    padding: 20px;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
}

.plugins-footer a {
    color: #3b82f6;
    text-decoration: none;
}

.plugins-footer a:hover {
    text-decoration: underline;
}
`;

// Add styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = pluginStyles;
document.head.appendChild(styleSheet);

// Initialize plugin marketplace when plugins tab is activated
export const initializePluginsMarketplace = () => {
    new PluginMarketplaceUI();
};
