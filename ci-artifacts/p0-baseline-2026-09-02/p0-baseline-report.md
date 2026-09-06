# 肥喵记账 P0 同款基线报告

- 结论：**P0_PARTIAL**
- 基线：`p0-2026-09-02`
- 产品规则：Android 是产品和信息架构母版，iOS 是原生实现，不是第二款软件。
- 当前源码：`e0e0fbd83fd7f6ee823a3659405f48fd470c5df4` / `feature/ai-model-selector`；工作区 dirty=`True`

## 已检查

- 源码与 fixture 检查：`33/33` 项通过
- PNG + provenance 检查：`0/39` 对完整有效
- 待确认路由：`5` 项

## 源码合同

| 检查 | 结果 | 期望 | 实际 |
|---|---|---|---|
| Android version | pass | `1.289.0+304` | `1.289.0+304` |
| Android build watermark | pass | `b0901-304` | `b0901-304` |
| Android database version | pass | `49` | `49` |
| iOS version | pass | `1.286.0+300` | `1.286.0+300` |
| iOS deployment target | pass | `26.0` | `26.0` |
| Fixture hash is self-consistent | pass | `sha256:b061ac4951eb7960e56c57e09e27d6ac2858e21d3560a9de07688841d746f722` | `sha256:b061ac4951eb7960e56c57e09e27d6ac2858e21d3560a9de07688841d746f722` |
| Manifest fixture date | pass | `True` | `True` |
| Android compile-time fixture date | pass | `True` | `True` |
| Android fixture uses AppClock | pass | `True` | `True` |
| iOS fixture date injection | pass | `True` | `True` |
| iOS timezone injection | pass | `True` | `True` |
| iOS demo clock reads fixture environment | pass | `True` | `True` |
| iOS import review uses dedicated demo root | pass | `True` | `True` |
| iOS import review route has XCTest coverage | pass | `True` | `True` |
| Fixture id declared | pass | `True` | `True` |
| Android expected income | pass | `True` | `True` |
| Android expected expense | pass | `True` | `True` |
| Android expected budget | pass | `True` | `True` |
| Golden scenario declared: home-overview | pass | `True` | `True` |
| Golden scenario declared: quick-add | pass | `True` | `True` |
| Golden scenario declared: quick-add-income | pass | `True` | `True` |
| Golden scenario declared: transactions | pass | `True` | `True` |
| Golden scenario declared: stats-month | pass | `True` | `True` |
| Golden scenario declared: budget | pass | `True` | `True` |
| Golden scenario declared: reimburse | pass | `True` | `True` |
| Golden scenario declared: reimburse-settlement | pass | `True` | `True` |
| Route review declared: books | pass | `True` | `True` |
| Route review declared: accounts | pass | `True` | `True` |
| Route review declared: reconcile | pass | `True` | `True` |
| Route review declared: liabilities | pass | `True` | `True` |
| Route review declared: net-worth | pass | `True` | `True` |
| Route review declared: import-review | pass | `True` | `True` |
| iOS workflow routes match manifest | pass | `['ai', 'home', 'quickadd', 'quickadd/income', 'settings', 'settings/accounts', 'settings/accounts/detail', 'settings/ai', 'settings/ai-diagnostics', 'settings/ai-extensions', 'settings/ai-local', 'settings/ai-memory', 'settings/ai-schedules', 'settings/ai-search', 'settings/ai-tasks', 'settings/assets', 'settings/assets/detail', 'settings/backup', 'settings/books', 'settings/budget', 'settings/categories', 'settings/display', 'settings/import-review', 'settings/liabilities', 'settings/memory', 'settings/net-worth', 'settings/reconcile', 'settings/recurring', 'settings/reimburse', 'settings/reimburse/settlement', 'settings/reports', 'settings/savings', 'settings/tags', 'settings/theme', 'stats/custom', 'stats/month', 'stats/week', 'stats/year', 'transactions']` | `['ai', 'home', 'quickadd', 'quickadd/income', 'settings', 'settings/accounts', 'settings/accounts/detail', 'settings/ai', 'settings/ai-diagnostics', 'settings/ai-extensions', 'settings/ai-local', 'settings/ai-memory', 'settings/ai-schedules', 'settings/ai-search', 'settings/ai-tasks', 'settings/assets', 'settings/assets/detail', 'settings/backup', 'settings/books', 'settings/budget', 'settings/categories', 'settings/display', 'settings/import-review', 'settings/liabilities', 'settings/memory', 'settings/net-worth', 'settings/reconcile', 'settings/recurring', 'settings/reimburse', 'settings/reimburse/settlement', 'settings/reports', 'settings/savings', 'settings/tags', 'settings/theme', 'stats/custom', 'stats/month', 'stats/week', 'stats/year', 'transactions']` |

## 路由未决项

| 场景 | 当前事实 | iOS 路由 | 处理 |
|---|---|---|---|
| `books` | home drawer / 我的账本 | `settings/books` | Confirm whether Android's canonical product surface is the drawer entry or the dedicated book-management list; do not compare different surfaces under one id. |
| `accounts` | 资产管理 > 资金 | `settings/accounts` | Confirm whether the Android production entry is the asset hub funds tab or a dedicated account-management page; then make the iOS route represent the same surface. |
| `reconcile` | 资产管理 > 资金 | `settings/reconcile` | Confirm the Android user path to reconciliation. The current capture is not evidence for the iOS reconciliation page. |
| `liabilities` | 资产管理 > 资金 | `settings/liabilities` | Confirm whether Android exposes a dedicated liability surface or a funds-tab section before changing either app. |
| `net-worth` | 资产管理 > 总览 | `settings/net-worth` | Use the Android asset-hub overview as the canonical information hierarchy unless the actual Android entry is proven otherwise. |
| `import-review` | 导入复核 production page | `settings/import-review` | The iOS demo launch must render the review page itself; a home screenshot is invalid evidence. |

## PNG 与 provenance 证据

| 场景 | Android PNG/元数据 | iOS PNG/元数据 | 结论 |
|---|---|---|---|
| `home-overview` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `quick-add` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `transactions` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `stats-week` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `stats-month` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `stats-year` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `stats-custom` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `budget` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `reconcile` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `reimburse` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `savings` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `recurring` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `assets` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `liabilities` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `net-worth` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `books` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `accounts` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `categories` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `tags` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `settings` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-settings` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `import-review` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `reports` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `memory` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-tasks` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-diagnostics` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-search` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-memory` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-extensions` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-schedules` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `ai-local` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `backup` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `theme` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `display` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `quick-add-income` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `asset-detail` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `account-detail` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |
| `reimburse-settlement` | pass/unprovenanced `[1080, 1920]` | pass/unprovenanced `[1260, 2736]` | incomplete |

## 当前不能宣称的内容

1. PNG 文件存在不等于页面身份正确；本次检查的旧 PNG 旁缺少采集提交号和 fixture hash sidecar。
2. 本机没有 Swift/Xcode，无法在 Windows 重新运行 iOS 冷启动截图；当前 iOS PNG 只能算已有证据，不能算本轮重采集通过。
3. `accounts`、`reconcile`、`liabilities`、`net-worth`、`books` 的 Android 入口仍需按真实用户路径确认，不能依据文件名强行判定。

## 下一步关闭条件

- 在 macOS CI 重新运行 Android/iOS 双端截图，使用本报告中的版本、fixture、时区和逻辑时间。
- 为每次截图上传 `source revision / app version / DB version / fixture hash / device / OS` 元数据。
- 先确认未决路由，再生成新的成对截图；旧 PNG 不覆盖。
- P0 关闭后才把差异交给 P1 主记账链路处理。
