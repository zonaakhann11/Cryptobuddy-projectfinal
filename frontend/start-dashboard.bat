@echo off
set NODE_DIR=%~dp0.tools\node-v22.17.0-win-x64
set PATH=%NODE_DIR%;%PATH%
cd /d %~dp0
echo Using portable Node from %NODE_DIR%
call "%NODE_DIR%\node.exe" -v
call "%NODE_DIR%\npm.cmd" install
call "%NODE_DIR%\npx.cmd" --yes vite --host=127.0.0.1 --port=5173
pause
