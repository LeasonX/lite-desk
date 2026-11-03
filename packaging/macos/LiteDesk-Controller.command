#!/bin/bash
# LiteDesk 控制端 (macOS 双击启动)
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 没找到 python3, 请先安装: https://www.python.org 或 brew install python"
  read -r -p "按回车关闭"; exit 1
fi
if [ ! -d .venv ]; then
  echo "首次运行, 正在创建环境并安装依赖..."
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
read -r -p "请输入被控端 IP (如 192.168.1.20): " TARGET
read -r -p "请输入被控端显示的连接密码: " PWD
.venv/bin/python controller.py "$TARGET" --password "$PWD"
read -r -p "已退出, 按回车关闭"
