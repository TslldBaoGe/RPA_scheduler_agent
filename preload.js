const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  startAgent: () => ipcRenderer.invoke('start-agent'),
  stopAgent: () => ipcRenderer.invoke('stop-agent'),
  getStatus: () => ipcRenderer.invoke('get-status'),
  clearLog: () => ipcRenderer.invoke('clear-log'),
  
  onLog: (callback) => {
    ipcRenderer.on('log', (event, message) => callback(message))
  },
  
  onStatus: (callback) => {
    ipcRenderer.on('status', (event, status) => callback(status))
  },
  
  onInfo: (callback) => {
    ipcRenderer.on('info', (event, info) => callback(info))
  },
  
  onClearLog: (callback) => {
    ipcRenderer.on('clear-log', () => callback())
  },
  
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel)
  }
})
