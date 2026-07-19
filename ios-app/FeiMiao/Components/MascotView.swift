import SwiftUI
import UIKit

enum MascotMood: String, CaseIterable, Sendable {
    case idle
    case success
    case overspend
    case celebrate
    case empty
    case thinking
    case report

    fileprivate var fallbackEmoji: String {
        switch self {
        case .idle: "🐱"
        case .success: "🧧"
        case .overspend: "🙀"
        case .celebrate: "😻"
        case .empty: "😴"
        case .thinking: "🤔"
        case .report: "📋"
        }
    }

    fileprivate var fallbackColor: Color {
        switch self {
        case .idle, .thinking: .fmPrimarySoft
        case .success, .report: .fmIncome.opacity(0.18)
        case .overspend: .fmRisk.opacity(0.15)
        case .celebrate: .fmPink.opacity(0.18)
        case .empty: .fmInputFill.opacity(0.70)
        }
    }

    fileprivate var accessibilityName: String {
        switch self {
        case .idle: "待机的肥喵"
        case .success: "记账成功的肥喵"
        case .overspend: "超支提醒肥喵"
        case .celebrate: "庆祝的肥喵"
        case .empty: "睡觉的肥喵"
        case .thinking: "思考中的肥喵"
        case .report: "查看报告的肥喵"
        }
    }
}

/// Bitmap mascot with an intermittent two-breath animation and an eight-second rest.
/// The rest interval is completely static, avoiding permanent 60/120 fps rendering.
struct MascotView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let mood: MascotMood
    var size: CGFloat = 48
    var animated = false
    var bob: CGFloat = -3
    var swayDegrees: Double = 3.4
    var anchor: UnitPoint = .center
    var decorative = true

    @State private var breathing = false

    var body: some View {
        image
            .frame(width: size, height: size)
            .scaleEffect(breathing ? 1.07 : 1, anchor: anchor)
            .offset(y: breathing ? bob : 0)
            .rotationEffect(
                .degrees(breathing ? swayDegrees / 2 : -swayDegrees / 2),
                anchor: anchor
            )
            .compositingGroup()
            .accessibilityHidden(decorative)
            .accessibilityLabel(decorative ? "" : mood.accessibilityName)
            .task(id: animated && !reduceMotion) {
                guard animated, !reduceMotion else {
                    breathing = false
                    return
                }
                await runBreathingBouts()
            }
    }

    @ViewBuilder
    private var image: some View {
        if let bitmap = loadBitmap() {
            Image(uiImage: bitmap)
                .resizable()
                .scaledToFit()
        } else {
            ZStack {
                Circle().fill(mood.fallbackColor)
                Text(mood.fallbackEmoji)
                    .font(.system(size: size * 0.52))
            }
        }
    }

    private func loadBitmap() -> UIImage? {
        if let image = UIImage(named: mood.rawValue) {
            return image
        }
        let locations: [URL?] = [
            Bundle.main.url(forResource: mood.rawValue, withExtension: "png"),
            Bundle.main.url(
                forResource: mood.rawValue,
                withExtension: "png",
                subdirectory: "Mascot"
            ),
        ]
        return locations.compactMap { $0 }.lazy.compactMap {
            UIImage(contentsOfFile: $0.path)
        }.first
    }

    @MainActor
    private func runBreathingBouts() async {
        while !Task<Never, Never>.isCancelled {
            for _ in 0..<2 {
                withAnimation(.easeInOut(duration: 2.2)) {
                    breathing = true
                }
                guard await pause(nanoseconds: 2_200_000_000) else { return }

                withAnimation(.easeInOut(duration: 2.2)) {
                    breathing = false
                }
                guard await pause(nanoseconds: 2_200_000_000) else { return }
            }
            guard await pause(nanoseconds: 8_000_000_000) else { return }
        }
    }

    private func pause(nanoseconds: UInt64) async -> Bool {
        do {
            try await Task<Never, Never>.sleep(nanoseconds: nanoseconds)
            return !Task<Never, Never>.isCancelled
        } catch {
            return false
        }
    }
}

/// The home-card pose keeps its gripping edge anchored while breathing.
struct HomePeekingMascotView: View {
    var isOverspending: Bool
    var height: CGFloat = 96

    var body: some View {
        MascotView(
            mood: isOverspending ? .overspend : .idle,
            size: height,
            animated: true,
            bob: 2,
            swayDegrees: 0,
            anchor: .trailing
        )
        .offset(x: 4)
    }
}
