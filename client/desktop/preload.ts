import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Voice control
  startListening: () => ipcRenderer.invoke('voice:start-listening'),
  stopListening: () => ipcRenderer.invoke('voice:stop-listening'),

  // AI processing
  processAIRequest: (request: any) => ipcRenderer.invoke('ai:process-request', request),

  // System control
  openApplication: (appName: string) => ipcRenderer.invoke('system:open-app', appName),
  getSystemInfo: () => ipcRenderer.invoke('system:get-info'),

  // Window control
  toggleMainWindow: () => ipcRenderer.invoke('window:toggle-main'),
  setFloatingPosition: (x: number, y: number) => ipcRenderer.invoke('window:set-floating-position', x, y),

  // Event listeners
  onVoiceActivity: (callback: (event: any, data: any) => void) => 
    ipcRenderer.on('voice:activity', callback),
  
  onAIResponse: (callback: (event: any, data: any) => void) => 
    ipcRenderer.on('ai:response', callback)
});

// Type definitions for the exposed API
declare global {
  interface Window {
    electronAPI: {
      startListening: () => Promise<any>;
      stopListening: () => Promise<any>;
      processAIRequest: (request: any) => Promise<any>;
      openApplication: (appName: string) => Promise<any>;
      getSystemInfo: () => Promise<any>;
      toggleMainWindow: () => Promise<any>;
      setFloatingPosition: (x: number, y: number) => Promise<any>;
      onVoiceActivity: (callback: (event: any, data: any) => void) => void;
      onAIResponse: (callback: (event: any, data: any) => void) => void;
    };
  }
}
