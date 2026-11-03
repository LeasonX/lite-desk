#!/bin/bash
# LiteDesk 一键打包 .app / 可执行文件 (macOS 双击运行)
cd "$(dirname "$0")" || exit 1
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -r requirements.txt pyinstaller
.venv/bin/python build.py
echo ""
echo "完成! dist 文件夹里就是 LiteDesk-Host 和 LiteDesk-Controller.app, 不需要装 Python 就能运行。"
echo "注意: 未签名应用首次打开被 Gatekeeper 拦时, 右键点 .app -> 打开 -> 仍要打开。"
read -r -p "按回车关闭"
