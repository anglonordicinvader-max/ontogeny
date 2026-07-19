const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
  getBlenderPort: () => ipcRenderer.invoke('get-backend-port').then(p => p + 1),
  getMuJoCoPort: () => ipcRenderer.invoke('get-backend-port').then(p => p + 2),
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close')
});
