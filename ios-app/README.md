# 肥喵记账 iOS

当前生产方向是 `FeiMiao`：用 SwiftUI 原生实现 Android 肥喵记账的同款 iOS 版本。Android 当前产品是可见界面、信息架构、品牌素材、功能语义和操作路径的唯一基准；SwiftUI 只负责实现，不授权改成通用 iOS 模板。系统原生能力只用于键盘、安全区、权限、触感反馈和侧滑返回等不会改变产品身份的边界。

最新不可变约束见 [`../docs/ios/FEIMIAO_IOS_PARITY_CONTRACT.md`](../docs/ios/FEIMIAO_IOS_PARITY_CONTRACT.md)。旧批次 1–5 合同只保留数据地基和历史记录价值；其中 `TabView`、系统大标题、通用 `List/Form` 优先等展示决策已作废。

## 当前工程

```text
ios-app/
├── project.yml               # XcodeGen：生成 FeiMiao.xcodeproj
├── FeiMiao/                  # 当前 SwiftUI App
│   ├── App/                  # AppStore、推开式抽屉根壳与启动入口
│   ├── Components/           # 账单行、账本菜单、空状态
│   ├── Design/               # 语义颜色与通用卡片
│   └── Views/                # 首页、明细、搜索、记账、资料管理
├── FeiMiaoKit/               # 当前 SwiftPM 核心包
│   ├── Sources/FeiMiaoDomain # 定点金额、实体、稳定分类键
│   ├── Sources/FeiMiaoData   # GRDB 仓储与 Android 备份导入
│   └── Tests/                # 纯规则和数据库集成测试
├── QingJi/                   # 旧 SwiftData 原型，仅作参考
├── QingJiCore/               # 旧原型核心包
└── QingJiWidget/             # 旧原型小组件
```

`QingJi` 不再由当前 `project.yml` 构建，也不是新版数据迁移来源。

## 本地运行

完整 App 需要 macOS、Xcode 26 和 XcodeGen；部署目标为 iOS 18，因此也可在更新系统上运行。

```bash
brew install xcodegen
cd ios-app
xcodegen generate --spec project.yml
open FeiMiao.xcodeproj
```

在 Xcode 中选择 `FeiMiao` scheme。模拟器构建不需要签名；真机安装需要选择自己的 Apple Team 并换成可用的 Bundle Identifier。

## 自动化测试

```bash
swift test --package-path ios-app/FeiMiaoKit --parallel
```

测试覆盖十进制定点金额、稳定分类树、CRUD 重启持久化、总账本聚合、搜索、转账账户守恒、软删除、账户归档、时间精度、附件引用，以及 Android v40 原始数据库/完整 ZIP 备份导入。

Windows 本机没有 iOS SDK，不能编译 SwiftUI App；`.github/workflows/ios-ci.yml` 会在 macOS 上运行 SwiftPM 测试、生成 Xcode 工程、构建并冷启动 Simulator App，再生成两个下载产物：

- `FeiMiao-Appetize.zip`：上传到 Appetize 的模拟器包。
- `FeiMiao-unsigned.ipa`：未签名设备包，需用自己的 Apple ID/证书重签。

## Android 备份兼容

设置页可选择 Android 肥喵导出的 `.zip`，也兼容旧 `.db/.bak`。导入流程不会直接把 Android 数据库作为 iOS 在线库使用，而是：

1. 校验备份格式、路径、文件清单、CRC 和 SHA-256；
2. 只读解析 Android 核心表；
3. 把缺失的 iOS 同步字段补为稳定值；
4. 先用 SQLite 一致性快照保留导入前的 iOS 数据（最多 3 份）；
5. 在单个 SQLite 事务中替换账本、账户、分类、标签和账单；
6. 以流式方式解压数据库和收据并设置逐项/总量上限，避免大备份占满内存；
7. 把备份内收据复制到 iOS 沙盒并重写附件路径。

API Key 不从 Android 备份带入。预算 V2、统计、AI、资产以及退款/报销到账交互不属于批次 1–5。
