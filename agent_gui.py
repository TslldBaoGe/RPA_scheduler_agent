#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cron Scheduler Agent - GUI Version
本地代理程序，连接服务器接收指令并在本地执行
"""
import asyncio
import websockets
import json
import subprocess
import sys
import os
import uuid
import threading
import time
import queue
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkinter import font as tkfont

# 配置
SERVER_URL = "ws://rpa.tslldtslldtslld.top/ws/agent"
AGENT_ID = None
AGENT_NAME = None
RECONNECT_INTERVAL = 5

# 正在执行的任务
running_processes = {}

# 日志队列
log_queue = queue.Queue()


def log(message):
    """添加日志到队列"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_queue.put(f"[{timestamp}] {message}")


def get_agent_info():
    global AGENT_ID, AGENT_NAME
    
    config_file = "agent_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            AGENT_ID = config.get("agent_id")
            AGENT_NAME = config.get("agent_name")
    
    if not AGENT_ID:
        AGENT_ID = str(uuid.uuid4())
        AGENT_NAME = f"Agent-{os.environ.get('COMPUTERNAME', 'Unknown')}"
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({
                "agent_id": AGENT_ID,
                "agent_name": AGENT_NAME,
                "created_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
    
    return {
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "hostname": os.environ.get("COMPUTERNAME", "Unknown"),
        "platform": sys.platform,
        "pid": os.getpid()
    }


def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0 or (hours == 0 and minutes == 0):
        parts.append(f"{secs}秒")
    
    return "".join(parts) if parts else "0秒"


def kill_process_tree(pid):
    """终止进程及其所有子进程"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            timeout=10
        )
        return True
    except Exception as e:
        log(f"终止进程失败: {e}")
        return False


class StreamOutput:
    """实时捕获流输出"""
    def __init__(self, stream):
        self.stream = stream
        self.lines = []
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
    
    def _read_loop(self):
        try:
            while True:
                line = self.stream.readline()
                if not line:
                    break
                with self.lock:
                    self.lines.append(line)
        except Exception as e:
            pass
        finally:
            self.finished.set()
    
    def get_output(self):
        with self.lock:
            return "".join(self.lines)
    
    def wait(self, timeout=None):
        self.finished.wait(timeout)


async def execute_command_async(cmd, timeout, websocket, task_id, execution_id):
    """异步执行命令"""
    start_time = datetime.now()
    global running_processes
    
    work_dir = None
    import re
    python_match = re.search(r'(?:python|python\.exe)\s+["\']?([^\s"\']+\.py)["\']?', cmd, re.IGNORECASE)
    if python_match:
        script_path = python_match.group(1).strip('"\'')
        if os.path.exists(script_path):
            work_dir = os.path.dirname(os.path.abspath(script_path))
    
    clean_env = os.environ.copy()
    clean_env['PYTHONUNBUFFERED'] = '1'
    clean_env['PYTHONIOENCODING'] = 'utf-8'
    
    if re.search(r'python\.exe["\']?\s+', cmd, re.IGNORECASE) and '-u' not in cmd:
        cmd = re.sub(r'(python\.exe["\']?)\s+', r'\1 -u ', cmd, count=1, flags=re.IGNORECASE)
    elif re.search(r'python["\']?\s+', cmd, re.IGNORECASE) and '.exe' not in cmd.lower().split()[0] and '-u' not in cmd:
        cmd = re.sub(r'(python["\']?)\s+', r'\1 -u ', cmd, count=1, flags=re.IGNORECASE)
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=work_dir,
        env=clean_env,
        bufsize=0,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    
    stdout_capture = StreamOutput(process.stdout)
    stderr_capture = StreamOutput(process.stderr)
    
    lock = threading.Lock()
    running_processes[execution_id] = {
        "process": process,
        "terminated": False,
        "lock": lock,
        "stdout_capture": stdout_capture,
        "stderr_capture": stderr_capture
    }
    
    was_terminated = False
    last_output_time = time.time()
    last_stdout = ""
    last_stderr = ""
    
    while True:
        returncode = process.poll()
        if returncode is not None:
            break
        
        with lock:
            if running_processes.get(execution_id, {}).get("terminated"):
                was_terminated = True
                break
        
        if time.time() - start_time.timestamp() > timeout:
            was_terminated = True
            break
        
        current_stdout = stdout_capture.get_output()
        current_stderr = stderr_capture.get_output()
        
        if time.time() - last_output_time >= 10:
            if current_stdout != last_stdout or current_stderr != last_stderr:
                try:
                    await websocket.send(json.dumps({
                        "type": "execution_output",
                        "agent_id": AGENT_ID,
                        "task_id": task_id,
                        "execution_id": execution_id,
                        "output": {
                            "stdout": current_stdout,
                            "stderr": current_stderr,
                            "status": "running"
                        }
                    }))
                    last_stdout = current_stdout
                    last_stderr = current_stderr
                except Exception as e:
                    log(f"发送输出失败: {e}")
            last_output_time = time.time()
        
        await asyncio.sleep(0.5)
    
    # 进程退出后，再次检查是否被终止
    with lock:
        if running_processes.get(execution_id, {}).get("terminated"):
            was_terminated = True
    
    if process.poll() is None:
        kill_process_tree(process.pid)
        try:
            process.wait(timeout=5)
        except:
            pass
    
    stdout_capture.wait(timeout=1)
    stderr_capture.wait(timeout=1)
    
    stdout = stdout_capture.get_output()
    stderr = stderr_capture.get_output()
    
    returncode = process.returncode if process.returncode is not None else -1
    
    if execution_id in running_processes:
        del running_processes[execution_id]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "terminated" if was_terminated else ("success" if returncode == 0 else "error"),
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "execution_time": end_time.isoformat(),
        "duration": format_duration(duration),
        "work_dir": work_dir
    }
    
    try:
        await websocket.send(json.dumps({
            "type": "execution_result",
            "agent_id": AGENT_ID,
            "task_id": task_id,
            "execution_id": execution_id,
            "result": result
        }))
        log(f"任务完成: {task_id} - {result['status']}")
    except Exception as e:
        log(f"发送结果失败: {e}")


def terminate_execution(execution_id):
    """终止执行中的任务"""
    global running_processes
    
    if execution_id in running_processes:
        entry = running_processes[execution_id]
        process = entry.get("process")
        lock = entry.get("lock")
        
        with lock:
            entry["terminated"] = True
        
        if process and process.poll() is None:
            try:
                kill_process_tree(process.pid)
                log(f"已终止任务: {execution_id}")
                return True
            except Exception as e:
                log(f"终止任务失败: {e}")
                return False
    return False


async def send_heartbeat(websocket):
    """定时发送心跳"""
    while True:
        try:
            await asyncio.sleep(120)
            await websocket.send(json.dumps({
                "type": "ping",
                "agent_id": AGENT_ID,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            break


class AgentApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RPA Scheduler Agent")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果存在）
        try:
            self.root.iconbitmap("agent.ico")
        except:
            pass
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 状态变量
        self.is_running = False
        self.agent_info = None
        self.loop = None
        self.agent_thread = None
        
        self.setup_ui()
        
        # 启动时自动获取 Agent 信息
        self.agent_info = get_agent_info()
        self.update_info_display()
        
        # 启动日志处理
        self.process_logs()
        
        # 关闭窗口时的处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态区域
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 状态指示器
        status_row = ttk.Frame(status_frame)
        status_row.pack(fill=tk.X)
        
        ttk.Label(status_row, text="连接状态:").pack(side=tk.LEFT)
        self.status_indicator = tk.Canvas(status_row, width=16, height=16, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(5, 10))
        self.status_indicator.create_oval(2, 2, 14, 14, fill="gray", tags="status")
        
        self.status_label = ttk.Label(status_row, text="未连接", foreground="gray")
        self.status_label.pack(side=tk.LEFT)
        
        # Agent 信息
        info_frame = ttk.LabelFrame(main_frame, text="Agent 信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X)
        
        ttk.Label(info_grid, text="Agent ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.agent_id_label = ttk.Label(info_grid, text="-", foreground="#666")
        self.agent_id_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(info_grid, text="Agent 名称:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.agent_name_label = ttk.Label(info_grid, text="-", foreground="#666")
        self.agent_name_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(info_grid, text="主机名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.hostname_label = ttk.Label(info_grid, text="-", foreground="#666")
        self.hostname_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(info_grid, text="服务器:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.server_label = ttk.Label(info_grid, text=SERVER_URL, foreground="#666")
        self.server_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="启动", command=self.start_agent, width=15)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_agent, width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_log, width=10).pack(side=tk.RIGHT)
    
    def update_info_display(self):
        if self.agent_info:
            self.agent_id_label.config(text=self.agent_info["agent_id"][:8] + "...")
            self.agent_name_label.config(text=self.agent_info["agent_name"])
            self.hostname_label.config(text=self.agent_info["hostname"])
    
    def update_status(self, connected):
        if connected:
            self.status_indicator.itemconfig("status", fill="#22c55e")
            self.status_label.config(text="已连接", foreground="#22c55e")
        else:
            self.status_indicator.itemconfig("status", fill="#ef4444")
            self.status_label.config(text="已断开", foreground="#ef4444")
    
    def set_connecting(self):
        self.status_indicator.itemconfig("status", fill="#f59e0b")
        self.status_label.config(text="连接中...", foreground="#f59e0b")
    
    def process_logs(self):
        """处理日志队列"""
        try:
            while True:
                message = log_queue.get_nowait()
                self.append_log(message)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_logs)
    
    def append_log(self, message):
        """添加日志到文本框"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def start_agent(self):
        """启动 Agent"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 启动 Agent 线程
        self.agent_thread = threading.Thread(target=self.run_agent, daemon=True)
        self.agent_thread.start()
    
    def stop_agent(self):
        """停止 Agent"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status(False)
        log("Agent 已停止")
    
    def run_agent(self):
        """运行 Agent 主循环"""
        log(f"启动 Agent: {self.agent_info['agent_name']}")
        log(f"连接服务器: {SERVER_URL}")
        
        asyncio.run(self.agent_loop())
    
    async def agent_loop(self):
        """Agent 主循环"""
        while self.is_running:
            try:
                self.root.after(0, self.set_connecting)
                
                async with websockets.connect(
                    SERVER_URL,
                    ping_interval=120,
                    ping_timeout=60,
                    close_timeout=None
                ) as websocket:
                    self.root.after(0, lambda: self.update_status(True))
                    log("已连接到服务器")
                    
                    await websocket.send(json.dumps({
                        "type": "register",
                        "agent": self.agent_info
                    }))
                    log("已注册到服务器")
                    
                    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                    running_tasks = set()
                    
                    try:
                        async for message in websocket:
                            if not self.is_running:
                                break
                            
                            try:
                                data = json.loads(message)
                                msg_type = data.get("type")
                                
                                if msg_type == "execute":
                                    cmd = data.get("cmd")
                                    timeout = data.get("timeout", 300)
                                    task_id = data.get("task_id")
                                    execution_id = data.get("execution_id")
                                    
                                    log(f"执行任务: {task_id}")
                                    log(f"命令: {cmd}")
                                    
                                    task = asyncio.create_task(
                                        execute_command_async(cmd, timeout, websocket, task_id, execution_id)
                                    )
                                    running_tasks.add(task)
                                    task.add_done_callback(running_tasks.discard)
                                
                                elif msg_type == "terminate":
                                    execution_id = data.get("execution_id")
                                    log(f"收到终止命令: {execution_id}")
                                    
                                    success = terminate_execution(execution_id)
                                    
                                    try:
                                        await websocket.send(json.dumps({
                                            "type": "terminate_ack",
                                            "agent_id": AGENT_ID,
                                            "execution_id": execution_id,
                                            "success": success
                                        }))
                                    except Exception as e:
                                        log(f"发送终止确认失败: {e}")
                                
                                elif msg_type == "pong":
                                    pass
                                
                                elif msg_type == "shutdown":
                                    log("收到关闭命令")
                                    await websocket.send(json.dumps({
                                        "type": "shutdown_ack",
                                        "agent_id": AGENT_ID
                                    }))
                                    heartbeat_task.cancel()
                                    self.root.after(0, self.stop_agent)
                                    return
                                    
                            except json.JSONDecodeError:
                                log(f"无效消息: {message[:50]}")
                            except Exception as e:
                                log(f"处理消息错误: {e}")
                    finally:
                        heartbeat_task.cancel()
                            
            except websockets.exceptions.ConnectionClosed:
                log(f"连接断开，{RECONNECT_INTERVAL}秒后重连...")
                self.root.after(0, lambda: self.update_status(False))
            except Exception as e:
                log(f"连接错误: {e}")
                log(f"{RECONNECT_INTERVAL}秒后重连...")
                self.root.after(0, lambda: self.update_status(False))
            
            if self.is_running:
                await asyncio.sleep(RECONNECT_INTERVAL)
    
    def on_closing(self):
        """关闭窗口"""
        self.is_running = False
        self.root.destroy()
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    app = AgentApp()
    app.run()


if __name__ == "__main__":
    main()
