#!/usr/bin/env python3
"""生成应用图标 assets/icon.{png,ico,icns}。

图标是二进制文件, 不直接进仓库: 由本脚本在打包时现画现生成,
这样仓库保持纯文本, build.py 在任何平台打包前都会先调用它。
"""
import os
from PIL import Image, ImageDraw

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(out, exist_ok=True)
    img = Image.new("RGBA", (512, 512), (32, 42, 68, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([16, 16, 496, 496], radius=90, outline=(255, 210, 60, 255), width=14)
    d.rectangle([96, 120, 416, 330], outline=(255, 255, 255, 255), width=12)
    d.line([(256, 330), (256, 400)], fill=(255, 255, 255, 255), width=12)
    d.line([(176, 416), (336, 416)], fill=(255, 255, 255, 255), width=12)
    cx, cy = 320, 250
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=(255, 210, 60, 255), width=10)
    d.line([(cx - 40, cy), (cx + 40, cy)], fill=(255, 210, 60, 255), width=8)
    d.line([(cx, cy - 40), (cx, cy + 40)], fill=(255, 210, 60, 255), width=8)
    img.save(os.path.join(out, "icon.png"))
    # 单个格式失败不能拖垮整个打包 (如某平台 Pillow 写 icns/ico 受限), 逐个容错
    for fmt, kw in [("icon.ico", {"sizes": [(16, 16), (32, 32), (48, 48), (256, 256)]}), ("icon.icns", {})]:
        try:
            img.save(os.path.join(out, fmt), **kw)
        except Exception as e:
            print(f"warning: {fmt} 生成失败 ({e}), 打包时将跳过该图标")
    print("icons generated in", out)

if __name__ == "__main__":
    main()
