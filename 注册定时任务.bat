@echo off
chcp 936 >nul 2>&1
title 注册 AI 趋势日报定时任务
cd /d "%~dp0"

echo ================================================
echo   注册 Windows 计划任务：每天 09:10 自动运行
echo ================================================
echo.

net session >nul 2>&1
if errorlevel 1 (
  echo [!] 当前不是管理员权限，注册到当前用户即可，一般也能成功。
  echo.
)

echo 任务名：AI-Trends-Daily
echo 执行：%~dp0每日任务.bat
echo 时间：每天 09:10
echo.

schtasks /Create /TN "AI-Trends-Daily" /TR "\"%~dp0每日任务.bat\"" /SC DAILY /ST 09:10 /F
if errorlevel 1 (
  echo.
  echo [x] 注册失败。可以手动操作：
  echo     开始菜单搜「任务计划程序」→ 创建基本任务
  echo     名称 AI-Trends-Daily，每天，09:10
  echo     操作选「启动程序」，程序填：
  echo     %~dp0每日任务.bat
  pause
  exit /b 1
)

echo.
echo [OK] 注册成功。下次执行时间：
schtasks /Query /TN "AI-Trends-Daily" /FO LIST | findstr /C:"下次" /C:"Next"
echo.
echo 想立刻试跑一次，可以执行：
echo     schtasks /Run /TN "AI-Trends-Daily"
echo.
echo 运行日志在 logs\daily.log
echo.
pause
