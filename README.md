# RPA Scheduler Agent

本地代理程序，连接服务器接收指令并在本地执行命令。

## 功能

- 连接到服务器 WebSocket
- 执行命令（支持终止)
- 实时输出捕获
- 癚拟环境支持

## 使用方法

1. 安装依赖:
   ```bash
   pip install websockets pyinstaller
   ```

2. 打包:
   ```bash
   python build_agent.py
   ```

3. 运行:
   ```bash
   RPA-Agent.exe
   ```

4. 配置:
   - 服务器地址: 修改 `agent.py` 中的 `SERVER_URL`
   - Agent ID 保   - 首次运行会自动生成并保存到 `agent_config.json`

## 文件说明

- `agent.py` - Agent 主程序
- `build_agent.py` - 打包脚本
- `agent_config.json` - Agent 配置文件（自动生成)
