const { contextBridge, ipcRenderer } = require('electron');

const backendPort = ipcRenderer.sendSync('get-backend-port') || 8000;
const baseUrl = `http://127.0.0.1:${backendPort}`;
const wsUrl = `ws://127.0.0.1:${backendPort}`;

contextBridge.exposeInMainWorld('aiBackend', {
  port: backendPort,
  baseUrl: baseUrl,
  wsUrl: wsUrl,

  // Settings API
  getSettingsSync: () => ipcRenderer.sendSync('get-settings-sync'),
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),

  ask: (requestData) => ipcRenderer.invoke('ask-ai', requestData),
  askStream: (requestData) => ipcRenderer.send('ask-ai-stream', requestData),
  stopStream: () => ipcRenderer.send('abort-ai-stream'),
  onStreamToken: (callback) => {
    ipcRenderer.removeAllListeners('ai-stream-token');
    ipcRenderer.on('ai-stream-token', (event, data) => callback(data));
  },
  onStreamError: (callback) => {
    ipcRenderer.removeAllListeners('ai-stream-error');
    ipcRenderer.on('ai-stream-error', (event, err) => callback(err));
  },
  toggleMainWindow: () => ipcRenderer.send('toggle-main-window'),
  openSettings: () => ipcRenderer.send('open-settings-window'),
  closeSettings: () => ipcRenderer.send('close-settings-window'),
  hideOrb: () => ipcRenderer.send('hide-orb-window'),
  showOrb: () => ipcRenderer.send('show-orb-window'),
  setOrbStatus: (status) => ipcRenderer.send('set-orb-status', status),
  onVoiceTrigger: (callback) => ipcRenderer.on('trigger-voice-listen', () => callback()),
  notifySettingsUpdated: (data) => ipcRenderer.send('settings-updated', data),
  onSettingsUpdated: (callback) => {
    ipcRenderer.removeAllListeners('refresh-settings');
    ipcRenderer.on('refresh-settings', (event, data) => callback(data));
  },
  triggerAction: (action) => ipcRenderer.send('trigger-action', action),
  resizeOrbWindow: (width, height) => ipcRenderer.send('resize-orb-window', { width, height }),
  onWindowResized: (callback) => {
    ipcRenderer.removeAllListeners('window-resized');
    ipcRenderer.on('window-resized', () => callback());
  },
  onTriggerAction: (callback) => {
    ipcRenderer.removeAllListeners('execute-action');
    ipcRenderer.on('execute-action', (event, action) => callback(action));
  },
  // Persona APIs
  getPersonas: () => ipcRenderer.invoke('persona-get-all'),
  getActivePersona: () => ipcRenderer.invoke('persona-get-active'),
  setActivePersona: (id) => ipcRenderer.invoke('persona-set-active', id),
  savePersona: (persona) => ipcRenderer.invoke('persona-save', persona),
  deletePersona: (id) => ipcRenderer.invoke('persona-delete', id),
  runCommand: (cmd) => ipcRenderer.invoke('run-command', cmd)
});
