#!/usr/bin/env python3
"""
Agent 打包脚本 - 使用 PyInstaller 打包成 EXE
"""
import PyInstaller.__main__
import os
import sys

def build_agent():
    """打包 Agent 为可执行文件"""
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 打包参数
    args = [
        'agent.py',  # 主程序
        '--name=RPA-Agent',  # 生成的 exe 名称
        '--onefile',  # 打包成单个文件
        '--windowed',  # 使用窗口模式（不显示控制台）
        '--icon=NONE',  # 可以添加图标
        '--add-data=agent_config.json;.',  # 包含配置文件
        '--hidden-import=websockets',
        '--hidden-import=websockets.legacy',
        '--hidden-import=websockets.legacy.client',
        '--hidden-import=asyncio',
        '--clean',  # 清理临时文件
        '--noconfirm',  # 不确认覆盖
        f'--distpath={current_dir}/dist',  # 输出目录
        f'--workpath={current_dir}/build',  # 工作目录
        f'--specpath={current_dir}',  # spec 文件目录
    ]
    
    print("开始打包 Agent...")
    print(f"输出目录: {current_dir}/dist")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n✅ 打包完成!")
        print(f"可执行文件位置: {current_dir}/dist/RPA-Agent.exe")
        print("\n使用说明:")
        print("1. 将 RPA-Agent.exe 和 agent_config.json 复制到目标机器")
        print("2. 修改 agent_config.json 中的服务器地址")
        print("3. 双击运行 RPA-Agent.exe")
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_agent()
