import SwiftUI

/// Layout-stable press feedback shared by home controls and drawer rows.
/// Scaling is a render transform, so pressing never changes surrounding layout.
struct PressableButtonStyle: ButtonStyle {
    var pressedScale: CGFloat = 0.97
    var pressedOpacity: Double = 0.86

    func makeBody(configuration: Configuration) -> some View {
        PressableButtonBody(
            configuration: configuration,
            pressedScale: pressedScale,
            pressedOpacity: pressedOpacity
        )
    }
}

private struct PressableButtonBody: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let configuration: ButtonStyleConfiguration
    let pressedScale: CGFloat
    let pressedOpacity: Double

    var body: some View {
        configuration.label
            .scaleEffect(
                reduceMotion || !configuration.isPressed ? 1 : pressedScale
            )
            .opacity(configuration.isPressed ? pressedOpacity : 1)
            .animation(
                reduceMotion ? nil : FeiMiaoMotion.press,
                value: configuration.isPressed
            )
    }
}

extension ButtonStyle where Self == PressableButtonStyle {
    static var feiMiaoPressable: PressableButtonStyle {
        PressableButtonStyle()
    }
}
