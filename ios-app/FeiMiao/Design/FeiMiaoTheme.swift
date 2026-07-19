import SwiftUI
import UIKit
import FeiMiaoDomain

private func adaptiveColor(
    light: (CGFloat, CGFloat, CGFloat),
    dark: (CGFloat, CGFloat, CGFloat),
    lightAlpha: CGFloat = 1,
    darkAlpha: CGFloat = 1
) -> Color {
    Color(uiColor: UIColor { traits in
        let isDark = traits.userInterfaceStyle == .dark
        let components = isDark ? dark : light
        return UIColor(
            red: components.0,
            green: components.1,
            blue: components.2,
            alpha: isDark ? darkAlpha : lightAlpha
        )
    })
}

extension Color {
    /// Blue-gray fur: the only brand/selection color.
    static let fmPrimary = adaptiveColor(
        light: (0.49, 0.55, 0.61),
        dark: (0.65, 0.73, 0.82)
    )
    static let fmPrimarySoft = fmPrimary.opacity(0.14)

    /// Warm eye-gold: income and positive money only.
    static let fmIncome = adaptiveColor(
        light: (0.95, 0.70, 0.24),
        dark: (0.97, 0.80, 0.43)
    )

    /// Low-saturation green is reserved for healthy budget progress.
    static let fmHealthy = adaptiveColor(
        light: (0.50, 0.69, 0.41),
        dark: (0.60, 0.77, 0.52)
    )

    /// Warning and overspend color. Destructive red is deliberately absent.
    static let fmRisk = adaptiveColor(
        light: (1.00, 0.62, 0.41),
        dark: (1.00, 0.67, 0.48)
    )
    static let fmPink = adaptiveColor(
        light: (0.96, 0.66, 0.72),
        dark: (0.98, 0.73, 0.78)
    )

    static let fmPageTop = adaptiveColor(
        light: (0.98, 0.88, 0.69),
        dark: (0.13, 0.12, 0.11)
    )
    static let fmPageBottom = adaptiveColor(
        light: (1.00, 0.99, 0.97),
        dark: (0.13, 0.12, 0.11)
    )
    static let fmPageBase = adaptiveColor(
        light: (0.97, 0.97, 0.98),
        dark: (0.13, 0.12, 0.11)
    )

    /// Default card alpha mirrors Android's warm theme (40% light / 55% dark).
    static let fmCard = adaptiveColor(
        light: (1, 1, 1),
        dark: (0.20, 0.18, 0.17),
        lightAlpha: 0.40,
        darkAlpha: 0.55
    )
    static let fmSelectedCard = adaptiveColor(
        light: (1, 1, 1),
        dark: (0.28, 0.27, 0.26),
        lightAlpha: 0.36,
        darkAlpha: 0.46
    )
    static let fmInputFill = adaptiveColor(
        light: (0.95, 0.95, 0.97),
        dark: (0.23, 0.22, 0.20)
    )
    static let fmHairline = adaptiveColor(
        light: (0, 0, 0),
        dark: (1, 1, 1),
        lightAlpha: 0.06,
        darkAlpha: 0.10
    )

    static let fmSecondaryText = Color.primary.opacity(0.55)
    static let fmHintText = Color.primary.opacity(0.45)
}

enum FeiMiaoRadius {
    static let badge: CGFloat = 8
    static let control: CGFloat = 12
    static let row: CGFloat = 16
    static let card: CGFloat = 20
    static let largeCard: CGFloat = 28
}

enum FeiMiaoSpacing {
    static let extraSmall: CGFloat = 4
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let extraLarge: CGFloat = 24
    static let extraExtraLarge: CGFloat = 32
}

enum FeiMiaoMotion {
    static let fast: TimeInterval = 0.12
    static let standard: TimeInterval = 0.25
    static let smooth: TimeInterval = 0.40

    static let press = Animation.easeOut(duration: fast)
    static let enter = Animation.easeOut(duration: standard)
}

enum FeiMiaoType {
    static let pageTitle = Font.system(size: 17, weight: .semibold)
    static let rowTitle = Font.system(size: 15.5, weight: .medium)
    static let body = Font.system(size: 15, weight: .regular)
    static let secondary = Font.system(size: 13, weight: .regular)
    static let sectionLabel = Font.system(size: 13.5, weight: .medium)
    static let trailingValue = Font.system(size: 14, weight: .regular)
    static let caption = Font.system(size: 12.5, weight: .regular)
}

enum FeiMiaoAssetName {
    static let brandLogo = "logo"
    static let mascotIdle = "idle"
    static let mascotEmpty = "empty"
    static let mascotOverspend = "overspend"
}

struct FeiMiaoPageBackground: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        if colorScheme == .dark {
            Color.fmPageBase
        } else {
            LinearGradient(
                colors: [.fmPageTop, .fmPageBottom],
                startPoint: .top,
                endPoint: UnitPoint(x: 0.5, y: 0.85)
            )
        }
    }
}

extension MoneyAmount {
    var yuanText: String {
        let isNegative = decimal < .zero
        let magnitude = isNegative ? -decimal : decimal
        let number = NSDecimalNumber(decimal: magnitude)
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        formatter.groupingSeparator = ","
        let numberText = formatter.string(from: number) ?? NSDecimalNumber(decimal: magnitude).stringValue
        return "\(isNegative ? "-" : "")\u{00A5}\(numberText)"
    }
}

struct FeiMiaoCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(FeiMiaoSpacing.large)
            .background(
                Color.fmCard,
                in: RoundedRectangle(
                    cornerRadius: FeiMiaoRadius.card,
                    style: .continuous
                )
            )
            .overlay {
                RoundedRectangle(
                    cornerRadius: FeiMiaoRadius.card,
                    style: .continuous
                )
                .stroke(Color.fmHairline, lineWidth: 0.5)
            }
    }
}

extension View {
    func feiMiaoCard() -> some View {
        modifier(FeiMiaoCardModifier())
    }
}
