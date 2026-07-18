# 肥喵记账 iOS：批次 1–5 交付合同

> 基线：Android `1.197.0+199` / SQLite v40；iOS 从最终业务语义起步，不复刻历史错误。

## 不可变原则

- 同一份账务数据在 Android 与 iOS 上必须得到相同的净额、归属日和账户变化。
- 原生 iOS 交互优先：`TabView`、`NavigationStack`、`List`、`Form`、`sheet`、`DatePicker`、`Menu`、`PhotosPicker`、SF Symbols。
- 品牌部分保留肥喵猫咪、蓝灰主色、铜金收入、橙色风险、预算健康绿和账本封面。
- 金额使用十进制定点字符串存储，禁止用二进制浮点数写库。
- 所有同步候选实体保留 UUID 与更新时间；删除语义不得依赖物理行消失。
- iOS 不读取其他 App 通知；自动记账由快捷指令、分享扩展、OCR 与 Widget 在后续批次替代。

## 批次 1–5 范围

1. 原生工程外壳、语义设计系统、CI 与 Appetize 构建。
2. GRDB/SQLite 数据地基；兼容读取肥喵备份中的 `database/qingji.db` 核心表。
3. 账本、账户、两级分类、标签和基础设置 CRUD。
4. 首页、账本切换、按日账单、搜索筛选与内容优先排版。
5. 手动新增和编辑支出/收入/转账，含日期时间、账户、分类、标签、备注、图片、不计收支和待报销。

## 明确排除

- 退款/报销到账与 checkpoint 属批次 6，本批只保存 `reimbursable` 标记。
- 预算 V2、统计全量、AI、资产与系统扩展分别进入后续批次。
- 不把旧 SwiftData 原型数据当作生产迁移来源；旧原型仅保留作参考。

## 每批门禁

- 纯 Swift 规则测试与 GRDB 集成测试通过。
- XcodeGen 生成工程，macOS CI 的 Swift 测试和 Simulator build 通过。
- Appetize 真实打开并完成至少：切账本、搜索、新增、编辑、重启后仍存在。
- 提交只包含该批文件，存在清晰回退点。
