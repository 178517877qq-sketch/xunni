import SwiftUI

struct AppShellView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var drawerProgress: CGFloat = 0
    @State private var dragStartProgress: CGFloat?
    @State private var destination: AppDrawerDestination?
    @State private var showingEntry = false

    private let drawerAnimation = Animation.timingCurve(
        0.22,
        1,
        0.36,
        1,
        duration: 0.24
    )

    var body: some View {
        GeometryReader { proxy in
            let drawerWidth = min(max(proxy.size.width * 0.75, 240), 320)
            ZStack(alignment: .leading) {
                FeiMiaoPageBackground()
                    .ignoresSafeArea()

                SideDrawerView(
                    width: drawerWidth,
                    onSelect: openDestination,
                    onClose: closeDrawer
                )
                .frame(width: drawerWidth)
                .frame(maxHeight: .infinity)
                .allowsHitTesting(drawerProgress > 0.01)
                .accessibilityHidden(drawerProgress <= 0.01)
                .accessibilityAction(.escape, closeDrawer)

                mainSurface(drawerWidth: drawerWidth)
                    .offset(x: drawerProgress * drawerWidth)
            }
            .contentShape(Rectangle())
            .simultaneousGesture(drawerGesture(drawerWidth: drawerWidth))
        }
        .navigationDestination(item: $destination) { destination in
            destinationView(destination)
                .toolbar(.visible, for: .navigationBar)
        }
        .sheet(isPresented: $showingEntry) {
            ManualEntryView {
                showingEntry = false
            }
        }
    }

    private func mainSurface(drawerWidth: CGFloat) -> some View {
        let cornerRadius = 26 * drawerProgress
        return HomeView(
            openDrawer: openDrawer,
            openAdd: { showingEntry = true }
        )
        .background {
            FeiMiaoPageBackground()
                .ignoresSafeArea()
        }
        .clipShape(
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .stroke(
                    Color.primary.opacity(0.08 * drawerProgress),
                    lineWidth: drawerProgress > 0 ? 0.5 : 0
                )
        }
        .overlay {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color.black.opacity(0.12 * drawerProgress))
                .contentShape(
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                )
                .onTapGesture(perform: closeDrawer)
                .allowsHitTesting(drawerProgress > 0.001)
        }
        .shadow(
            color: Color.black.opacity(0.20 * drawerProgress),
            radius: 24 * drawerProgress,
            x: -8 * drawerProgress
        )
        .accessibilityHidden(drawerProgress > 0.5)
    }

    private func drawerGesture(drawerWidth: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .local)
            .onChanged { value in
                if dragStartProgress == nil {
                    let translation = value.translation
                    let horizontal = abs(translation.width) > abs(translation.height) * 1.35
                    let openingFromEdge = value.startLocation.x <= 28 && translation.width > 0
                    let closingOpenDrawer = drawerProgress > 0.001 && translation.width < 0
                    guard horizontal, openingFromEdge || closingOpenDrawer else { return }
                    dragStartProgress = drawerProgress
                }

                guard let start = dragStartProgress else { return }
                drawerProgress = min(
                    max(start + value.translation.width / drawerWidth, 0),
                    1
                )
            }
            .onEnded { value in
                guard let start = dragStartProgress else { return }
                dragStartProgress = nil
                let projected = min(
                    max(start + value.predictedEndTranslation.width / drawerWidth, 0),
                    1
                )
                settleDrawer(open: projected >= 0.5)
            }
    }

    private func openDrawer() {
        settleDrawer(open: true)
    }

    private func closeDrawer() {
        settleDrawer(open: false)
    }

    private func settleDrawer(open: Bool) {
        let target: CGFloat = open ? 1 : 0
        if reduceMotion {
            drawerProgress = target
        } else {
            withAnimation(drawerAnimation) {
                drawerProgress = target
            }
        }
    }

    private func openDestination(_ next: AppDrawerDestination) {
        closeDrawer()
        destination = next
    }

    @ViewBuilder
    private func destinationView(_ destination: AppDrawerDestination) -> some View {
        switch destination {
        case .transactions:
            TransactionsView(embedsNavigationStack: false)
        case .accounts:
            AccountsManagementView()
        case .books:
            BooksManagementView()
        case .categories:
            CategoriesManagementView()
        case .tags:
            TagsManagementView()
        case .settings:
            SettingsView(embedsNavigationStack: false)
        }
    }
}
