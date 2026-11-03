#!/usr/bin/env python3
"""一键打包成本机平台的原生程序 (在哪个系统运行, 就产出哪个系统的包)

用法:  pip install pyinstaller && python3 build.py
产物:  dist/
  Windows : LiteDesk-Host.exe (带控制台, 显示连接密码) / LiteDesk-Controller.exe (无控制台窗口程序)
  macOS   : LiteDesk-Host (可执行) / LiteDesk-Controller.app (双击运行)
  Linux   : LiteDesk-Host / LiteDesk-Controller

为什么必须在目标系统上打包: PyInstaller 不是交叉编译器, 它把当前系统的
Python 解释器和原生库 (mss/pynput 依赖的 Win32/Quartz/X11) 打进产物,
在 Linux 上永远打不出 .exe/.app。这也是配 GitHub Actions 云端打包的原因:
把本仓库推到 GitHub, Actions 会在 windows/macos 云机器上跑这个脚本并产出真包。
"""
import platform, subprocess, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
SYSTEM = platform.system()  # Windows / Darwin / Linux

def build(entry: str, name: str, windowed: bool):
    # 不用 --collect-all: 它会把 mss/pynput 的全部子模块和数据一股脑收进来,
    # 在部分平台会让 PyInstaller 分析阶段失败。改成显式声明运行时才动态加载的后端:
    # 抓屏只需 mss 本体; pynput 按平台加载 _win32/_darwin/_xorg 后端, 静态分析跟不到, 必须点名。
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--name", name, "--paths", ROOT,
            "--hidden-import", "mss",
            "--hidden-import", "pynput.mouse._win32", "--hidden-import", "pynput.keyboard._win32",
            "--hidden-import", "pynput.mouse._darwin", "--hidden-import", "pynput.keyboard._darwin",
            "--hidden-import", "pynput.mouse._xorg", "--hidden-import", "pynput.keyboard._xorg",
            "--hidden-import", "PIL.ImageTk"]
    icon_name = {"Windows": "icon.ico", "Darwin": "icon.icns"}.get(SYSTEM, "icon.png")
    icon = os.path.join(ROOT, "assets", icon_name)
    if os.path.exists(icon):
        args += ["--icon", icon]
    if windowed:
        args.append("--windowed")  # macOS 下会额外生成 .app
    args.append(os.path.join(ROOT, entry))
    print("+", " ".join(args), flush=True)
    # 捕获 PyInstaller 输出: 失败时把尾部写进 GitHub Actions 的 Job Summary
    # ($GITHUB_STEP_SUMMARY 指向的文件会渲染在运行页上, 公开仓库未登录也能看),
    # 这样在看不到完整日志时也能定位失败原因; 本地运行时该变量不存在, 自动跳过。
    proc = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors="replace")
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-60:])
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(f"\n### PyInstaller failed: {name} (exit {proc.returncode})\n\n```\n{tail}\n```\n")
        print(f"::error::PyInstaller failed for {name} with exit code {proc.returncode}; see job summary for log tail")
        raise SystemExit(proc.returncode)

def main():
    # 图标是生成的二进制产物, 打包前现生成 (仓库里只存 make_icons.py)
    subprocess.check_call([sys.executable, os.path.join(ROOT, "make_icons.py")], cwd=ROOT)
    build("host.py", "LiteDesk-Host", windowed=False)        # 被控端要控制台显示密码
    build("controller.py", "LiteDesk-Controller", windowed=True)
    print("\n完成, 产物在 dist/:")
    for f in sorted(os.listdir(os.path.join(ROOT, "dist"))):
        print(" -", f)
    if SYSTEM == "Darwin":
        print("\nmacOS 注意: 未签名应用首次打开会被 Gatekeeper 拦, 右键 .app -> 打开 -> 仍要打开。")
        print("被控端还需到 系统设置 > 隐私与安全性 给它开「屏幕录制」和「辅助功能」。")
    if SYSTEM == "Windows":
        print("\nWindows 注意: 未签名 .exe 首次运行 SmartScreen 会提示, 点「更多信息 -> 仍要运行」。")

if __name__ == "__main__":
    main()
