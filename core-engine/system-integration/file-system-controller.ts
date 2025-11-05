// core-engine/system-integration/file-system-controller.ts
import { promises as fs } from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface SearchResult {
  path: string;
  name: string;
  size: number;
  modified: Date;
  type: string;
  relevance?: number;
}

export class FileSystemController {
  private recentFiles: string[] = [];
  private readonly MAX_RECENT_FILES = 20;

  // File search with multiple criteria
  async searchFiles(query: string, options: {
    directory?: string;
    fileTypes?: string[];
    maxResults?: number;
    contentSearch?: boolean;
  } = {}): Promise<SearchResult[]> {
    const {
      directory = process.cwd(),
      fileTypes = [],
      maxResults = 50,
      contentSearch = false
    } = options;

    let results: SearchResult[] = [];

    if (contentSearch) {
      results = await this.searchFileContent(query, directory, fileTypes);
    } else {
      results = await this.searchFileNames(query, directory, fileTypes);
    }

    // Sort by relevance and limit results
    return results
      .sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
      .slice(0, maxResults);
  }

  // File operations
  async performFileOperation(operation: string, source: string, destination?: string): Promise<string> {
    switch (operation) {
      case 'copy':
        await fs.copyFile(source, destination);
        return `Copied ${source} to ${destination}`;
      
      case 'move':
        await fs.rename(source, destination);
        return `Moved ${source} to ${destination}`;
      
      case 'delete':
        await fs.unlink(source);
        return `Deleted ${source}`;
      
      case 'backup':
        const backupPath = await this.createBackup(source);
        return `Backed up ${source} to ${backupPath}`;
      
      default:
        throw new Error(`Unsupported operation: ${operation}`);
    }
  }

  // Content search using grep/ripgrep
  async searchFileContent(searchTerm: string, directory: string, fileTypes: string[] = []): Promise<SearchResult[]> {
    const fileTypeFilter = fileTypes.length > 0 ? `-g "*.{${fileTypes.join(',')}}"` : '';
    
    try {
      // Using ripgrep for fast content search
      const { stdout } = await execAsync(
        `rg --files-with-matches --ignore-case ${fileTypeFilter} "${searchTerm}" "${directory}"`
      );

      const filePaths = stdout.split('\n').filter(Boolean);
      const results: SearchResult[] = [];

      for (const filePath of filePaths.slice(0, 50)) {
        const stat = await fs.stat(filePath);
        results.push({
          path: filePath,
          name: path.basename(filePath),
          size: stat.size,
          modified: stat.mtime,
          type: path.extname(filePath),
          relevance: await this.calculateRelevance(filePath, searchTerm)
        });
      }

      return results;
    } catch (error) {
      // Fallback to manual search if ripgrep not available
      return this.manualContentSearch(searchTerm, directory, fileTypes);
    }
  }

  // Quick access to recent files
  async getRecentFiles(type?: string): Promise<SearchResult[]> {
    const validFiles = await this.validateRecentFiles();
    
    if (type) {
      return validFiles.filter(file => 
        file.type.toLowerCase() === type.toLowerCase()
      );
    }
    
    return validFiles;
  }

  async openRecentFile(index: number): Promise<void> {
    const recentFiles = await this.getRecentFiles();
    if (index < 0 || index >= recentFiles.length) {
      throw new Error('Invalid file index');
    }

    const filePath = recentFiles[index].path;
    this.openFile(filePath);
  }

  private async searchFileNames(query: string, directory: string, fileTypes: string[]): Promise<SearchResult[]> {
    const results: SearchResult[] = [];
    
    async function searchRecursive(dir: string): Promise<void> {
      try {
        const items = await fs.readdir(dir);
        
        for (const item of items) {
          const fullPath = path.join(dir, item);
          
          try {
            const stat = await fs.stat(fullPath);
            
            if (stat.isDirectory()) {
              await searchRecursive(fullPath);
            } else if (this.matchesSearch(item, query, fileTypes)) {
              results.push({
                path: fullPath,
                name: item,
                size: stat.size,
                modified: stat.mtime,
                type: path.extname(item),
                relevance: this.calculateNameRelevance(item, query)
              });
            }
          } catch (error) {
            // Skip files we can't access
            continue;
          }
        }
      } catch (error) {
        console.error(`Error reading directory ${dir}:`, error);
      }
    }
    
    await searchRecursive.call(this, directory);
    return results;
  }

  private matchesSearch(filename: string, query: string, fileTypes: string[]): boolean {
    const matchesName = filename.toLowerCase().includes(query.toLowerCase());
    const matchesType = fileTypes.length === 0 || 
      fileTypes.some(type => filename.toLowerCase().endsWith(type.toLowerCase()));
    
    return matchesName && matchesType;
  }

  private calculateNameRelevance(filename: string, query: string): number {
    const lowerFilename = filename.toLowerCase();
    const lowerQuery = query.toLowerCase();
    
    let relevance = 0;
    
    // Exact match gets highest score
    if (lowerFilename === lowerQuery) relevance += 100;
    
    // Starts with query
    if (lowerFilename.startsWith(lowerQuery)) relevance += 50;
    
    // Contains query
    if (lowerFilename.includes(lowerQuery)) relevance += 25;
    
    // File extension match
    if (path.extname(filename)) relevance += 10;
    
    return relevance;
  }

  private async openFile(filePath: string): Promise<void> {
    // Platform-specific file opening
    const command = process.platform === 'win32' 
      ? `start "" "${filePath}"`
      : process.platform === 'darwin'
      ? `open "${filePath}"`
      : `xdg-open "${filePath}"`;
    
    await execAsync(command);
    this.addToRecentFiles(filePath);
  }

  private addToRecentFiles(filePath: string): void {
    this.recentFiles = this.recentFiles.filter(f => f !== filePath);
    this.recentFiles.unshift(filePath);
    
    if (this.recentFiles.length > this.MAX_RECENT_FILES) {
      this.recentFiles = this.recentFiles.slice(0, this.MAX_RECENT_FILES);
    }
  }
}
