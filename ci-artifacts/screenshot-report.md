# Android / iOS 截图对比报告

已采集并比较：0/39；缺失或无效：39。

| 功能 | 状态 | Android 尺寸 | iOS 尺寸 | 像素变化比例 | 平均通道差 | 备注 |
|---|---|---:|---:|---:|---:|---|
| 首页月度总览 | missing_android | -x- | -x- | - | - | 金额、账本筛选和最近账目要一致；导航和材质允许原生差异。 |
| 手动记账 | missing_android | -x- | -x- | - | - | 支出/收入/转账需另做交互回归；此对为默认支出首屏。 |
| 交易明细与搜索 | missing_android | -x- | -x- | - | - | 退款子行不重复显示，列表净额和按天合计一致。 |
| 周统计 | missing_android | -x- | -x- | - | - | 按周一至周日、含空白天。 |
| 月统计 | missing_android | -x- | -x- | - | - | 月度总额、分类构成和每日趋势一致。 |
| 年统计 | missing_android | -x- | -x- | - | - | 全年总额、每月趋势和分类排行一致。 |
| 自定义统计区间 | missing_android | -x- | -x- | - | - | 起止日包含整天，并记住上次区间。 |
| 预算与今日可花 | missing_android | -x- | -x- | - | - | 总预算、周期窗口、今日可花、分类预算、固定承诺模板和当前/下一周期 occurrence；匹配/跳过/退款复核由操作回归补充。 |
| 账户对账 | missing_android | -x- | -x- | - | - | 余额校准和质量状态需一致。 |
| 待报销 | missing_android | -x- | -x- | - | - | 报销到账创建附着冲减，原账单净额归零。 |
| 存钱目标 | missing_android | -x- | -x- | - | - | 目标进度和归档状态一致。 |
| 定时记账 | missing_android | -x- | -x- | - | - | 规则展示一致；后台调度能力按平台差异单独验收。 |
| 资产管理 | missing_android | -x- | -x- | - | - | 资产档案和生命周期入口一致。 |
| 负债管理 | missing_android | -x- | -x- | - | - | 负债档案、还款入口和余额口径一致。 |
| 净资产 | missing_android | -x- | -x- | - | - | 资产、应收、负债和质量状态一致。 |
| 账本管理 | missing_android | -x- | -x- | - | - | 总账本不可删除；封面是原生符号占位，正式封面资产待补。 |
| 账户管理 | missing_android | -x- | -x- | - | - | 账户类型、余额入口和对账入口一致；iOS 使用原生列表与 sheet。 |
| 分类管理 | missing_android | -x- | -x- | - | - | 稳定分类 key、层级、自定义和隐藏入口一致。 |
| 标签管理 | missing_android | -x- | -x- | - | - | 标签列表、排序和新建入口一致。 |
| 设置与数据管理 | missing_android | -x- | -x- | - | - | 入口覆盖一致；iOS CSV 复核、canonical ZIP 和 Android v1/v2 原始 SQLite ZIP 转换已接入，待真实备份验收。 |
| AI 记账入口 | missing_android | -x- | -x- | - | - | Android 与 iOS 均进入 Chats 列表；点记一记后进入正文。 |
| AI 服务商与模型设置 | missing_android | -x- | -x- | - | - | 服务商账号、模型、端点、Effort 和 Keychain/API Key 状态；OAuth 按平台能力单独标注。 |
| 账单导入复核与商户批量分类 | missing_android | -x- | -x- | - | - | 商品优先分类、商户分组、账户选择和退款订单匹配入口；原生控件允许视觉差异。 |
| 报告库与月报阅读 | missing_android | -x- | -x- | - | - | 报告正文和统计口径一致；Android 使用玻璃半屏报告库，iOS 使用原生 NavigationStack。 |
| 喵学到的分类 | missing_android | -x- | -x- | - | - | 分类学习映射的展示与删除；历史账单不受影响。 |
| AI 任务中心 | missing_android | -x- | -x- | - | - | 阶段、状态和配置摘要一致；不展示密钥、完整提示词或原始思考。 |
| AI 诊断 | missing_android | -x- | -x- | - | - | 服务商运行次数、失败状态和脱敏错误摘要。 |
| AI 统一搜索 | missing_android | -x- | -x- | - | - | 账单、对话和 AI 任务的只读统一搜索。 |
| AI 可控记忆 | missing_android | -x- | -x- | - | - | 仅明确授权记忆进入上下文；删除不改历史。 |
| AI 技能与连接 | missing_android | -x- | -x- | - | - | 白名单技能和连接器开关；联网搜索按开关生效。 |
| AI 定时报表 | missing_android | -x- | -x- | - | - | 计划数据一致；iOS 后台生成改为系统提醒后打开 App。 |
| 本地模型伴侣 | missing_android | -x- | -x- | - | - | 本机回环地址和健康检查；不允许远程明文 HTTP。 |
| 备份与恢复 | missing_android | -x- | -x- | - | - | 完整备份、附件和最近恢复点；恢复语义单独检查。 |
| 主题外观 | missing_android | -x- | -x- | - | - | 外观选择和系统 Liquid Glass；语义色保持一致。 |
| 账单与聊天显示 | missing_android | -x- | -x- | - | - | 内容优先/分类优先和用户气泡背景策略。 |
| 收入记账操作态 | missing_android | -x- | -x- | - | - | 同一记一笔页面切换到收入类型；键盘、分类和账户入口保留平台原生表现。 |
| 物品资产详情操作态 | missing_android | -x- | -x- | - | - | 同一演示物品的估值、持有指标、账单关联和出售/退货入口；操作按钮允许原生布局差异。 |
| 账户详情操作态 | missing_android | -x- | -x- | - | - | 同一现金账户的余额、趋势、校准入口和流水活动；iOS 使用原生 sheet 展示详情。 |
| 报销到账操作态 | missing_android | -x- | -x- | - | - | 同一待报销账单的到账账户、到账日期和抵消金额确认界面；确认按钮保留平台原生交互。 |
