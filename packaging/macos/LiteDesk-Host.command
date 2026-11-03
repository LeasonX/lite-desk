#!/bin/bash
# LiteDesk 被控端 (macOS 双击启动)
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 没找到 python3, 请先安装: https://www.python.org 或 brew install python"
  read -r -p "按回车关闭"; exit 1
fi
if [ ! -d .venv ]; then
  echo "首次运行, 正在创建环境并安装依赖..."
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
echo ""
echo "提醒: 首次被连接前, 请到 系统设置 > 隐私与安全性, 给「终端」开启 屏幕录制 + 辅助功能, 否则看不到画面/控制不了。"
echo "被控端启动后会显示连接密码, 把 本机IP + 密码 告诉控制端即可。"
echo ""
.venv/bin/python host.py
read -r -p "已退出, 按回车关闭"
