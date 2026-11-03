"""极简线协议: [4B 大端长度][1B 类型][payload]

为什么不用现成协议去套:
- RustDesk 用 protobuf + VP8/VP9/AV1 + 自研 TCP/UDP 封装, 强但重, 新手改不动。
- 这里只保留一条 TCP 长连接 + 长度前缀分帧。任何语言都能在 50 行内复刻,
  这就是跨端成本最低的协议形态。代价和升级路径见 README。

消息类型:
  HELLO/AUTH/AUTH_OK/AUTH_FAIL/CONFIG  -- JSON (utf-8)
  FRAME                                -- [2B w][2B h][8B ts_ms] + JPEG 字节 (毫秒时间戳装不进 4B)
  MOUSE/KEY/INPUT_ACK/PING/PONG        -- JSON (utf-8)
坐标一律传 0~1 的比例值, 而不是像素: 控制端窗口大小、被控端分辨率都不同,
传比例才能天然适配 1080p->4K、横屏->竖屏, 这是相对像素坐标的一个小改进。
"""
from __future__ import annotations
import hashlib, json, socket, struct

HELLO, AUTH, AUTH_OK, AUTH_FAIL, CONFIG = 1, 2, 3, 4, 5
FRAME = 16
MOUSE, KEY, INPUT_ACK = 32, 33, 34
PING, PONG = 48, 49

_HDR = struct.Struct("!IB")      # length(含type), type
_FRAME_META = struct.Struct("!HHQ")

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return bytes(buf)

def send_msg(sock, mtype: int, payload: bytes):
    sock.sendall(_HDR.pack(len(payload) + 1, mtype) + payload)

def recv_msg(sock) -> tuple[int, bytes]:
    (length, mtype) = _HDR.unpack(_recv_exact(sock, _HDR.size))
    if length < 1 or length > 64 * 1024 * 1024:
        raise ValueError(f"bad frame length {length}")
    return mtype, _recv_exact(sock, length - 1)

def send_json(sock, mtype: int, obj: dict):
    send_msg(sock, mtype, json.dumps(obj, ensure_ascii=False).encode())

def parse_json(payload: bytes) -> dict:
    return json.loads(payload.decode())

def pack_frame(width: int, height: int, ts_ms: int, jpeg: bytes) -> bytes:
    return _FRAME_META.pack(width, height, ts_ms) + jpeg

def unpack_frame(payload: bytes):
    w, h, ts = _FRAME_META.unpack(payload[:_FRAME_META.size])
    return w, h, ts, payload[_FRAME_META.size:]

def auth_digest(password: str, nonce: str) -> str:
    """挑战-应答: 密码不走明文, 服务端只发一次性 nonce。"""
    return hashlib.sha256(f"{password}:{nonce}".encode()).hexdigest()
