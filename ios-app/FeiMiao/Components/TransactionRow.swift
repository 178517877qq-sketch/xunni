import SwiftUI
import FeiMiaoDomain

struct TransactionDayGroup: Identifiable {
    let day: Date
    let items: [LedgerTransaction]

    var id: Date { day }
}

func groupTransactionsByDay(
    _ records: [LedgerTransaction],
    calendar: Calendar = .current
) -> [TransactionDayGroup] {
    let grouped = Dictionary(grouping: records) { calendar.startOfDay(for: $0.date) }
    return grouped.keys.sorted(by: >).map { day in
        TransactionDayGroup(
            day: day,
            items: grouped[day, default: []].sorted {
                if $0.date == $1.date { return $0.id > $1.id }
                return $0.date > $1.date
            }
        )
    }
}

struct TransactionRow: View {
    @EnvironmentObject private var store: AppStore

    let transaction: LedgerTransaction
    private let suppliedNetAmount: MoneyAmount?

    init(transaction: LedgerTransaction, netAmount: MoneyAmount? = nil) {
        self.transaction = transaction
        suppliedNetAmount = netAmount
    }

    var body: some View {
        HStack(spacing: 12) {
            categoryIcon

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(FeiMiaoType.rowTitle)
                    .foregroundStyle(Color.primary)
                    .lineLimit(1)

                HStack(spacing: 5) {
                    ForEach(Array(subtitleParts.enumerated()), id: \.offset) { index, part in
                        if index > 0 { Text("·") }
                        Text(part)
                    }
                }
                .font(FeiMiaoType.caption)
                .foregroundStyle(Color.fmSecondaryText)
                .lineLimit(1)

                if !tagNames.isEmpty {
                    Text(tagNames.joined(separator: " · "))
                        .font(.system(size: 10.5, weight: .regular))
                        .foregroundStyle(Color.fmPrimary)
                        .lineLimit(1)
                }
            }

            Spacer(minLength: 8)

            VStack(alignment: .trailing, spacing: 4) {
                if refundedAmount > .zero {
                    Text(originalAmountText)
                        .font(.system(size: 11, weight: .regular).monospacedDigit())
                        .foregroundStyle(Color.fmHintText)
                        .strikethrough(true, color: .fmHintText)
                }

                Text(amountText)
                    .font(.system(size: 15.5, weight: .semibold, design: .rounded).monospacedDigit())
                    .foregroundStyle(amountColor)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)

                statusBadges
            }
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
        .accessibilityValue(accessibilitySummary)
        .accessibilityIdentifier("transaction-\(transaction.id)")
    }

    private var categoryIcon: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(categorySymbol == nil ? iconBackground : categoryTileColor)
                .frame(width: 42, height: 42)
            if let categorySymbol {
                Image(systemName: categorySymbol)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.white)
            } else {
                Text(category?.emoji ?? fallbackEmoji)
                    .font(.system(size: 20))
            }
        }
        .accessibilityHidden(true)
    }

    @ViewBuilder
    private var statusBadges: some View {
        VStack(alignment: .trailing, spacing: 2) {
            if refundedAmount > .zero {
                badge("已退 \(refundedAmount.yuanText)", color: .fmIncome)
            }
            if transaction.isReimbursable {
                badge("待报销", color: .fmRisk)
            }
            if transaction.isExcluded {
                badge("不计收支", color: .fmSecondaryText)
            }
        }
    }

    private func badge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 9.5, weight: .medium))
            .foregroundStyle(color)
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .background(color.opacity(0.12), in: Capsule())
            .lineLimit(1)
    }

    private var category: LedgerCategory? {
        store.category(for: transaction.categoryID)
    }

    private var title: String {
        let clean = transaction.note.trimmingCharacters(in: .whitespacesAndNewlines)
        return clean.isEmpty ? (category?.nameZh ?? fallbackCategory) : clean
    }

    private var subtitleParts: [String] {
        [category?.nameZh ?? fallbackCategory, accountText, timeText].compactMap { value in
            guard let value, !value.isEmpty else { return nil }
            return value
        }
    }

    private var tagNames: [String] {
        store.tags
            .filter { transaction.tagIDs.contains($0.id) }
            .prefix(2)
            .map { "#\($0.name)" }
    }

    private var fallbackEmoji: String {
        switch transaction.kind {
        case .expense: "🏷️"
        case .income: "💰"
        case .transfer: "↔️"
        }
    }

    private var fallbackCategory: String {
        transaction.kind == .transfer ? "转账" : "未分类"
    }

    private var accountText: String? {
        let source = store.account(for: transaction.accountID)?.name
        guard transaction.kind == .transfer else { return source }
        let destination = store.account(for: transaction.toAccountID)?.name
        switch (source, destination) {
        case let (.some(source), .some(destination)):
            return "\(source) → \(destination)"
        case let (.some(source), .none):
            return source
        case let (.none, .some(destination)):
            return destination
        case (.none, .none):
            return nil
        }
    }

    private var iconBackground: Color {
        switch transaction.kind {
        case .expense: .fmPrimarySoft
        case .income: .fmIncome.opacity(0.13)
        case .transfer: .fmInputFill
        }
    }

    private var categorySymbol: String? {
        guard let key = category?.key else { return nil }
        switch key {
        case "subscription":
            return "ticket.fill"
        case let value where value == "dining" || value.hasPrefix("dining_") || value == "groceries":
            return "fork.knife"
        case let value where value == "transport" || value.hasPrefix("trans_"):
            return "bus.fill"
        case let value where value == "car" || value.hasPrefix("car_"):
            return "car.fill"
        case let value where value == "shopping" || value.hasPrefix("shop_") || value == "pets":
            return "bag.fill"
        case let value where value == "housing" || value.hasPrefix("house_"):
            return "house.fill"
        case let value where value == "medical" || value.hasPrefix("med_"):
            return "cross.case.fill"
        case let value where value == "education" || value.hasPrefix("edu_"):
            return "book.fill"
        case let value where value == "entertainment" || value.hasPrefix("ent_"):
            return "gamecontroller.fill"
        case let value where value == "gifts" || value.hasPrefix("gift_"):
            return "gift.fill"
        default:
            return transaction.kind == .income ? "banknote.fill" : nil
        }
    }

    private var categoryTileColor: Color {
        guard let key = category?.key else { return .fmPrimary }
        if key == "subscription" || key == "entertainment" || key.hasPrefix("ent_") {
            return Color(red: 0.89, green: 0.48, blue: 0.66)
        }
        if key == "dining" || key.hasPrefix("dining_") || key == "groceries" {
            return Color(red: 0.91, green: 0.55, blue: 0.32)
        }
        if key == "transport" || key.hasPrefix("trans_") || key == "car" || key.hasPrefix("car_") {
            return Color(red: 0.39, green: 0.66, blue: 0.86)
        }
        if key == "medical" || key.hasPrefix("med_") {
            return Color.fmHealthy
        }
        if transaction.kind == .income {
            return Color.fmIncome
        }
        return Color.fmPrimary
    }

    private var netAmount: MoneyAmount {
        suppliedNetAmount ?? store.netAmount(for: transaction)
    }

    private var refundedAmount: MoneyAmount {
        guard transaction.kind == .expense,
              transaction.amount > netAmount else { return .zero }
        return transaction.amount - netAmount
    }

    private var amountText: String {
        let amount = netAmount.yuanText
        switch transaction.kind {
        case .expense: return netAmount > .zero ? "-\(amount)" : amount
        case .income: return "+\(amount)"
        case .transfer: return amount
        }
    }

    private var originalAmountText: String {
        transaction.kind == .expense ? "-\(transaction.amount.yuanText)" : transaction.amount.yuanText
    }

    private var amountColor: Color {
        switch transaction.kind {
        case .expense: .primary
        case .income: .fmIncome
        case .transfer: .fmPrimary
        }
    }

    private var timeText: String? {
        switch transaction.timePrecision {
        case .exact, .entryClock:
            transaction.date.formatted(date: .omitted, time: .shortened)
        case .dateOnly, .legacyUnknown:
            nil
        }
    }

    private var accessibilitySummary: String {
        var parts = subtitleParts + [amountText]
        if refundedAmount > .zero { parts.append("已退款 \(refundedAmount.yuanText)") }
        if transaction.isReimbursable { parts.append("待报销") }
        if transaction.isExcluded { parts.append("不计入收支") }
        return parts.joined(separator: "，")
    }
}
