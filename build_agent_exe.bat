@echo off
echo ==========================================
echo RPA Agent 打包工具
echo ==========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 安装 PyInstaller
echo [1/4] 安装 PyInstaller...
python -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

REM 创建临时打包脚本
echo [2/4] 创建打包配置...
(
echo import PyInstaller.__main__
echo import os
echo.
echo current_dir = r'%CD%'
echo.
echo PyInstaller.__main__.run([
echo     'agent.py',
echo     '--name=RPA-Agent',
echo     '--onefile',
echo     '--console',
echo     '--clean',
echo     '--noconfirm',
echo     '--hidden-import=websockets',
echo     '--hidden-import=websockets.legacy',
echo     '--hidden-import=websockets.legacy.client',
echo     '--hidden-import=asyncio',
echo     '--add-data=agent_config.json;.',
echo     f'--distpath={current_dir}\\dist',
echo     f'--workpath={current_dir}\\build',
echo     f'--specpath={current_dir}',
echo ])
) > temp_build.py

REM 执行打包
echo [3/4] 开始打包...
python temp_build.py
if errorlevel 1 (
    echo [错误] 打包失败
    del temp_build.py
    pause
    exit /b 1
)

REM 清理临时文件
echo [4/4] 清理临时文件...
del temp_build.py
if exist "RPA-Agent.spec" del "RPA-Agent.spec"
if exist build rmdir /s /q build

echo.
echo ==========================================
echo [成功] 打包完成！
echo ==========================================
echo.
echo 输出文件: dist\RPA-Agent.exe
echo.
echo 使用说明:
echo 1. 将 dist\RPA-Agent.exe 复制到目标机器
echo 2. 修改 agent_config.json 中的服务器地址
echo 3. 双击运行 RPA-Agent.exe
echo.
pause
