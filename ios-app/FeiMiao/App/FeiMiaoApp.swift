import SwiftUI

@main
struct FeiMiaoApp: App {
    @StateObject private var store = AppStore()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(store)
                .tint(.fmPrimary)
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { store.reloadAll() }
                }
        }
    }
}
