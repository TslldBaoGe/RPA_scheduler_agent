@echo off
echo ==========================================
echo RPA Agent 打包工具
echo ==========================================
echo.

echo [1/3] 正在打包...
pyinstaller agent.py --name=RPA-Agent --onefile --console --clean --noconfirm --hidden-import=websockets --hidden-import=websockets.legacy --hidden-import=websockets.legacy.client --hidden-import=asyncio --distpath=dist --workpath=build

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo [2/3] 复制配置文件...
if not exist dist\agent_config.json (
    copy agent_config.json dist\
)

echo [3/3] 清理临时文件...
if exist RPA-Agent.spec del RPA-Agent.spec
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
echo 2. 将 agent_config.json 放在同一目录
echo 3. 修改 agent_config.json 中的服务器地址
echo 4. 双击运行 RPA-Agent.exe
echo.
pause
