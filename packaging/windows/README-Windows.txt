LiteDesk — Windows 包
====================

两种用法, 任选一种:

A. 免打包直接用 (电脑上有 Python 3.10+)
   被控端: 双击 LiteDesk-Host.bat, 记下窗口里显示的连接密码
   控制端: 双击 LiteDesk-Controller.bat, 按提示输入被控端 IP 和密码
   (第一次双击会自动安装依赖, 需要联网)

B. 打成真正的 .exe (发给没装 Python 的电脑用)
   双击 Build-EXE.bat, 完成后 dist\ 里就是:
     LiteDesk-Host.exe        被控端 (带黑窗口, 用来显示连接密码)
     LiteDesk-Controller.exe  控制端
   未签名的 exe 首次运行会被 SmartScreen 提示, 点「更多信息 > 仍要运行」即可。

C. 不想在自己电脑上打包?
   把这个文件夹推到 GitHub, 仓库里带了 .github/workflows/build.yml,
   在 Actions 页面点 Run workflow, 云端 Windows 机器会自动打出 .exe 并提供下载。

被控端 IP 怎么看: 被控电脑上按 Win+R 输入 cmd, 运行 ipconfig, 找 IPv4 地址 (如 192.168.1.20)。
仅建议在局域网或 Tailscale/WireGuard 组网内使用, 不要把 9000 端口直接暴露到公网 (当前版本未加密)。
