import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var store: AppStore
    @State private var selection = Tab.home

    enum Tab: Hashable {
        case home
        case transactions
        case add
        case accounts
        case settings
    }

    var body: some View {
        TabView(selection: $selection) {
            HomeView(openAdd: { selection = .add })
                .tabItem { Label("首页", systemImage: "house.fill") }
                .tag(Tab.home)

            TransactionsView()
                .tabItem { Label("明细", systemImage: "list.bullet.rectangle") }
                .tag(Tab.transactions)

            ManualEntryView(onSaved: { selection = .home })
                .tabItem { Label("记账", systemImage: "plus.circle.fill") }
                .tag(Tab.add)

            AccountsOverviewView()
                .tabItem { Label("账户", systemImage: "wallet.bifold.fill") }
                .tag(Tab.accounts)

            SettingsView()
                .tabItem { Label("设置", systemImage: "gearshape.fill") }
                .tag(Tab.settings)
        }
        .accessibilityHidden(!store.isReady || store.isImportingBackup)
        .overlay {
            if !store.isReady || store.isImportingBackup {
                ZStack {
                    Color(.systemGroupedBackground)
                        .ignoresSafeArea()
                    VStack(spacing: 14) {
                        Image(systemName: "cat.fill")
                            .font(.system(size: 42, weight: .medium))
                            .foregroundStyle(Color.fmPrimary)
                        ProgressView(store.isImportingBackup ? "正在校验并导入备份…" : "正在打开本月账本…")
                            .tint(.fmPrimary)
                    }
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel(store.isImportingBackup ? "正在导入备份" : "正在打开账本")
            }
        }
        .alert(
            "肥喵遇到一点问题",
            isPresented: Binding(
                get: { store.presentedError != nil },
                set: { if !$0 { store.presentedError = nil } }
            )
        ) {
            Button("知道了", role: .cancel) { store.presentedError = nil }
        } message: {
            Text(store.presentedError ?? "")
        }
    }
}
