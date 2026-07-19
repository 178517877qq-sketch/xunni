import SwiftUI
import FeiMiaoDomain

/// The account tab owns its navigation stack. Settings reuses
/// `AccountsManagementView` directly so navigation stacks are never nested.
struct AccountsOverviewView: View {
    var body: some View {
        NavigationStack {
            AccountsManagementView()
        }
    }
}

struct AccountsManagementView: View {
    @EnvironmentObject private var store: AppStore
    @State private var editorRoute: AccountEditorRoute?
    @State private var pendingDeletion: LedgerAccount?
    @State private var pendingDeletionIsInUse = false

    private var activeAccounts: [LedgerAccount] {
        store.accounts.filter(\.isAvailableForNewTransactions)
    }

    private var archivedAccounts: [LedgerAccount] {
        store.accounts.filter(\.isArchived)
    }

    private var netWorth: MoneyAmount {
        activeAccounts
            .filter(\.includeInNetWorth)
            .reduce(.zero) { total, account in
                total + (store.accountBalances[account.id] ?? account.openingBalance)
            }
    }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Label("净资产", systemImage: "chart.line.uptrend.xyaxis")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(.secondary)
                    Text(netWorth.yuanText)
                        .font(.system(size: 32, weight: .semibold, design: .rounded))
                        .contentTransition(.numericText())
                    Text("仅汇总使用中且已计入净资产的账户")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .feiMiaoCard()
                .listRowInsets(EdgeInsets())
                .listRowBackground(Color.clear)
            }

            Section("使用中的账户") {
                if activeAccounts.isEmpty {
                    if store.accounts.isEmpty {
                        ContentUnavailableView(
                            "还没有账户",
                            systemImage: "wallet.bifold",
                            description: Text("先建立现金、银行卡或支付账户，再开始记账。")
                        )
                        .frame(maxWidth: .infinity)
                        .listRowBackground(Color.clear)
                    } else {
                        ContentUnavailableView(
                            "没有使用中的账户",
                            systemImage: "archivebox",
                            description: Text("新建账户，或从已归档账户中恢复一个。")
                        )
                        .frame(maxWidth: .infinity)
                        .listRowBackground(Color.clear)
                    }
                } else {
                    ForEach(activeAccounts) { account in
                        accountRow(account)
                    }
                }
            }

            if !archivedAccounts.isEmpty {
                Section {
                    ForEach(archivedAccounts) { account in
                        accountRow(account)
                    }
                } header: {
                    Text("已归档")
                } footer: {
                    Text("归档账户会保留余额和历史账单，可以随时编辑并恢复使用。")
                }
            }
        }
        .navigationTitle("账户")
        .overlay {
            if store.isLedgerLoading && store.accountBalances.isEmpty {
                ZStack {
                    FeiMiaoPageBackground()
                    ProgressView("正在读取账户余额…")
                        .tint(.fmPrimary)
                }
                .ignoresSafeArea(edges: .bottom)
            }
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    editorRoute = AccountEditorRoute(account: nil)
                } label: {
                    Label("添加账户", systemImage: "plus")
                }
                .accessibilityIdentifier("add-account")
            }
        }
        .sheet(item: $editorRoute) { route in
            AccountEditorView(account: route.account)
        }
        .confirmationDialog(
            pendingDeletionIsInUse ? "无法删除账户" : "删除账户？",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            if pendingDeletionIsInUse {
                Button("知道了", role: .cancel) { pendingDeletion = nil }
            } else {
                Button("删除", role: .destructive) {
                    guard let account = pendingDeletion else { return }
                    guard store.databaseURL != nil else {
                        store.presentedError = "账本数据库当前不可用，请稍后重试。"
                        pendingDeletion = nil
                        return
                    }
                    store.presentedError = nil
                    store.deleteAccount(account.id)
                    pendingDeletion = nil
                }
                Button("取消", role: .cancel) { pendingDeletion = nil }
            }
        } message: {
            Text(
                pendingDeletionIsInUse
                    ? "这个账户已有历史账单，不能删除。请打开账户编辑并开启“归档账户”，历史记录和账户名称都会保留。"
                    : "这个账户没有关联账单，删除后将不再出现在选择列表中。"
            )
        }
    }

    private func accountRow(_ account: LedgerAccount) -> some View {
        let isArchived = account.isArchived
        return Button {
            editorRoute = AccountEditorRoute(account: account)
        } label: {
            HStack(spacing: 12) {
                Image(systemName: AccountTypeOption.icon(for: account.type))
                    .font(.title3)
                    .foregroundStyle(isArchived ? Color.secondary : Color.fmPrimary)
                    .frame(width: 38, height: 38)
                    .background(
                        isArchived ? Color(.tertiarySystemGroupedBackground) : Color.fmPrimarySoft,
                        in: RoundedRectangle(cornerRadius: 10)
                    )

                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text(account.name)
                            .font(.body.weight(.medium))
                            .foregroundStyle(isArchived ? Color.secondary : Color.primary)
                        if isArchived {
                            Text("已归档")
                                .font(.caption2.weight(.medium))
                                .foregroundStyle(.secondary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color(.tertiarySystemGroupedBackground), in: Capsule())
                        }
                    }
                    Text(accountSubtitle(account))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 3) {
                    Text((store.accountBalances[account.id] ?? account.openingBalance).yuanText)
                        .font(.body.monospacedDigit().weight(.semibold))
                        .foregroundStyle(isArchived ? Color.secondary : Color.primary)
                    if isArchived || !account.includeInNetWorth {
                        Text(isArchived ? "不计当前净资产" : "不计净资产")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("account-row-\(account.id)")
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            if !isArchived {
                Button("删除", role: .destructive) {
                    requestDeletion(account)
                }
            }
            Button("编辑") {
                editorRoute = AccountEditorRoute(account: account)
            }
            .tint(.fmPrimary)
        }
    }

    private func accountSubtitle(_ account: LedgerAccount) -> String {
        let typeTitle = AccountTypeOption.title(for: account.type)
        let institution = account.institution.trimmingCharacters(in: .whitespacesAndNewlines)
        return institution.isEmpty ? typeTitle : "\(typeTitle) · \(institution)"
    }

    private func requestDeletion(_ account: LedgerAccount) {
        store.presentedError = nil
        guard let isInUse = store.accountIsInUse(account.id) else {
            return
        }
        pendingDeletionIsInUse = isInUse
        pendingDeletion = account
    }
}

private struct AccountEditorRoute: Identifiable {
    let id = UUID()
    let account: LedgerAccount?
}

private struct AccountEditorView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    private let account: LedgerAccount?
    @State private var name: String
    @State private var type: String
    @State private var openingBalanceText: String
    @State private var includeInNetWorth: Bool
    @State private var institution: String
    @State private var isArchived: Bool

    init(account: LedgerAccount?) {
        self.account = account
        _name = State(initialValue: account?.name ?? "")
        _type = State(initialValue: account?.type ?? AccountTypeOption.cash.rawValue)
        _openingBalanceText = State(initialValue: account?.openingBalance.storageString ?? "0")
        _includeInNetWorth = State(initialValue: account?.includeInNetWorth ?? true)
        _institution = State(initialValue: account?.institution ?? "")
        _isArchived = State(initialValue: account?.isArchived ?? false)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("账户信息") {
                    TextField("账户名称", text: $name)
                        .textInputAutocapitalization(.never)

                    Picker("账户类型", selection: $type) {
                        ForEach(AccountTypeOption.allCases) { option in
                            Label(option.title, systemImage: option.icon)
                                .tag(option.rawValue)
                        }
                        if AccountTypeOption(rawValue: type) == nil {
                            Text(type).tag(type)
                        }
                    }

                    TextField("开户行或平台（可选）", text: $institution)
                }

                Section {
                    HStack {
                        Text("¥")
                            .foregroundStyle(.secondary)
                        TextField("0.00", text: $openingBalanceText)
                            .keyboardType(.numbersAndPunctuation)
                            .multilineTextAlignment(.trailing)
                    }
                    Toggle(isArchived ? "恢复后计入净资产" : "计入净资产", isOn: $includeInNetWorth)
                } header: {
                    Text("期初余额")
                } footer: {
                    Text("可以输入负数表示信用卡欠款。修改期初余额会立即影响当前余额。")
                }

                if account != nil {
                    Section {
                        Toggle("归档账户", isOn: $isArchived)
                    } footer: {
                        Text("归档后会从使用中的账户分组移出，余额和历史账单仍会保留，也可以随时恢复。")
                    }
                }
            }
            .navigationTitle(account == nil ? "新建账户" : "编辑账户")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存", action: save)
                        .disabled(!canSave)
                }
            }
        }
    }

    private var parsedOpeningBalance: MoneyAmount? {
        let value = openingBalanceText.trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? .zero : MoneyAmount(value)
    }

    private var canSave: Bool {
        !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && parsedOpeningBalance != nil
    }

    private func save() {
        guard let openingBalance = parsedOpeningBalance, canSave else { return }
        guard store.databaseURL != nil else {
            store.presentedError = "账本数据库当前不可用，请稍后重试。"
            return
        }
        store.presentedError = nil
        if var account {
            account.name = name
            account.type = type
            account.openingBalance = openingBalance
            account.includeInNetWorth = includeInNetWorth
            account.institution = institution
            account.status = isArchived
                ? LedgerAccountStatus.archived.rawValue
                : LedgerAccountStatus.active.rawValue
            store.updateAccount(account)
        } else {
            store.createAccount(
                name: name,
                type: type,
                openingBalance: openingBalance,
                includeInNetWorth: includeInNetWorth,
                institution: institution
            )
        }
        if store.presentedError == nil { dismiss() }
    }
}

private enum AccountTypeOption: String, CaseIterable, Identifiable {
    case cash
    case bank
    case credit
    case alipay
    case wechat
    case investment
    case other

    var id: String { rawValue }

    var title: String {
        switch self {
        case .cash: "现金"
        case .bank: "银行卡"
        case .credit: "信用卡"
        case .alipay: "支付宝"
        case .wechat: "微信支付"
        case .investment: "投资账户"
        case .other: "其他账户"
        }
    }

    var icon: String {
        switch self {
        case .cash: "banknote"
        case .bank: "building.columns"
        case .credit: "creditcard"
        case .alipay: "a.circle"
        case .wechat: "message.fill"
        case .investment: "chart.line.uptrend.xyaxis"
        case .other: "wallet.bifold"
        }
    }

    static func title(for rawValue: String) -> String {
        Self(rawValue: rawValue)?.title ?? "其他账户"
    }

    static func icon(for rawValue: String) -> String {
        Self(rawValue: rawValue)?.icon ?? "wallet.bifold"
    }
}
