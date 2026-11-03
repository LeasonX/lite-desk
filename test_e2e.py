#!/usr/bin/env python3
"""无头端到端测试: 自己拉起 Mock 被控端 -> 连接/鉴权 -> 收帧 -> 发键鼠 -> 校验回执与画面变化。
用法: python3 test_e2e.py   (退出码 0 = 通过, 并生成 frame_preview.jpg)
"""
import subprocess, sys, time
from litedesk.client import RemoteClient

PORT, PASSWORD = 19001, "test123"

def main():
    proc = subprocess.Popen([sys.executable, "host.py", "--mock", "--port", str(PORT),
                             "--password", PASSWORD, "--fps", "15"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # 先测错误密码 (被控端是单会话顺序处理, 必须排在正常连接之前)
        for _ in range(50):
            try:
                RemoteClient("127.0.0.1", PORT, "wrong"); raise SystemExit("错误密码居然通过了")
            except PermissionError:
                print("[ok] 错误密码被拒绝"); break
            except OSError:
                time.sleep(0.2)

        cli = None
        for _ in range(50):  # 等服务起来
            try:
                cli = RemoteClient("127.0.0.1", PORT, PASSWORD); break
            except OSError:
                time.sleep(0.2)
        assert cli is not None, "连不上被控端"
        print(f"[ok] 鉴权通过, HELLO={cli.hello}")

        assert cli.wait_frames(3), "收不到画面帧"
        with cli._lock: first = cli.latest.copy()
        print(f"[ok] 收到画面 {cli.frame_count} 帧, 尺寸={first.size}")

        cli.mouse(0.25, 0.75, action="move"); cli.mouse(0.25, 0.75, action="down"); cli.mouse(0.25, 0.75, action="up")
        cli.key("a", "down"); cli.key("a", "up")
        time.sleep(0.8)
        with cli._lock: acks = list(cli.acks)
        mouse_acks = [a for a in acks if a.get("kind") == "mouse" and a.get("action") == "down"]
        assert mouse_acks and abs(mouse_acks[0]["x"] - 0.25) < 1e-6, f"鼠标回执不对: {acks}"
        assert any(a.get("kind") == "key" and a.get("key") == "a" for a in acks), f"键盘回执缺失: {acks}"
        print(f"[ok] 控制闭环: 收到 {len(acks)} 条 INPUT_ACK, 光标已移到 (0.25, 0.75) 并点击")

        assert cli.wait_frames(cli.frame_count + 2), "控制后画面未继续更新"
        with cli._lock: cli.latest.save("frame_preview.jpg")
        print("[ok] 控制后画面持续更新, 预览已存 frame_preview.jpg")
        cli.close()
        print("PASS: LiteDesk 端到端链路通 (鉴权/画面/鼠标/键盘)")
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()
