import SwiftUI
import FeiMiaoDomain

struct TransactionDayCard: View {
    let group: TransactionDayGroup
    let netAmount: (LedgerTransaction) -> MoneyAmount
    let onSelect: (LedgerTransaction) -> Void

    private var totalExpense: MoneyAmount {
        group.items.reduce(.zero) { total, item in
            guard item.kind == .expense, !item.isExcluded else { return total }
            return total + netAmount(item)
        }
    }

    private var totalIncome: MoneyAmount {
        group.items.reduce(.zero) { total, item in
            guard item.kind == .income, !item.isExcluded else { return total }
            return total + netAmount(item)
        }
    }

    var body: some View {
        ParityGlassSurface(
            radius: FeiMiaoRadius.card,
            fillColor: .fmCard,
            padding: EdgeInsets()
        ) {
            VStack(spacing: 0) {
                dayHeader

                ForEach(Array(group.items.enumerated()), id: \.element.id) { index, item in
                    if index > 0 {
                        Rectangle()
                            .fill(Color.fmHairline.opacity(1.3))
                            .frame(height: 0.5)
                            .padding(.leading, 66)
                            .padding(.trailing, 14)
                    }

                    Button {
                        onSelect(item)
                    } label: {
                        TransactionRow(
                            transaction: item,
                            netAmount: netAmount(item)
                        )
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                    }
                    .buttonStyle(.feiMiaoPressable)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 10)
    }

    private var dayHeader: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 8) {
                Text(dateLabel)
                    .font(.system(size: 13.5, weight: .medium))
                    .foregroundStyle(Color.fmSecondaryText)
                Spacer(minLength: 10)
                totals
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(dateLabel)
                    .font(.system(size: 13.5, weight: .medium))
                    .foregroundStyle(Color.fmSecondaryText)
                HStack {
                    Spacer()
                    totals
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.top, 12)
        .padding(.bottom, 8)
    }

    private var totals: some View {
        HStack(spacing: 8) {
            if totalExpense > .zero {
                Text("支 \(plainAmount(totalExpense))")
            }
            if totalIncome > .zero {
                Text("收 \(plainAmount(totalIncome))")
            }
        }
        .font(.system(size: 12, weight: .regular, design: .rounded).monospacedDigit())
        .foregroundStyle(Color.fmSecondaryText)
        .lineLimit(1)
    }

    private var dateLabel: String {
        let calendar = Calendar.current
        let day = calendar.startOfDay(for: group.day)
        let today = calendar.startOfDay(for: .now)
        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)
        let full = "\(calendar.component(.month, from: day))月\(calendar.component(.day, from: day))日 周\(weekday(day))"
        if day == today { return "今天 · \(full)" }
        if day == yesterday { return "昨天 · \(full)" }
        return full
    }

    private func weekday(_ date: Date) -> String {
        let symbols = ["日", "一", "二", "三", "四", "五", "六"]
        let index = Calendar.current.component(.weekday, from: date) - 1
        return symbols[index]
    }

    private func plainAmount(_ amount: MoneyAmount) -> String {
        amount.yuanText.replacingOccurrences(of: "¥", with: "")
    }
}
