LiteDesk — macOS 包
===================

两种用法, 任选一种:

A. 免打包直接用 (电脑上有 Python 3.10+, 没有的话到 python.org 装, 或 brew install python)
   被控端: 双击 LiteDesk-Host.command, 记下显示的连接密码
   控制端: 双击 LiteDesk-Controller.command, 按提示输入被控端 IP 和密码
   (第一次双击会自动建虚拟环境并安装依赖, 需要联网)
   如果双击提示"无法打开, 因为来自身份不明的开发者": 右键该文件 > 打开 > 仍要打开。

   ★ 被控端必做 (不做就黑屏/控制不了, 这是 macOS 的系统限制, RustDesk 也一样):
     系统设置 > 隐私与安全性 > 屏幕录制: 给「终端」打开
     系统设置 > 隐私与安全性 > 辅助功能: 给「终端」打开
     改完后关掉终端重新双击启动。

B. 打成真正的 .app (发给没装 Python 的 Mac 用)
   双击 Build-APP.command, 完成后 dist/ 里就是 LiteDesk-Host 和 LiteDesk-Controller.app。
   打包分芯片: 在 Apple Silicon 的 Mac 上打出 arm64 版, Intel Mac 上打出 Intel 版, 不能混用。
   未签名 .app 首次打开同样右键 > 打开。

C. 不想在自己 Mac 上打包?
   把这个文件夹推到 GitHub, 仓库里带了 .github/workflows/build.yml,
   在 Actions 页面点 Run workflow, 云端会同时打出 arm64 和 Intel 两个 macOS 包供下载。

被控端 IP 怎么看: 系统设置 > Wi-Fi > 已连接网络的详情, 或终端运行 ipconfig getifaddr en0。
仅建议在局域网或 Tailscale/WireGuard 组网内使用, 不要把 9000 端口直接暴露到公网 (当前版本未加密)。
