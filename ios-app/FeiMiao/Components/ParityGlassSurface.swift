import SwiftUI

/// Android-parity glass shell with an inexpensive solid-color fast path.
/// Use `blurred: true` only over moving content, such as the home entry launcher.
struct ParityGlassSurface<Content: View>: View {
    private let radius: CGFloat
    private let blurred: Bool
    private let fillColor: Color?
    private let contentInsets: EdgeInsets
    private let castsShadow: Bool
    private let content: Content

    init(
        radius: CGFloat = FeiMiaoRadius.card,
        blurred: Bool = false,
        fillColor: Color? = nil,
        padding: EdgeInsets = EdgeInsets(
            top: FeiMiaoSpacing.medium,
            leading: FeiMiaoSpacing.large,
            bottom: FeiMiaoSpacing.medium,
            trailing: FeiMiaoSpacing.large
        ),
        castsShadow: Bool = false,
        @ViewBuilder content: () -> Content
    ) {
        self.radius = radius
        self.blurred = blurred
        self.fillColor = fillColor
        self.contentInsets = padding
        self.castsShadow = castsShadow
        self.content = content()
    }

    private var shape: RoundedRectangle {
        RoundedRectangle(cornerRadius: radius, style: .continuous)
    }

    private var resolvedFill: Color {
        fillColor ?? .fmCard
    }

    var body: some View {
        content
            .padding(contentInsets)
            .background {
                if blurred {
                    shape.fill(.ultraThinMaterial)
                    shape.fill(resolvedFill)
                } else {
                    shape.fill(resolvedFill)
                }
            }
            .clipShape(shape)
            .overlay {
                shape.stroke(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.60),
                            Color.primary.opacity(0.06),
                            Color.primary.opacity(0.16),
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    ),
                    lineWidth: 1
                )
            }
            .shadow(
                color: castsShadow ? Color.black.opacity(0.06) : .clear,
                radius: castsShadow ? 10 : 0,
                y: castsShadow ? 3 : 0
            )
    }
}
