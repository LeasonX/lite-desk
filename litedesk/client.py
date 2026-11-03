"""控制端 (Controller)

两层:
  RemoteClient -- 纯网络/协议层, 无 UI 依赖, 可被 GUI、脚本、自动化测试共用。
                  这是刻意和 RustDesk 学的: 它的 client.rs 也不和 Flutter UI 耦合。
  ControllerApp -- Tkinter 界面 (标准库, 零额外依赖, Win/mac/Linux 都有)。
                   以后换 Flutter/Qt 只换这一层, 协议层不动。
"""
from __future__ import annotations
import argparse, io, socket, threading, time
from PIL import Image
from . import protocol as P

class RemoteClient:
    def __init__(self, host: str, port: int, password: str):
        self.sock = socket.create_connection((host, port), timeout=10)
        mtype, payload = P.recv_msg(self.sock)
        assert mtype == P.HELLO, "expected HELLO"
        self.hello = P.parse_json(payload)
        P.send_json(self.sock, P.AUTH, {"digest": P.auth_digest(password, self.hello["nonce"])})
        mtype, payload = P.recv_msg(self.sock)
        if mtype != P.AUTH_OK:
            raise PermissionError(f"auth failed: {payload!r}")
        self.latest: Image.Image | None = None
        self.frame_count = 0
        self.acks: list[dict] = []
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()
    def _loop(self):
        try:
            while True:
                mtype, payload = P.recv_msg(self.sock)
                if mtype == P.FRAME:
                    _, _, _, jpeg = P.unpack_frame(payload)
                    img = Image.open(io.BytesIO(jpeg)); img.load()
                    with self._lock: self.latest, self.frame_count = img, self.frame_count + 1
                elif mtype == P.INPUT_ACK:
                    with self._lock: self.acks.append(P.parse_json(payload))
        except Exception:
            pass
    # 坐标传比例 (0~1), 见 protocol.py 说明
    def mouse(self, x: float, y: float, action="move", button="left", delta=0):
        P.send_json(self.sock, P.MOUSE, {"x": x, "y": y, "action": action, "button": button, "delta": delta})
    def key(self, key: str, action="down"):
        P.send_json(self.sock, P.KEY, {"key": key, "action": action})
    def set_quality(self, quality: int):
        P.send_json(self.sock, P.CONFIG, {"quality": quality})
    def wait_frames(self, n: int, timeout=10.0) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                if self.frame_count >= n: return True
            time.sleep(0.05)
        return False
    def close(self):
        try: self.sock.close()
        except OSError: pass

# ---------- GUI ----------
def run_gui(host: str, port: int, password: str):
    import tkinter as tk
    from PIL import ImageTk
    cli = RemoteClient(host, port, password)
    root = tk.Tk(); root.title(f"LiteDesk - {host}:{port}")
    canvas = tk.Canvas(root, bg="black", width=960, height=540); canvas.pack(fill="both", expand=True)
    state = {}
    def ratio(e):
        w, h = canvas.winfo_width(), canvas.winfo_height()
        return min(1, max(0, e.x / max(1, w))), min(1, max(0, e.y / max(1, h)))
    canvas.bind("<Motion>", lambda e: cli.mouse(*ratio(e)))
    canvas.bind("<ButtonPress-1>", lambda e: cli.mouse(*ratio(e), action="down"))
    canvas.bind("<ButtonRelease-1>", lambda e: cli.mouse(*ratio(e), action="up"))
    canvas.bind("<ButtonPress-3>", lambda e: cli.mouse(*ratio(e), action="down", button="right"))
    canvas.bind("<MouseWheel>", lambda e: cli.mouse(*ratio(e), action="wheel", delta=1 if e.delta > 0 else -1))
    root.bind("<KeyPress>", lambda e: cli.key(e.keysym, "down"))
    root.bind("<KeyRelease>", lambda e: cli.key(e.keysym, "up"))
    def tick():
        with cli._lock: img = cli.latest
        if img is not None:
            w, h = canvas.winfo_width(), canvas.winfo_height()
            photo = ImageTk.PhotoImage(img.resize((max(1, w), max(1, h))))
            state["photo"] = photo
            canvas.create_image(0, 0, anchor="nw", image=photo)
        root.after(50, tick)  # 20fps 上限刷新; 真正帧率由被控端决定
    tick(); root.mainloop()

def main():
    a = argparse.ArgumentParser(description="LiteDesk 控制端")
    a.add_argument("host"); a.add_argument("--port", type=int, default=9000)
    a.add_argument("--password", required=True)
    args = a.parse_args()
    run_gui(args.host, args.port, args.password)

if __name__ == "__main__":
    main()
