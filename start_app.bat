@echo off
setlocal enabledelayedexpansion

title 自动气象站智慧学习平台 - 启动中心

echo ============================================================
echo.
echo      SmartQbank 智慧学习平台 (Vue 3 + FastAPI 版)
echo.
echo ============================================================
echo.

:: 检查 Python 环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 找不到 Python 虚拟环境 (.venv)，请确保已安装依赖。
    pause
    exit /b
)

:: 检查 Node.js 环境
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 找不到 npm 命令，请确保已安装 Node.js。
    pause
    exit /b
)

:: 1. 启动后端 FastAPI
echo [1/3] 正在后台启动后端服务 (FastAPI)...
start /b "SmartQbank_Backend" ".venv\Scripts\python.exe" run_api.py

:: 等待后端初始化
timeout /t 3 /nobreak > nul

:: 2. 启动前端 Vite
echo [2/3] 正在后台启动前端界面 (Vite)...
cd frontend
start /b "SmartQbank_Frontend" cmd /c "npm run dev"
cd ..

:: 等待前端准备就绪
echo [3/3] 正在等待服务就绪并打开浏览器...
timeout /t 5 /nobreak > nul

:: 3. 打开浏览器
start http://localhost:5173

echo.
echo ============================================================
echo.
echo   一键启动成功！
echo.
echo   - 前端访问地址: http://localhost:5173
echo   - 后端 API 地址: http://localhost:8000
echo.
echo   提示: 保持此窗口开启以运行服务。按 Ctrl+C 可终止。
echo.
echo ============================================================
echo.

:: 保持窗口不退出，以便查看实时日志
pause > nul
