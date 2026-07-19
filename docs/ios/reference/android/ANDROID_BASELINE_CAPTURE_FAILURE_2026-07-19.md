# Android 视觉基准采集失败记录

- 时间：2026-07-19 21:28-21:30（Asia/Shanghai）
- 结果：未生成首页、抽屉、记账入口截图或 UI tree。
- 阻塞点：专用 AVD 已进入 emulator 进程，但 ADB transport 始终为 `offline`，无法安装 APK、启动应用、执行 `uiautomator dump` 或 `screencap`。
- 约束遵守：未重建 APK；未修改 Android/iOS 产品代码；未终止或重启 emulator/qemu 进程。

## 指定 APK

```text
Path: C:\src\xunni-codex\ci-artifacts\releases\feimiao-codex-v1.202.0-204.apk
Size: 120826320 bytes
SHA256: 3C178D9A6EE37DE806B281BD031058AD60A355E690844099534BAC421C566CC3
Package: com.qingji.qingji.codex
Version: 1.202.0 (versionCode 204)
Min SDK: 24
Target SDK: 36
```

APK 元数据命令：

```powershell
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\build-tools\37.0.0\aapt.exe' dump badging 'C:\src\xunni-codex\ci-artifacts\releases\feimiao-codex-v1.202.0-204.apk'
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\src\xunni-codex\ci-artifacts\releases\feimiao-codex-v1.202.0-204.apk'
```

## AVD 与工具链

已运行的专用 AVD 进程命令行：

```text
emulator.exe -avd codex_ascii_api35 -port 5584 -no-window -no-metrics -gpu swiftshader_indirect -no-snapshot-load -no-snapshot-save -no-boot-anim -no-audio -verbose
```

监听端口：`127.0.0.1:5584`、`127.0.0.1:5585`。进程：`emulator.exe` PID 29560、`qemu-system-x86_64-headless.exe` PID 25324。

```text
Android Debug Bridge 1.0.41 / 37.0.0-14910828
Android emulator 36.6.11.0 / build 15507667
```

## 复现命令与结果

初始检查：

```powershell
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\platform-tools\adb.exe' devices -l
```

```text
List of devices attached
127.0.0.1:5585         offline transport_id:2
emulator-5584          offline transport_id:1
```

第一次恢复尝试：

```powershell
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\platform-tools\adb.exe' reconnect offline
```

约 25 秒内每 5 秒轮询一次，五次均为：

```text
emulator-5584          offline transport_id:3
```

第二次恢复尝试：

```powershell
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\platform-tools\adb.exe' kill-server
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\platform-tools\adb.exe' start-server
& 'C:\Users\寻逆啊\AppData\Local\Android\Sdk\platform-tools\adb.exe' connect 127.0.0.1:5585
```

结果：`failed to connect to 127.0.0.1:5585`；随后轮询仍显示：

```text
127.0.0.1:5585         offline transport_id:1
emulator-5584          offline transport_id:2
```

## 未执行项

以下命令依赖 `device` 状态，因此未执行，避免产生误导性空文件：

```powershell
adb -s emulator-5584 install -r <指定 APK>
adb -s emulator-5584 shell am start -n <package/activity>
adb -s emulator-5584 exec-out uiautomator dump /dev/tty
adb -s emulator-5584 exec-out screencap -p
```

失败原因不是 APK 构建或应用启动错误，而是 APK 安装之前的 ADB transport 离线。
