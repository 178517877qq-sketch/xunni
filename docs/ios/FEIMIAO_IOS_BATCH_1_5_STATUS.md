# 肥喵记账 iOS：批次 1–5 状态

更新时间：2026-07-19

> **状态更正：用户已否决这一版通用 SwiftUI UI，旧版不能称为同款 iOS。以下 GRDB、备份、CRUD 和 CI 结果仍是可复用地基；根 Tab、系统模板首页、加载态和相关 UI“已完成”结论全部撤销。当前重建进度以 [`FEIMIAO_IOS_PARITY_CONTRACT.md`](FEIMIAO_IOS_PARITY_CONTRACT.md) 为准。**

## 当前同款重建里程碑

- 版本：`0.2.0 (2)`，基线提交 `5392cf0`。
- 已在工作树完成：推开式抽屉根壳、真实品牌素材、暖色启动/主页背景、无阻塞主页首帧、月份一致快照、安卓结构的汇总卡/筛选/按日账单/底部记账入口。
- 预算、统计与 AI 尚未接入真实数据层，本里程碑只显示真实的无预算和手动记账状态。
- Windows 无 Swift/Xcode 工具链；当前代码仍需 macOS CI 编译、XCTest、Simulator 冷启动和截图验收，CI 通过前不得宣称完成。

## 工作位置

- 工作树：`C:\tmp\xunni-ios-batch15`
- 分支：`codex/ios-feimiao-batch-1-5`
- 当前实现：`ios-app/FeiMiao` + `ios-app/FeiMiaoKit`
- 旧 `ios-app/QingJi*` 只作参考，当前 XcodeGen 不再构建它。

## 已实现

### 批次 1：工程与设计系统

- `project.yml` 已切到 `FeiMiao`，部署目标 iOS 18。
- SwiftUI 根 Tab、蓝灰/铜金/风险/健康语义色、深色模式适配已接入。
- Swift tools 已升至 6.1（业务源码保持 Swift 5 模式），AppIcon 与 11 张肥喵账本封面已进入当前 target。
- 启动阶段不在主线程打开数据库；首帧显示原生肥喵加载态，Launch Screen 使用明暗自适应背景。
- iOS CI 已切到新工程：SwiftPM 测试、XcodeGen、Simulator 构建/冷启动、Appetize ZIP、未签名 IPA。

### 批次 2：GRDB 与 Android v40 兼容

- 金额全程使用十进制定点文本。
- iOS 内部表保留 UUID、更新时间和软删除字段。
- Android `.zip/.db/.bak` 走只读映射导入，不直接作为 iOS 在线库。
- ZIP 会校验格式、版本、路径、文件清单、CRC 与 SHA-256，并限制解压规模。
- ZIP 数据库和收据改为流式解压与增量 SHA-256，不再把整包资产堆进内存；总量、数据库和单项资产均有独立上限，ZIP64 元数据也做防溢出检查。
- 导入前保留 SQLite 一致性安全备份（最多 3 份）；核心表替换在单个事务中完成。
- 收据复制到 iOS 沙盒并重写账单图片路径。

### 批次 3：基础资料 CRUD

- 账本：新增、编辑、加星、计入总账本、删除迁移、默认账本保护。
- 账户：类型、期初余额、净资产汇总；有历史账单的账户禁止物理删除。
- 账户支持归档/恢复：历史名称、余额和搜索保留，新记账只允许使用中账户；编辑历史账单不会偷偷改到账户列表第一项。
- 分类：支出/收入、两级层级、隐藏、增删改；仓储层限制跨类型和第三级。
- 标签：增删改和颜色预设。
- 基础设置键值读写及当前账本持久化。
- 账本管理可预览并选择 11 张竖版封面；隐藏父分类在只改名称时不会被静默重挂。

### 批次 4：首页、明细与搜索

- 首页显示当月支出/收入/结余和最近账单。
- 总账本只聚合 `include_in_total` 账本，切换结果会持久化。
- 明细按自然日分组，支出/收入/转账筛选，原生滑动编辑/删除。
- 搜索覆盖备注、分类、账户、账本、标签、金额和时间范围；输入做 180ms 防抖。
- 净额和账户余额均改为单次批量计算，去掉启动阶段的 N+1 全表查询。

### 批次 5：新增与编辑

- 支出、收入、转账新增/编辑。
- 日期和具体时分、账本、账户、两级分类、标签、备注。
- PhotosPicker 附件、待报销、不计收支。
- 转账强制不同账户，仓储层自动清理转账分类和待报销标记。
- 账单行显示备注主标题、分类小字、具体时间和转出→转入账户。
- 无准确时分的旧账单继续保持“未知时间”语义；只有用户主动补录后才变为精确时间。
- 图片在账单保存成功前只暂存在内存，取消、失败或反复更换不会留下孤儿文件；共享附件仍被其他账单引用时不会误删。
- 明细/搜索行改为真实语义按钮，补齐 VoiceOver 标签、导入遮罩隔离和 44pt 颜色触控目标。

## 自动化覆盖

- 当前共 28 个 XCTest 用例，已在 macOS CI 全部通过。
- Domain：金额精确运算、非法金额、时间精度存储键、120 个 Android 分类定义完全一致。
- Data：CRUD 重启持久化、总账本聚合、搜索、转账账户守恒、软删除、账户删除/归档保护、旧时间精度、共享附件引用、两级分类约束、设置读写。
- Import：Android v40 原始 DB、完整 ZIP、流式校验 asset media、收据恢复、哈希失败不改库、未来版本拒绝、畸形库不清空、安全备份可重开。

## 本轮本地证据

- Swift tree-sitter：28/28 个 Swift 文件解析成功，0 语法错误。
- `actionlint`：`.github/workflows/ios-ci.yml` 通过。
- YAML 与 Asset Catalog JSON 解析通过。
- AppIcon 为 1024×1024 RGB；11 张账本封面均为 420×560。
- Swift/Android 分类：120/120，键、名称、英文、emoji、类型、父级完全一致。
- `git diff --check`：通过（仅 Windows 的 LF→CRLF 提示）。

## macOS CI 交付证据

- GitHub Actions：`iOS CI #19`，run `29675262611`，提交 `1dc3124`。
- `FeiMiaoKit tests`：成功，28 个 XCTest 全部通过。
- `Simulator build and launch`：成功；完成 XcodeGen、Simulator 构建、安装、首次启动后 5 秒存活、主页截图、终止、第二次启动后 2 秒存活。
- `Unsigned device IPA`：成功；Release 设备构建和 IPA 完整性检查通过。
- `FeiMiao-Appetize`：7.71 MB，SHA-256 `fee4d29b5e995ef98749dc98248082a66a58daeacd09e770477809fe6c6f98bd`。
- `FeiMiao-unsigned-ipa`：3.36 MB，SHA-256 `5e0fec5203490019e5f254e0fa9319f680272184f92ecd978a86929a6489a872`。
- `FeiMiao-simulator-diagnostics`：177 KB，SHA-256 `2bafc2e505e3a1515d18fd852a73c126a385dcb279835166cddfbc174f510322`。
- `FeiMiao-device-build-diagnostics`：25.5 KB，SHA-256 `a629e3ce419c29a7d8ef5439b6b7fac0749cc20ab8421174a4c1b4bc6c3fd8be`。

## 剩余人工门禁

Appetize 手工冒烟尚未执行：切账本、搜索、新增、编辑、重启后仍存在。因此批次 1–5 的代码与自动化门禁已经完成，正式封板只差这一次人工交互验收；完成前不进入批次 6。
