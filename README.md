# LiteDesk — 极简跨端远程桌面

参考 [RustDesk](https://github.com/rustdesk/rustdesk)（约 12.8 万 star，Rust + Flutter，AGPL-3.0）做的**教学级精简版**：
只保留「能远程连接、能看画面、能操作」这一条核心链路，同一套 Python 代码跑 Windows / macOS / Linux。
代码总量约 500 行，协议、被控端、控制端各一个文件，读完就能改。

> ⚠️ 定位：局域网 / 自有设备 / 学习原理。**不要直接暴露到公网**——原因和补法在文末「安全与局限」。

---

## 1. 先拆 RustDesk：它到底由什么组成

| RustDesk 模块 | 职责 | LiteDesk 对应 |
|---|---|---|
| `libs/scrap` | 抓屏（DXGI / X11 / Quartz） | `host.RealScreen`（mss 薄封装）+ `MockScreen` |
| `libs/enigo` | 跨平台键鼠注入 | `host.InputSink`（pynput 薄封装） |
| `libs/hbb_common` | 视频编解码、TCP/UDP 封装、配置 | `protocol.py`（长度前缀分帧 + JSON 控制信道） |
| `src/server` | 画面/输入/音频/剪贴板服务、会话管理 | `host.Host._session` |
| `src/client.rs` | 发起对端连接（与 UI 解耦） | `client.RemoteClient` |
| `src/rendezvous_mediator.rs` | 与 `rustdesk-server` 通信，做 TCP 打洞 / 中继兜底 | ❌ 砍掉（见 §4，这也是它最难的部分） |
| `flutter/` | 桌面 + 移动端 UI | `client.ControllerApp`（Tkinter，标准库零依赖） |
| 视频编码 | VP8/VP9/AV1 + 硬编、码率自适应 | JPEG 帧（见 §3 取舍） |
| 其它 | 文件传输、剪贴板、音频、TCP 隧道、多显示器、地址簿… | ❌ 全部砍掉，只留键鼠 + 画面 |

**一句话本质**：远程桌面 = ①不停抓屏编码发出去 + ②把对方的键鼠事件在本地重放 + ③解决「两台不在同一网络的机器怎么连上」。①②不难，③（NAT 穿透 + 中继）才是 RustDesk 一半以上的工程量。

## 2. 架构与数据流

```
被控端 Host                                  控制端 Controller
┌─────────────────────────────┐   TCP 长连接   ┌────────────────────────┐
│ 抓屏 mss ─► Pillow JPEG 编码 │ ── FRAME ───► │ 解码 ─► Tkinter Canvas │
│ 注入 pynput ◄─ 键鼠事件重放  │ ◄─ MOUSE/KEY─ │ 采集窗口键鼠事件        │
│ 鉴权: nonce + SHA256(密码)   │ ◄─ AUTH ───── │ RemoteClient (无UI层)  │
└─────────────────────────────┘   CONFIG/PING  └────────────────────────┘
        协议: [4B长度][1B类型][payload]，控制消息用 JSON，画面用 二进制头+JPEG
        坐标: 传 0~1 比例值而非像素 → 分辨率/窗口尺寸不同也能对齐
```

连接时序：`HELLO(nonce, 分辨率) → AUTH(SHA256(密码:nonce)) → AUTH_OK → 循环[FRAME / MOUSE / KEY / INPUT_ACK]`

## 3. 关键取舍（为什么这样简化）

1. **JPEG 帧 vs 视频编码**：JPEG 每帧独立、无状态、30 行能写完，12fps 下局域网够用（960×540 约 30–60KB/帧）。
   代价是带宽和延迟远不如 VP8/H.264——看视频、拖窗口会糊会卡。这是**故意的**：先通链路，再换编码（见 §5 第 1 条）。
2. **TCP 直连 vs 打洞/中继**：同局域网、或被控端有公网 IP/做了端口转发时直连最简单。跨互联网先用 Tailscale/WireGuard 组网再直连，是个人使用性价比最高的「作弊解法」。
3. **单会话**：同时只允许一个控制端。少了并发仲裁、旁观模式，但避免了「两个人抢鼠标」，且默认更安全。
4. **Mock 降级**：无显示器、无抓屏权限时自动切换合成桌面，链路照样可测。真实软件最常见的「装上打不开」多半死在权限/显示服务，降级路径必须一开始就设计。
5. **UI 用 Tkinter**：丑，但标准库自带、零安装。要好看再换 Flutter/Qt，协议层不用动——分层就是为了这一天。

## 4. 相对 RustDesk 的改进点（小而实，不是堆功能）

这些是读 RustDesk 时觉得「如果重写一个简洁版可以做得更好」的地方，本项目已落地前 4 条：

1. **比例坐标代替像素坐标**：RustDesk 要在客户端做分辨率协商与缩放换算；比例坐标天然适配不同分辨率、缩放和窗口尺寸，控制端零协商。
2. **默认随机一次性密码 + 挑战应答**：密码不走明文、不存明文比对，服务端只发 nonce。本项目默认不设固定密码、每次启动随机生成（仿 RustDesk 临时密码，但做成默认行为而非可选项）。
3. **协议层与 UI 彻底分离 + 无头可测**：`RemoteClient` 没有任何 UI 依赖，一条 `test_e2e.py` 就能自动验证鉴权/画面/键鼠闭环。RustDesk 的端到端测试门槛要高得多。
4. **能力降级而非启动失败**：抓屏/注入不可用时降级 Mock 并明示，而不是闪退或黑屏——对新手和跨平台分发更友好。
5. **（思路，未落地）配置只有 3 个旋钮**：fps / 画质 / 密码。RustDesk 设置项上百，对普通用户是负担；简洁版应坚持「高级设置折叠、默认能用」。
6. **（思路，未落地）先组网后远程**：与其自研打洞/中继，不如官方推荐 Tailscale/WireGuard 作为传输层，把精力留给画面与操作体验——小团队做基础设施是必输的仗。

## 5. 改进路线图（按性价比排序）

| 优先级 | 事项 | 做法 |
|---|---|---|
| P0 | 加密传输 | 现在是明文 TCP+哈希鉴权。套 TLS（`ssl` 标准库包一层 socket 即可）或走 WireGuard |
| P0 | macOS/Linux 平台坑 | macOS 录屏+辅助功能权限引导；Linux Wayland 换 PipeWire/portal 抓屏、uinput 注入 |
| P1 | 真视频编码 | PyAV/ffmpeg 接 H.264 硬编 + 只传变化区域，帧率拉到 30，带宽降一个量级 |
| P1 | NAT 穿透/中继 | STUN 打洞（UDP）→ 失败走自建中继转发；或直接集成 WebRTC（aiortc），打洞+加密+媒体一次解决 |
| P1 | 自适应码率 | 按 PING 往返时延和丢帧动态调 quality/fps（本项目已有 CONFIG 信道，补策略即可） |
| P2 | 剪贴板/文件传输/多屏 | 各是一条独立信道，协议加消息类型即可，别和画面流耦合 |
| P2 | 换 UI + 打包 | Flutter 或 Tauri 做界面，PyInstaller 打成单文件分发；移动端控制需重做触控手势映射 |
| P3 | 正式身份体系 | 设备 ID、密钥对（学 RustDesk 的公钥确认）、连接确认弹窗、无人值守密码与 2FA |

## 6. 运行

```bash
pip install -r requirements.txt     # Pillow 必需; mss/pynput 真实模式才用

# 被控端（真实桌面）
python3 host.py                     # 控制台会打印随机连接密码
# 被控端（无显示环境先体验/测试）
python3 host.py --mock --password 123456

# 控制端（另一台机器，或本机另一个终端连 127.0.0.1）
python3 controller.py <被控端IP> --password 123456

# 无头端到端自测（拉起 Mock 被控端，验证鉴权→画面→鼠标→键盘全链路）
python3 test_e2e.py
```

跨端说明：同一套代码在 Windows/macOS/Linux 均可运行；Python 3.10+。真实抓屏/注入依赖 mss/pynput 对各平台原生 API 的封装，这正是「跨端」的实现方式——差异被库吃掉，业务代码一份。

## 7. 安全与局限（说清楚，不藏）

- **明文传输**：当前版本画面与键鼠未加密，只适合可信局域网或 VPN 内使用，上公网前必须先做 P0 的 TLS。
- **密码强度**：6 位随机码只防顺手牵羊，抗不了暴力破解（暂无限流）；公网场景换长密码+限流+密钥对。
- **权限**：被控端等于把键鼠交给对方，只给可信的人连接；用完关掉进程即断开，无后台常驻、无开机自启（这点比装正式远控软件更干净）。
- **性能上限**：JPEG+TCP 在高延迟网络下会卡顿、拖影；这是 §5 P1 解决的问题，不掩饰。

## 打包成 Windows / macOS 程序

PyInstaller 不是交叉编译器：在哪个系统打包，就只能产出哪个系统的程序，Linux 上打不出 `.exe`/`.app`。本项目给了两条路：

1. **在本机打包**：在目标电脑上运行 `python3 build.py`（Windows 用包里的 `Build-EXE.bat`、macOS 用 `Build-APP.command`），产出在 `dist/`：Windows 是 `LiteDesk-Host.exe` + `LiteDesk-Controller.exe`；macOS 是 `LiteDesk-Host` + `LiteDesk-Controller.app`。未签名程序首次运行会撞 SmartScreen / Gatekeeper，按包内说明放行即可。
2. **云端打包（推荐，不用有对应电脑）**：把仓库推到 GitHub，`.github/workflows/build.yml` 会在 Windows、macOS（arm64 + Intel）云机器上自动执行同一个 `build.py`，并在打包后自动冒烟测试被控端，产物在 Actions 里下载，打 tag 时自动挂到 Release。

另有免打包的双击启动器：Windows 包里的 `.bat`、macOS 包里的 `.command`，需要电脑上有 Python 3.10+，首次运行自动装依赖。

## 文件结构

```
lite-desk/
├── litedesk/protocol.py   # 线协议: 分帧、消息类型、挑战应答鉴权
├── litedesk/host.py       # 被控端: 抓屏(Real/Mock) + 注入 + 会话服务
├── litedesk/client.py     # 控制端: RemoteClient 协议层 + Tkinter GUI
├── host.py / controller.py# 两个启动入口
├── test_e2e.py            # 无头端到端测试
└── frame_preview.jpg      # 测试时保存的一帧远端画面
```
