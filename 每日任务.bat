@echo off
chcp 936 >nul 2>&1
title AI 趋势日报 - 每日任务
cd /d "%~dp0"
set "LOG=%~dp0logs\daily.log"
if not exist "%~dp0logs" mkdir "%~dp0logs"

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo 开始执行：%date% %time% >> "%LOG%"

rem 用 WorkBuddy 自带的 Python（没有就用系统 python）
set "PY=C:/Users/23972/.workbuddy/binaries/python/versions/3.13.12/python.exe"
if not exist "%PY%" set "PY=python"

echo [1/2] 触发采集并等待新报告 >> "%LOG%"
"%PY%" "%~dp0scripts\trigger_run.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [x] 采集失败，跳过发邮件 >> "%LOG%"
  exit /b 1
)

echo [2/2] 生成 PDF 并发送邮件 >> "%LOG%"
"%PY%" "%~dp0scripts\report_pdf.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [x] 邮件发送失败 >> "%LOG%"
  exit /b 1
)

echo [OK] 完成：%date% %time% >> "%LOG%"
exit /b 0
