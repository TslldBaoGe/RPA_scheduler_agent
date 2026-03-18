@echo off
echo Building RPA Agent Electron App...
echo.

cd /d "%~dp0"

echo Installing dependencies...
call npm install

echo.
echo Building Windows executable...
call npm run build

echo.
echo Build complete!
echo Output: dist/RPA-Agent Setup.exe
pause
