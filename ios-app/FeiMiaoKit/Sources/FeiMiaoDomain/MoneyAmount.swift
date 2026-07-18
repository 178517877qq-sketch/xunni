import Foundation

/// Decimal money value that round-trips through SQLite as text.
/// Binary floating point values are deliberately kept out of the persistence API.
public struct MoneyAmount: Hashable, Codable, Comparable, Sendable {
    public let decimal: Decimal

    public static let zero = MoneyAmount(decimal: .zero)

    public init(decimal: Decimal) {
        self.decimal = decimal
    }

    public init?(_ storage: String) {
        let clean = storage.trimmingCharacters(in: .whitespacesAndNewlines)
        let decimalPattern = #"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"#
        guard clean.range(of: decimalPattern, options: .regularExpression) != nil,
              let value = Decimal(
            string: clean,
            locale: Locale(identifier: "en_US_POSIX")
        ) else { return nil }
        self.decimal = value
    }

    public var storageString: String {
        NSDecimalNumber(decimal: decimal).stringValue
    }

    public func formatted(currencyCode: String = "CNY") -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = currencyCode
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        return formatter.string(from: NSDecimalNumber(decimal: decimal))
            ?? "\(currencyCode) \(storageString)"
    }

    public static func < (lhs: Self, rhs: Self) -> Bool {
        lhs.decimal < rhs.decimal
    }

    public static func + (lhs: Self, rhs: Self) -> Self {
        MoneyAmount(decimal: lhs.decimal + rhs.decimal)
    }

    public static func - (lhs: Self, rhs: Self) -> Self {
        MoneyAmount(decimal: lhs.decimal - rhs.decimal)
    }
}
