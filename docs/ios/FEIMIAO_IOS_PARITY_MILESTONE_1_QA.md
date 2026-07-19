# 肥喵记账 iOS 同款里程碑 1 验收记录

日期：2026-07-19

## 范围

- 回退基线：`5392cf0`。
- 版本：`0.2.0 (2)`。
- 只修改 `ios-app`、`docs/ios`；Android 工作树和 APK 未修改。
- 本里程碑覆盖设计 token/品牌素材、推开式抽屉、首页月份快照、首页汇总/筛选/日卡/底部入口和启动顺序。
- 预算、统计、AI、自动记账仍属后续里程碑，不用假数据占位。

## 本地证据

- `git diff --check`：通过，仅有 Windows LF/CRLF 提示。
- Asset Catalog `Contents.json`：3 个均可解析。
- iOS Resources：11 张账本封面、1 张 Logo、3 张首页猫图存在；猫图和 Logo 均有有效 alpha。
- 当前 SwiftUI target 已移除五栏 `TabView` 和 `cat.fill` 品牌占位。
- 三轮只读静态审查已检查首页 API、根导航、SQL、退款净额、月份边界、资源路径和启动竞态；发现的问题已在提交前修正。

## 未在 Windows 验证

- Windows 本机没有 Swift、Xcode、XcodeGen 和 iOS Simulator，不能把静态审查当作编译通过。
- Android 专用 AVD 的 ADB transport 持续 offline，未能从现有 APK 重新抓图；已改用当前 Android 源码和用户已有真实截图作为基准，失败复现另有记录。
- macOS CI 必须继续执行 SwiftPM 测试、XcodeGen、Simulator build、两次冷启动、截图和未签名 IPA 构建。CI 全绿且截图人工对比前，本里程碑不标记完成。
