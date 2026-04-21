const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aiBackend', {
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
  setOrbStatus: (status) => ipcRenderer.send('set-orb-status', status)
});
