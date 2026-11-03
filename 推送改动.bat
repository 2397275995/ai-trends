@echo off
title 推送 AI 趋势项目改动
cd /d "%~dp0"
set "LOG=%TEMP%\aitrends-push.log"

echo ================================================
echo   推送 ai-trends 改动到 GitHub
echo   仓库：https://github.com/2397275995/ai-trends
echo ================================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [x] 当前目录不是 git 仓库：%CD%
  pause
  exit /b 1
)

echo === 第一步：同步远端 ===
git pull --rebase origin main > "%LOG%" 2>&1
if errorlevel 1 goto pulllog
echo 已同步。
goto push

:pulllog
type "%LOG%"
echo.
findstr /C:"CONFLICT" "%LOG%" >nul
if not errorlevel 1 (
  echo [x] 和远端冲突，先执行：git rebase --abort
  echo     然后把情况告诉 WorkBuddy。
  pause
  exit /b 1
)
findstr /C:"Could not connect" /C:"Failed to connect" /C:"timed out" /C:"Could not resolve host" "%LOG%" >nul
if not errorlevel 1 (
  echo [!] 连不上 GitHub，网络问题。稍后重试即可，本地提交不会丢。
  pause
  exit /b 1
)
echo [x] 同步失败，原因见上。
pause
exit /b 1

:push
echo.
echo === 第二步：推送 ===
git push -u origin main > "%LOG%" 2>&1
if errorlevel 1 goto pushlog
type "%LOG%"
echo.
echo [OK] 推送成功。EdgeOne 会自动重新部署，约两分钟。
echo.
echo 别忘了去 EdgeOne 控制台给项目加环境变量，例如：
echo     NOTIFY_WECOM = 企业微信群机器人 webhook
echo.
pause
exit /b 0

:pushlog
type "%LOG%"
echo.
findstr /C:"Could not connect" /C:"Failed to connect" /C:"timed out" /C:"Could not resolve host" "%LOG%" >nul
if not errorlevel 1 (
  echo [!] 推送时连不上 GitHub，网络问题，稍后重试。
  pause
  exit /b 1
)
echo [x] 推送失败，原因见上。
pause
exit /b 1
