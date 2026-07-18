import SwiftUI
import FeiMiaoDomain

struct TransactionDayGroup: Identifiable {
    let day: Date
    let items: [LedgerTransaction]

    var id: Date { day }
}

func groupTransactionsByDay(_ records: [LedgerTransaction], calendar: Calendar = .current) -> [TransactionDayGroup] {
    let grouped = Dictionary(grouping: records) { calendar.startOfDay(for: $0.date) }
    return grouped.keys.sorted(by: >).map { day in
        TransactionDayGroup(day: day, items: grouped[day, default: []].sorted { $0.date > $1.date })
    }
}

struct TransactionRow: View {
    @EnvironmentObject private var store: AppStore
    let transaction: LedgerTransaction

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(iconBackground)
                    .frame(width: 42, height: 42)
                Text(category?.emoji ?? fallbackEmoji)
                    .font(.title3)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.body.weight(.medium))
                    .lineLimit(1)
                HStack(spacing: 5) {
                    Text(category?.nameZh ?? fallbackCategory)
                    if let accountText {
                        Text("·")
                        Text(accountText)
                    }
                    if let timeText {
                        Text("·")
                        Text(timeText)
                    }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            }

            Spacer(minLength: 8)

            VStack(alignment: .trailing, spacing: 4) {
                Text(amountText)
                    .font(.body.monospacedDigit().weight(.semibold))
                    .foregroundStyle(amountColor)
                if transaction.isReimbursable {
                    Label("待报销", systemImage: "arrow.uturn.backward.circle")
                        .font(.caption2)
                        .foregroundStyle(.primary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.fmRisk.opacity(0.16), in: Capsule())
                } else if transaction.isExcluded {
                    Text("不计收支")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
        .accessibilityValue(accessibilitySummary)
        .accessibilityIdentifier("transaction-\(transaction.id)")
    }

    private var category: LedgerCategory? { store.category(for: transaction.categoryID) }

    private var title: String {
        let clean = transaction.note.trimmingCharacters(in: .whitespacesAndNewlines)
        return clean.isEmpty ? (category?.nameZh ?? fallbackCategory) : clean
    }

    private var fallbackEmoji: String {
        switch transaction.kind {
        case .expense: "🧾"
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
        case .expense: Color.fmPrimarySoft
        case .income: Color.fmIncome.opacity(0.13)
        case .transfer: Color(.tertiarySystemFill)
        }
    }

    private var amountText: String {
        let netAmount = store.netAmount(for: transaction)
        let amount = netAmount.yuanText
        switch transaction.kind {
        case .expense: return netAmount > .zero ? "-\(amount)" : amount
        case .income: return "+\(amount)"
        case .transfer: return amount
        }
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
        var parts = [category?.nameZh ?? fallbackCategory, accountText, timeText, amountText].compactMap { $0 }
        if transaction.isReimbursable { parts.append("待报销") }
        if transaction.isExcluded { parts.append("不计入收支") }
        return parts.joined(separator: "，")
    }
}
