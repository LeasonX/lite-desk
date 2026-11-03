@echo off
chcp 65001 >nul
title LiteDesk 被控端
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
echo.
echo 被控端启动后会显示连接密码, 把 本机IP + 密码 告诉控制端即可被连接。
echo.
python host.py
pause
