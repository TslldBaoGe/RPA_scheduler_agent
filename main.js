const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain } = require('electron')
const path = require('path')
const AgentCore = require('./agent-core')

let mainWindow = null
let tray = null
let agent = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 600,
    height: 500,
    minWidth: 500,
    minHeight: 400,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    icon: path.join(__dirname, 'renderer', 'icon.png'),
    show: false,
    autoHideMenuBar: true
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function createTray() {
  const iconPath = path.join(__dirname, 'renderer', 'icon.png')
  const trayIcon = nativeImage.createFromPath(iconPath)
  
  tray = new Tray(trayIcon.resize({ width: 16, height: 16 }))
  
  const contextMenu = Menu.buildFromTemplate([
    { label: '显示窗口', click: () => mainWindow && mainWindow.show() },
    { label: '启动 Agent', click: () => startAgent() },
    { label: '停止 Agent', click: () => stopAgent() },
    { type: 'separator' },
    { label: '退出', click: () => quitApp() }
  ])
  
  tray.setToolTip('RPA Agent')
  tray.setContextMenu(contextMenu)
  
  tray.on('double-click', () => {
    mainWindow && mainWindow.show()
  })
}

function startAgent() {
  if (agent && agent.isRunning) return
  
  agent = new AgentCore()
  
  agent.on('log', (message) => {
    if (mainWindow) {
      mainWindow.webContents.send('log', message)
    }
  })
  
  agent.on('status', (status) => {
    if (mainWindow) {
      mainWindow.webContents.send('status', status)
    }
    if (tray) {
      tray.setToolTip(`RPA Agent - ${status.connected ? '已连接' : '未连接'}`)
    }
  })
  
  agent.on('info', (info) => {
    if (mainWindow) {
      mainWindow.webContents.send('info', info)
    }
  })
  
  agent.start()
}

function stopAgent() {
  if (agent) {
    agent.stop()
    agent = null
  }
}

function quitApp() {
  app.isQuitting = true
  stopAgent()
  tray && tray.destroy()
  app.quit()
}

app.whenReady().then(() => {
  createWindow()
  createTray()
  
  ipcMain.handle('start-agent', () => {
    startAgent()
    return true
  })
  
  ipcMain.handle('stop-agent', () => {
    stopAgent()
    return true
  })
  
  ipcMain.handle('get-status', () => {
    if (agent) {
      return {
        isRunning: agent.isRunning,
        connected: agent.connected
      }
    }
    return { isRunning: false, connected: false }
  })
  
  ipcMain.handle('clear-log', () => {
    if (mainWindow) {
      mainWindow.webContents.send('clear-log')
    }
    return true
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    quitApp()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

app.on('before-quit', () => {
  app.isQuitting = true
})
