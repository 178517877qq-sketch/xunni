import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        NavigationStack {
            AppShellView()
        }
        .accessibilityHidden(store.isImportingBackup)
        .overlay {
            if store.isImportingBackup {
                ZStack {
                    FeiMiaoPageBackground()
                        .ignoresSafeArea()
                    VStack(spacing: 14) {
                        MascotView(mood: .idle, size: 72, animated: true)
                        ProgressView("正在校验并导入备份…")
                            .tint(.fmPrimary)
                    }
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("正在导入备份")
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
