"""被控端 (Host)

职责对应 RustDesk 的 src/server + libs/scrap(抓屏) + libs/enigo(键鼠注入),
但每一层都换成跨平台的薄封装, 失败时自动降级, 不让程序直接崩掉:
  抓屏: mss (Win: GDI/DXGI, mac: Quartz, Linux: X11) -> 无显示环境降级 MockScreen
  注入: pynput (Win32 / Quartz / X11 的统一封装)   -> 无权限/无显示时降级 MockSink
Mock 不是玩具: 它让整条链路 (协议/鉴权/画面/控制闭环) 在 CI 和无头机器上可测。
真实使用时 macOS 需在系统设置里给终端/应用开「屏幕录制 + 辅助功能」,
Windows 需注意 UAC 安全桌面、Linux Wayland 下抓屏/注入受限 (RustDesk 同样有此问题,
它靠 PipeWire/xdg-portal 绕, 这是后续第一个要补的平台坑)。
"""
from __future__ import annotations
import argparse, io, secrets, socket, threading, time
from PIL import Image, ImageDraw
from . import protocol as P

# ---------- 画面源 ----------
class MockScreen:
    """合成桌面: 背景+时钟+光标+最后按键。输入会真实改变下一帧画面, 形成可验证闭环。"""
    def __init__(self, w=960, h=540):
        self.width, self.height = w, h
        self.cursor = (0.5, 0.5)
        self.last_key, self.clicks = "", 0
    def grab(self) -> Image.Image:
        img = Image.new("RGB", (self.width, self.height), (32, 42, 68))
        d = ImageDraw.Draw(img)
        for x in range(0, self.width, 80):
            d.line([(x, 0), (x, self.height)], fill=(44, 56, 86))
        for y in range(0, self.height, 80):
            d.line([(0, y), (self.width, y)], fill=(44, 56, 86))
        d.rectangle([40, 40, 430, 150], fill=(52, 68, 105))
        d.text((60, 60), "LiteDesk - Mock Desktop", fill=(255, 255, 255))
        d.text((60, 90), time.strftime("%H:%M:%S"), fill=(180, 220, 255))
        d.text((60, 120), f"clicks={self.clicks}  last_key={self.last_key!r}", fill=(180, 220, 255))
        cx, cy = int(self.cursor[0] * self.width), int(self.cursor[1] * self.height)
        d.ellipse([cx-9, cy-9, cx+9, cy+9], outline=(255, 210, 60), width=3)
        d.line([(cx-14, cy), (cx+14, cy)], fill=(255, 210, 60))
        d.line([(cx, cy-14), (cx, cy+14)], fill=(255, 210, 60))
        return img

class RealScreen:
    def __init__(self):
        import mss  # 延迟导入: 没装/无显示时不影响 Mock 路径
        self._mss = mss.mss()
        mon = self._mss.monitors[1]
        self.width, self.height = mon["width"], mon["height"]
    def grab(self) -> Image.Image:
        raw = self._mss.grab(self._mss.monitors[1])
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

def make_screen(mock: bool):
    if not mock:
        try:
            return RealScreen(), False
        except Exception as e:
            print(f"[host] 真实抓屏不可用 ({e}), 降级 MockScreen")
    return MockScreen(), True

# ---------- 输入注入 ----------
class InputSink:
    def __init__(self, screen, is_mock: bool):
        self.screen, self.is_mock = screen, is_mock
        self._mouse = self._kb = None
        if not is_mock:
            try:
                from pynput import mouse, keyboard
                self._mouse, self._kb = mouse.Controller(), keyboard.Controller()
            except Exception as e:
                print(f"[host] pynput 不可用 ({e}), 输入仅记录不注入")
    def mouse(self, ev: dict):
        x, y = float(ev.get("x", .5)), float(ev.get("y", .5))
        if isinstance(self.screen, MockScreen):
            self.screen.cursor = (x, y)
            if ev.get("action") == "down":
                self.screen.clicks += 1
        if self._mouse:
            w = getattr(self.screen, "width", 1920); h = getattr(self.screen, "height", 1080)
            self._mouse.position = (int(x * w), int(y * h))
            from pynput.mouse import Button
            btn = Button.right if ev.get("button") == "right" else Button.left
            if ev.get("action") == "down": self._mouse.press(btn)
            elif ev.get("action") == "up": self._mouse.release(btn)
            elif ev.get("action") == "wheel": self._mouse.scroll(0, int(ev.get("delta", 0)))
    def key(self, ev: dict):
        k = str(ev.get("key", ""))
        if isinstance(self.screen, MockScreen) and ev.get("action") == "down":
            self.screen.last_key = k
        if self._kb and k:
            try:
                if ev.get("action") == "down": self._kb.press(k if len(k) == 1 else getattr(__import__("pynput.keyboard", fromlist=["Key"]), "Key")[k])
                elif ev.get("action") == "up": self._kb.release(k if len(k) == 1 else getattr(__import__("pynput.keyboard", fromlist=["Key"]), "Key")[k])
            except Exception:
                pass  # 特殊键映射不全时不中断会话, 完整键码表是后续工作

# ---------- 服务端 ----------
class Host:
    def __init__(self, port=9000, password="", fps=12, quality=60, mock=False):
        self.port, self.password = port, password or secrets.token_hex(3)  # 默认随机6位码, 仿 RustDesk 临时密码
        self.fps, self.quality = fps, quality
        self.screen, self.is_mock = make_screen(mock)
        self.sink = InputSink(self.screen, self.is_mock)
        self._cfg_lock = threading.Lock()
    def serve_forever(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port)); srv.listen(1)
        print(f"[host] 监听 :{self.port}  连接密码={self.password}  mock={self.is_mock}  (Ctrl+C 退出)")
        while True:
            conn, addr = srv.accept()
            print(f"[host] 连接来自 {addr}")
            try: self._session(conn)
            except Exception as e: print(f"[host] 会话结束: {e}")
            finally:
                try: conn.close()
                except OSError: pass
    def _session(self, conn: socket.socket):
        nonce = secrets.token_hex(16)
        P.send_json(conn, P.HELLO, {"version": "0.1", "nonce": nonce,
                      "width": self.screen.width, "height": self.screen.height, "mock": self.is_mock})
        mtype, payload = P.recv_msg(conn)
        if mtype != P.AUTH or P.parse_json(payload).get("digest") != P.auth_digest(self.password, nonce):
            P.send_json(conn, P.AUTH_FAIL, {"reason": "bad password"}); conn.close(); return
        P.send_json(conn, P.AUTH_OK, {})
        stop = threading.Event()
        threading.Thread(target=self._recv_loop, args=(conn, stop), daemon=True).start()
        interval = 1.0 / self.fps
        while not stop.is_set():
            t0 = time.time()
            img = self.screen.grab()
            with self._cfg_lock: q = self.quality
            buf = io.BytesIO(); img.save(buf, "JPEG", quality=q)
            try:
                P.send_msg(conn, P.FRAME, P.pack_frame(img.width, img.height, int(t0 * 1000), buf.getvalue()))
            except OSError: break
            time.sleep(max(0.0, interval - (time.time() - t0)))  # 简易限帧; 自适应码率见 README 路线图
        conn.close()
    def _recv_loop(self, conn, stop):
        try:
            while True:
                mtype, payload = P.recv_msg(conn)
                if mtype == P.MOUSE:
                    ev = P.parse_json(payload); self.sink.mouse(ev)
                    P.send_json(conn, P.INPUT_ACK, {"kind": "mouse", **ev})
                elif mtype == P.KEY:
                    ev = P.parse_json(payload); self.sink.key(ev)
                    P.send_json(conn, P.INPUT_ACK, {"kind": "key", **ev})
                elif mtype == P.CONFIG:
                    cfg = P.parse_json(payload)
                    with self._cfg_lock: self.quality = max(20, min(95, int(cfg.get("quality", self.quality))))
                elif mtype == P.PING:
                    P.send_json(conn, P.PONG, P.parse_json(payload))
        except Exception:
            stop.set()

def main():
    a = argparse.ArgumentParser(description="LiteDesk 被控端")
    a.add_argument("--port", type=int, default=9000)
    a.add_argument("--password", default="")
    a.add_argument("--fps", type=int, default=12)
    a.add_argument("--quality", type=int, default=60)
    a.add_argument("--mock", action="store_true", help="合成桌面 (无显示环境/测试)")
    args = a.parse_args()
    Host(args.port, args.password, args.fps, args.quality, args.mock).serve_forever()

if __name__ == "__main__":
    main()
