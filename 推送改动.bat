@echo off
setlocal enabledelayedexpansion
title 推送 AI 趋势项目改动
cd /d "%~dp0"
set "LOG=%TEMP%\aitrends-push.log"
set "PX="
set "PXARGS="

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

rem ── 先把本地改动提交掉，否则 pull --rebase 会被挡住 ──
git add -A >nul 2>&1
git commit -q -m "自动提交：推送前的本地改动" >nul 2>&1

rem ── 探测本地代理（先落盘再查，避免 for 里用管道）──
netstat -ano > "%TEMP%\ports.txt" 2>nul
for %%P in (7897 7890 7891 10809 10808 1080 8888 20171) do (
  if not defined PX (
    findstr /C:":%%P " "%TEMP%\ports.txt" >nul && set "PX=%%P"
  )
)
if defined PX (
  set "PXARGS=-c http.proxy=http://127.0.0.1:!PX! -c https.proxy=http://127.0.0.1:!PX!"
  echo [i] 检测到本地代理 127.0.0.1:!PX!，本次推送走代理
) else (
  echo [i] 没检测到本地代理，按直连尝试
)
echo.

echo === 第一步：同步远端 ===
git !PXARGS! pull --rebase origin main > "%LOG%" 2>&1
if errorlevel 1 goto pulllog
echo 已同步。
goto push

:pulllog
type "%LOG%"
echo.
findstr /C:"CONFLICT" /C:"Automatic merge failed" "%LOG%" >nul
if not errorlevel 1 (
  echo [x] 和远端内容冲突。
  echo     先执行：git rebase --abort
  echo     然后找 WorkBuddy 按数据结构合并，别自己改 JSON。
  pause
  exit /b 1
)
findstr /C:"Could not connect" /C:"Failed to connect" /C:"timed out" /C:"Could not resolve host" /C:"Connection refused" "%LOG%" >nul
if not errorlevel 1 (
  echo [!] 连不上 GitHub。
  echo     1. 代理软件要开着，端口默认 7897
  echo     2. 本机改动不会丢，稍后重试即可
  pause
  exit /b 1
)
echo [x] 同步失败，原因见上。
pause
exit /b 1

:push
echo.
echo === 第二步：推送 ===
git !PXARGS! push -u origin main > "%LOG%" 2>&1
if errorlevel 1 goto pushlog
type "%LOG%"
echo.
echo [OK] 推送成功。EdgeOne 会自动重新部署，约两分钟。
echo.
pause
exit /b 0

:pushlog
type "%LOG%"
echo.
findstr /C:"Could not connect" /C:"Failed to connect" /C:"timed out" /C:"Could not resolve host" "%LOG%" >nul
if not errorlevel 1 (
  echo [!] 推送时连不上 GitHub，检查代理后重试。
  pause
  exit /b 1
)
findstr /C:"rejected" /C:"non-fast-forward" "%LOG%" >nul
if not errorlevel 1 (
  echo [x] 远端又有新提交，再运行一次本脚本即可。
  pause
  exit /b 1
)
echo [x] 推送失败，原因见上。
pause
exit /b 1
