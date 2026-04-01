#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cron Scheduler Agent
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
from datetime import datetime

# 配置
SERVER_URL = "ws://rpa.tslldtslldtslld.top/ws/agent"
AGENT_ID = None
AGENT_NAME = None
RECONNECT_INTERVAL = 5

# 正在执行的任务
running_processes = {}


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
        "pid": os.getpid(),
        "python_path": sys.executable
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
        print(f"[Agent] Failed to kill process tree {pid}: {e}")
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
            print(f"[Agent] StreamOutput error: {e}")
        finally:
            self.finished.set()
    
    def get_output(self):
        with self.lock:
            return "".join(self.lines)
    
    def wait(self, timeout=None):
        self.finished.wait(timeout)


def execute_command_sync(cmd, timeout, execution_id):
    """在本地执行命令（同步）"""
    global running_processes
    
    start_time = datetime.now()
    process = None
    was_terminated = False
    stdout = ""
    stderr = ""
    
    try:
        # 提取工作目录
        work_dir = None
        import re
        python_match = re.search(r'(?:python|python\.exe)\s+["\']?([^\s"\']+\.py)["\']?', cmd, re.IGNORECASE)
        if python_match:
            script_path = python_match.group(1).strip('"\'')
            if os.path.exists(script_path):
                work_dir = os.path.dirname(os.path.abspath(script_path))
                print(f"[Agent] Work directory: {work_dir}")
        
        # 使用完整的环境变量，只添加额外的设置
        clean_env = os.environ.copy()
        # 禁用 Python 输出缓冲
        clean_env['PYTHONUNBUFFERED'] = '1'
        clean_env['PYTHONIOENCODING'] = 'utf-8'
        
        # 如果是 Python 命令，添加 -u 参数确保无缓冲
        # 只匹配 python.exe 或 python 后面跟空格或引号的情况
        if re.search(r'python\.exe["\']?\s+', cmd, re.IGNORECASE) and '-u' not in cmd:
            cmd = re.sub(r'(python\.exe["\']?)\s+', r'\1 -u ', cmd, count=1, flags=re.IGNORECASE)
        elif re.search(r'python["\']?\s+', cmd, re.IGNORECASE) and '.exe' not in cmd.lower().split()[0] and '-u' not in cmd:
            cmd = re.sub(r'(python["\']?)\s+', r'\1 -u ', cmd, count=1, flags=re.IGNORECASE)
        
        # 使用 Popen 启动进程
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
        
        # 创建输出捕获器
        stdout_capture = StreamOutput(process.stdout)
        stderr_capture = StreamOutput(process.stderr)
        
        # 注册进程
        lock = threading.Lock()
        running_processes[execution_id] = {
            "process": process,
            "terminated": False,
            "lock": lock,
            "stdout_capture": stdout_capture,
            "stderr_capture": stderr_capture
        }
        
        # 等待进程完成或被终止
        start_wait = time.time()
        while True:
            # 检查进程是否完成
            returncode = process.poll()
            if returncode is not None:
                break
            
            # 检查是否被终止
            with lock:
                if running_processes.get(execution_id, {}).get("terminated"):
                    was_terminated = True
                    break
            
            # 检查超时
            if time.time() - start_wait > timeout:
                was_terminated = True
                break
            
            time.sleep(0.1)
        
        # 如果进程还在运行，终止它
        if process.poll() is None:
            kill_process_tree(process.pid)
            try:
                process.wait(timeout=5)
            except:
                pass
        
        # 等待输出捕获完成
        stdout_capture.wait(timeout=1)
        stderr_capture.wait(timeout=1)
        
        # 获取输出
        stdout = stdout_capture.get_output()
        stderr = stderr_capture.get_output()
        
        returncode = process.returncode if process.returncode is not None else -1
        
    except Exception as e:
        print(f"[Agent] Execute error: {e}")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        return {
            "status": "error",
            "error": str(e),
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": end_time.isoformat(),
            "duration": format_duration(duration)
        }
    finally:
        # 移除注册
        if execution_id in running_processes:
            del running_processes[execution_id]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if was_terminated:
        return {
            "status": "terminated",
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": end_time.isoformat(),
            "duration": format_duration(duration),
            "work_dir": work_dir
        }
    
    return {
        "status": "success" if returncode == 0 else "error",
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "execution_time": end_time.isoformat(),
        "duration": format_duration(duration),
        "work_dir": work_dir
    }


async def execute_command_async(cmd, timeout, websocket, task_id, execution_id):
    """异步执行命令"""
    loop = asyncio.get_event_loop()
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
                    print(f"[Agent] Failed to send output: {e}")
            last_output_time = time.time()
        
        await asyncio.sleep(0.5)
    
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
    except Exception as e:
        print(f"[Agent] Failed to send result: {e}")


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
                print(f"[Agent] Terminated execution: {execution_id}")
                return True
            except Exception as e:
                print(f"[Agent] Failed to terminate execution {execution_id}: {e}")
                return False
    return False


async def send_heartbeat(websocket):
    """定时发送心跳"""
    while True:
        try:
            await asyncio.sleep(120)  # 每2分钟发送一次心跳
            await websocket.send(json.dumps({
                "type": "ping",
                "agent_id": AGENT_ID,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            print(f"[Agent] Heartbeat error: {e}")
            break


async def agent_loop():
    """Agent 主循环"""
    agent_info = get_agent_info()
    
    print(f"[Agent] Starting agent: {agent_info['agent_name']} ({agent_info['agent_id']})")
    print(f"[Agent] Connecting to server: {SERVER_URL}")
    
    while True:
        try:
            async with websockets.connect(
                SERVER_URL,
                ping_interval=120,  # 2分钟发送一次 WebSocket ping
                ping_timeout=60,    # 60秒没收到 pong 则断开
                close_timeout=None
            ) as websocket:
                print("[Agent] Connected to server")
                
                await websocket.send(json.dumps({
                    "type": "register",
                    "agent": agent_info
                }))
                
                # 启动心跳任务
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                
                running_tasks = set()
                
                try:
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            
                            if msg_type == "execute":
                                cmd = data.get("cmd")
                                timeout = data.get("timeout", 300)
                                task_id = data.get("task_id")
                                execution_id = data.get("execution_id")
                                
                                print(f"[Agent] Executing command: {cmd}")
                                
                                task = asyncio.create_task(
                                    execute_command_async(cmd, timeout, websocket, task_id, execution_id)
                                )
                                running_tasks.add(task)
                                task.add_done_callback(running_tasks.discard)
                                
                            elif msg_type == "terminate":
                                execution_id = data.get("execution_id")
                                print(f"[Agent] Received terminate command for: {execution_id}")
                                
                                success = terminate_execution(execution_id)
                                
                                try:
                                    await websocket.send(json.dumps({
                                        "type": "terminate_ack",
                                        "agent_id": AGENT_ID,
                                        "execution_id": execution_id,
                                        "success": success
                                    }))
                                except Exception as e:
                                    print(f"[Agent] Failed to send terminate_ack: {e}")
                                
                            elif msg_type == "pong":
                                # 收到心跳响应
                                pass
                                
                            elif msg_type == "shutdown":
                                print("[Agent] Received shutdown command")
                                await websocket.send(json.dumps({
                                    "type": "shutdown_ack",
                                    "agent_id": AGENT_ID
                                }))
                                heartbeat_task.cancel()
                                return
                                
                        except json.JSONDecodeError:
                            print(f"[Agent] Invalid message: {message}")
                        except Exception as e:
                            print(f"[Agent] Error processing message: {e}")
                finally:
                    heartbeat_task.cancel()
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"[Agent] Connection closed, reconnecting in {RECONNECT_INTERVAL} seconds...")
        except Exception as e:
            print(f"[Agent] Connection error: {e}")
            print(f"[Agent] Reconnecting in {RECONNECT_INTERVAL} seconds...")
        
        await asyncio.sleep(RECONNECT_INTERVAL)


def main():
    print("=" * 50)
    print("Cron Scheduler Agent")
    print("=" * 50)
    print()
    
    if sys.version_info < (3, 7):
        print("Error: Python 3.7+ required")
        sys.exit(1)
    
    try:
        asyncio.run(agent_loop())
    except KeyboardInterrupt:
        print("\n[Agent] Stopped by user")
    except Exception as e:
        print(f"[Agent] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
