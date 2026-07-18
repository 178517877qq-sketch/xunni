import SwiftUI
import UIKit
import FeiMiaoDomain

private func adaptiveColor(
    light: (CGFloat, CGFloat, CGFloat),
    dark: (CGFloat, CGFloat, CGFloat)
) -> Color {
    Color(uiColor: UIColor { traits in
        let components = traits.userInterfaceStyle == .dark ? dark : light
        return UIColor(
            red: components.0,
            green: components.1,
            blue: components.2,
            alpha: 1
        )
    })
}

extension Color {
    static let fmPrimary = adaptiveColor(
        light: (0.29, 0.38, 0.49),
        dark: (0.65, 0.73, 0.82)
    )
    static let fmPrimarySoft = fmPrimary.opacity(0.14)
    static let fmCard = Color(uiColor: .secondarySystemGroupedBackground)
    static let fmIncome = adaptiveColor(
        light: (0.64, 0.43, 0.23),
        dark: (0.82, 0.64, 0.43)
    )
    static let fmHealthy = adaptiveColor(
        light: (0.22, 0.55, 0.39),
        dark: (0.42, 0.72, 0.55)
    )
    static let fmRisk = adaptiveColor(
        light: (0.88, 0.43, 0.18),
        dark: (1.00, 0.58, 0.33)
    )
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
            .padding(16)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
    }
}

extension View {
    func feiMiaoCard() -> some View {
        modifier(FeiMiaoCardModifier())
    }
}
