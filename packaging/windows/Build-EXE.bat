@echo off
chcp 65001 >nul
title LiteDesk 一键打包 EXE
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 Python, 请先安装 Python 3.10+ 并勾选 Add to PATH
  pause
  exit /b 1
)
python -m pip install -r requirements.txt pyinstaller
python build.py
echo.
echo 完成! dist 文件夹里就是 LiteDesk-Host.exe 和 LiteDesk-Controller.exe, 不需要装 Python 就能运行。
pause
