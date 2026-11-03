@echo off
chcp 65001 >nul
title LiteDesk 控制端
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 Python, 请先从 https://www.python.org 安装 Python 3.10 以上版本, 安装时勾选 "Add python.exe to PATH"
  pause
  exit /b 1
)
if not exist .deps_ok (
  echo 首次运行, 正在安装依赖...
  python -m pip install -r requirements.txt
  echo ok> .deps_ok
)
set /p TARGET=请输入被控端 IP (如 192.168.1.20):
set /p PWD=请输入被控端显示的连接密码:
python controller.py %TARGET% --password %PWD%
pause
