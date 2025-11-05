import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
    // Unified AI processing
    processAI: (prompt: string, context?: any) => 
        ipcRenderer.invoke('ai:process', prompt, context),
    
    // Voice processing
    processVoiceCommand: (audioData: ArrayBuffer, language?: string) => 
        ipcRenderer.invoke('voice:process', audioData, language),
    
    // Text-to-speech
    synthesizeSpeech: (text: string, voice?: string) => 
        ipcRenderer.invoke('voice:synthesize', text, voice),
    
    // System commands
    executeSystemCommand: (command: string, parameters?: any) => 
        ipcRenderer.invoke('system:execute', command, parameters),
    
    // Service status
    getServiceStatus: () => ipcRenderer.invoke('services:status'),
    
    // System integration (from core engine)
    openApplication: (appName: string) => 
        ipcRenderer.invoke('system:open-app', appName),
    
    getSystemInfo: () => ipcRenderer.invoke('system:get-info'),
    
    // File operations (from core engine)
    searchFiles: (directory: string, pattern: string) => 
        ipcRenderer.invoke('files:search', directory, pattern)
});
