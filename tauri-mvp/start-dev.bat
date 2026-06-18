@echo off
REM 活着为了讲述 快速启动脚本（开发模式）
REM 自动启动后端和前端

echo ========================================
echo 活着为了讲述 快速启动
echo ========================================
echo.

REM 检查后端是否已在运行
netstat -ano | findstr :8000 >nul
if %errorlevel% == 0 (
    echo [后端] 已在运行 (端口 8000)
) else (
    echo [后端] 正在启动...
    start "Living to Tell Backend" /min cmd /c "cd /d %~dp0backend && python run.py --dev"
    timeout /t 3 /nobreak >nul
    echo [后端] 已启动
)

echo.

REM 检查前端是否已在运行
netstat -ano | findstr :1420 >nul
if %errorlevel% == 0 (
    echo [前端] 已在运行 (端口 1420)
) else (
    echo [前端] 正在启动...
    start "Living to Tell Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"
    timeout /t 5 /nobreak >nul
    echo [前端] 已启动
)

echo.
echo ========================================
echo 活着为了讲述 已启动！
echo ========================================
echo.
echo 浏览器访问: http://localhost:1420
echo 后端 API:   http://localhost:8000
echo.
echo 按任意键打开浏览器...
pause >nul

start http://localhost:1420
