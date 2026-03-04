#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本：将 Agent 打包成可执行文件
"""
import subprocess
import sys
import os

def build_exe():
    """使用 PyInstaller 打包 Agent"""
    
    # PyInstaller 参数
    args = [
        'pyinstaller',
        '--name=CronSchedulerAgent',  # 可执行文件名称
        '--onefile',  # 打包成单个文件
        '--console',  # 使用控制台模式（显示输出）
        '--hidden-import=websockets',
        'agent.py'
    ]
    
    print("开始打包 Agent...")
    subprocess.run(args, check=True)
    print("Agent 打包完成！")
    
    # 创建启动脚本
    create_start_script()

def create_start_script():
    """创建启动脚本"""
    script_content = '''@echo off
echo Starting Cron Scheduler Agent...
echo.
echo This agent will connect to the server and execute commands locally.
echo.
start CronSchedulerAgent.exe
'''
    
    with open('start-agent.bat', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("启动脚本已创建！")

if __name__ == '__main__':
    build_exe()
