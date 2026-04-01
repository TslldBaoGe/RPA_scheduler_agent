#!/usr/bin/env python3
"""
Agent 打包脚本 - 使用 PyInstaller 打包成 EXE
"""
import PyInstaller.__main__
import os
import sys

def build_agent():
    """打包 Agent 为可执行文件"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    args = [
        'agent.py',
        '--name=RPA-Agent',
        '--onefile',
        '--collect-submodules=websockets',
        '--hidden-import=asyncio',
        '--clean',
        '--noconfirm',
        f'--distpath={current_dir}',
        f'--workpath={current_dir}/build',
        f'--specpath={current_dir}',
    ]
    
    print("开始打包 Agent...")
    print(f"输出目录: {current_dir}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n打包完成!")
        print(f"可执行文件位置: {current_dir}/RPA-Agent.exe")
    except Exception as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_agent()
