const WebSocket = require('ws')
const { v4: uuidv4 } = require('uuid')
const EventEmitter = require('events')
const os = require('os')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const SERVER_URL = 'ws://120.79.224.20/ws/agent'
const RECONNECT_INTERVAL = 5000

class AgentCore extends EventEmitter {
  constructor() {
    super()
    this.agentId = null
    this.agentName = null
    this.isRunning = false
    this.connected = false
    this.ws = null
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.runningProcesses = new Map()
  }

  start() {
    if (this.isRunning) return
    
    this.loadConfig()
    this.isRunning = true
    this.connect()
    
    this.emit('log', `启动 Agent: ${this.agentName}`)
    this.emit('log', `连接服务器: ${SERVER_URL}`)
    this.emit('status', { isRunning: true, connected: false })
  }

  stop() {
    this.isRunning = false
    this.disconnect()
    this.terminateAllProcesses()
    
    this.emit('log', 'Agent 已停止')
    this.emit('status', { isRunning: false, connected: false })
  }

  loadConfig() {
    const configPath = path.join(process.cwd(), 'agent_config.json')
    
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'))
      this.agentId = config.agent_id
      this.agentName = config.agent_name
    }
    
    if (!this.agentId) {
      this.agentId = uuidv4()
      this.agentName = `Agent-${os.hostname()}`
      
      fs.writeFileSync(configPath, JSON.stringify({
        agent_id: this.agentId,
        agent_name: this.agentName,
        created_at: new Date().toISOString()
      }, null, 2))
    }
    
    this.emit('info', {
      agentId: this.agentId,
      agentName: this.agentName,
      hostname: os.hostname(),
      platform: process.platform
    })
  }

  connect() {
    if (!this.isRunning) return
    
    this.emit('log', '正在连接...')
    
    try {
      this.ws = new WebSocket(SERVER_URL)
      
      this.ws.on('open', () => {
        this.connected = true
        this.emit('log', '已连接到服务器')
        this.emit('status', { isRunning: true, connected: true })
        
        this.ws.send(JSON.stringify({
          type: 'register',
          agent: {
            agent_id: this.agentId,
            agent_name: this.agentName,
            hostname: os.hostname(),
            platform: process.platform,
            pid: process.pid
          }
        }))
        
        this.emit('log', '已注册到服务器')
        this.startHeartbeat()
      })
      
      this.ws.on('message', (data) => {
        this.handleMessage(data)
      })
      
      this.ws.on('close', () => {
        this.handleDisconnect()
      })
      
      this.ws.on('error', (error) => {
        this.emit('log', `连接错误: ${error.message}`)
        this.handleDisconnect()
      })
      
    } catch (error) {
      this.emit('log', `连接失败: ${error.message}`)
      this.scheduleReconnect()
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
  }

  handleDisconnect() {
    this.connected = false
    this.emit('log', `连接断开，${RECONNECT_INTERVAL / 1000}秒后重连...`)
    this.emit('status', { isRunning: true, connected: false })
    this.scheduleReconnect()
  }

  scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    
    this.reconnectTimer = setTimeout(() => {
      if (this.isRunning) {
        this.connect()
      }
    }, RECONNECT_INTERVAL)
  }

  startHeartbeat() {
    this.stopHeartbeat()
    
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.connected) {
        this.ws.send(JSON.stringify({
          type: 'ping',
          agent_id: this.agentId,
          timestamp: new Date().toISOString()
        }))
      }
    }, 120000)
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  handleMessage(data) {
    try {
      const message = JSON.parse(data.toString())
      const { type } = message
      
      switch (type) {
        case 'execute':
          this.executeCommand(message)
          break
        case 'terminate':
          this.terminateExecution(message)
          break
        case 'pong':
          break
        case 'shutdown':
          this.handleShutdown()
          break
      }
    } catch (error) {
      this.emit('log', `消息处理错误: ${error.message}`)
    }
  }

  executeCommand(message) {
    const { cmd, timeout = 300, task_id, execution_id } = message
    
    this.emit('log', `执行任务: ${task_id}`)
    this.emit('log', `命令: ${cmd}`)
    
    const processInfo = {
      terminated: false,
      startTime: Date.now(),
      timeout
    }
    
    const childProcess = spawn(cmd, [], {
      shell: true,
      cwd: process.cwd(),
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    })
    
    processInfo.process = childProcess
    this.runningProcesses.set(execution_id, processInfo)
    
    let stdout = ''
    let stderr = ''
    
    childProcess.stdout.on('data', (data) => {
      stdout += data.toString()
    })
    
    childProcess.stderr.on('data', (data) => {
      stderr += data.toString()
    })
    
    const timeoutTimer = setTimeout(() => {
      processInfo.terminated = true
      this.killProcess(childProcess)
    }, timeout * 1000)
    
    childProcess.on('close', (code) => {
      clearTimeout(timeoutTimer)
      this.runningProcesses.delete(execution_id)
      
      const duration = (Date.now() - processInfo.startTime) / 1000
      const status = processInfo.terminated ? 'terminated' : (code === 0 ? 'success' : 'error')
      
      this.sendResult(task_id, execution_id, {
        status,
        returncode: code,
        stdout,
        stderr,
        execution_time: new Date().toISOString(),
        duration: this.formatDuration(duration)
      })
      
      this.emit('log', `任务完成: ${task_id} - ${status}`)
    })
  }

  terminateExecution(message) {
    const { execution_id } = message
    
    this.emit('log', `收到终止命令: ${execution_id}`)
    
    const processInfo = this.runningProcesses.get(execution_id)
    if (processInfo) {
      processInfo.terminated = true
      this.killProcess(processInfo.process)
      
      this.ws.send(JSON.stringify({
        type: 'terminate_ack',
        agent_id: this.agentId,
        execution_id,
        success: true
      }))
    } else {
      this.ws.send(JSON.stringify({
        type: 'terminate_ack',
        agent_id: this.agentId,
        execution_id,
        success: false
      }))
    }
  }

  killProcess(proc) {
    if (proc && proc.pid) {
      try {
        if (process.platform === 'win32') {
          spawn('taskkill', ['/F', '/T', '/PID', proc.pid.toString()])
        } else {
          proc.kill('SIGTERM')
        }
      } catch (error) {
        this.emit('log', `终止进程失败: ${error.message}`)
      }
    }
  }

  terminateAllProcesses() {
    for (const [executionId, processInfo] of this.runningProcesses) {
      processInfo.terminated = true
      this.killProcess(processInfo.process)
    }
    this.runningProcesses.clear()
  }

  sendResult(taskId, executionId, result) {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({
        type: 'execution_result',
        agent_id: this.agentId,
        task_id: taskId,
        execution_id: executionId,
        result
      }))
    }
  }

  handleShutdown() {
    this.emit('log', '收到关闭命令')
    this.stop()
  }

  formatDuration(seconds) {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    
    const parts = []
    if (h > 0) parts.push(`${h}时`)
    if (m > 0) parts.push(`${m}分`)
    if (s > 0 || parts.length === 0) parts.push(`${s}秒`)
    
    return parts.join('')
  }
}

module.exports = AgentCore
