import SwiftUI
import FeiMiaoDomain

struct HomeSummaryCard: View {
    let month: Date
    let summary: LedgerSummary
    let canAdvanceMonth: Bool
    let onPreviousMonth: () -> Void
    let onNextMonth: () -> Void
    let onChooseMonth: () -> Void
    let onReturnToCurrentMonth: () -> Void

    private let calendar = Calendar.current

    var body: some View {
        ZStack(alignment: .topTrailing) {
            ParityGlassSurface(
                radius: FeiMiaoRadius.card,
                fillColor: .fmCard,
                padding: EdgeInsets(top: 12, leading: 16, bottom: 14, trailing: 16)
            ) {
                VStack(spacing: 0) {
                    header
                    Spacer().frame(height: 13)
                    incomeExpenseOverview
                    Spacer().frame(height: 13)
                    footer
                }
            }

            HomePeekingMascotView(isOverspending: false, height: 96)
                .offset(x: 4, y: -8)
                .allowsHitTesting(false)
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 8)
        .simultaneousGesture(monthSwipeGesture)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("home-summary-card")
    }

    private var header: some View {
        HStack(spacing: 8) {
            Button(action: onChooseMonth) {
                HStack(spacing: 4) {
                    Text(monthTitle)
                        .font(.system(size: 14, weight: .regular))
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(Color.fmSecondaryText)
                }
                .foregroundStyle(Color.primary)
                .frame(height: 28)
                .contentShape(Rectangle())
            }
            .buttonStyle(.feiMiaoPressable)
            .accessibilityHint(isCurrentMonth ? "选择月份" : "长按返回本月")
            .onLongPressGesture(minimumDuration: 0.45) {
                if !isCurrentMonth { onReturnToCurrentMonth() }
            }

            HStack(spacing: 2) {
                Text("统计")
                    .font(.system(size: 12, weight: .regular))
                Image(systemName: "chevron.right")
                    .font(.system(size: 9, weight: .semibold))
            }
            .foregroundStyle(Color.fmSecondaryText)
            .padding(.leading, 9)
            .padding(.trailing, 7)
            .frame(height: 26)
            .background(Color.fmCard, in: Capsule())
            .overlay { Capsule().stroke(Color.fmHairline, lineWidth: 0.5) }
            .accessibilityLabel("统计功能将在统计批次接入")

            Spacer(minLength: 82)
        }
    }

    private var incomeExpenseOverview: some View {
        HStack(spacing: 0) {
            moneyColumn(
                label: "支出",
                amount: summary.expense,
                color: .primary
            )

            Rectangle()
                .fill(Color.fmHairline.opacity(1.8))
                .frame(width: 0.5, height: 42)
                .padding(.horizontal, 12)

            moneyColumn(
                label: "收入",
                amount: summary.income,
                color: .fmIncome
            )
        }
        .padding(.trailing, 72)
    }

    private var footer: some View {
        HStack {
            Text("结余 \(summary.balance.yuanText)")
                .font(.system(size: 12, weight: .regular, design: .rounded).monospacedDigit())
                .foregroundStyle(balanceColor.opacity(0.72))
                .lineLimit(1)
                .minimumScaleFactor(0.75)

            Spacer()

            HStack(spacing: 2) {
                Text("设置预算")
                Image(systemName: "chevron.right")
                    .font(.system(size: 9, weight: .semibold))
            }
            .font(.system(size: 12, weight: .regular))
            .foregroundStyle(Color.fmPrimary)
            .accessibilityLabel("预算功能将在预算批次接入")
        }
    }

    private func moneyColumn(label: String, amount: MoneyAmount, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(label)
                .font(.system(size: 12, weight: .light))
                .foregroundStyle(Color.fmHintText)

            Text(amount.yuanText)
                .font(.system(size: 23, weight: .medium, design: .rounded).monospacedDigit())
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.62)
                .contentTransition(.numericText())
        }
        .frame(maxWidth: .infinity)
    }

    private var monthSwipeGesture: some Gesture {
        DragGesture(minimumDistance: 32)
            .onEnded { value in
                // The left screen edge belongs to the root drawer gesture.
                // HomeSummaryCard itself starts 16pt from that edge.
                guard value.startLocation.x > 20 else { return }
                guard abs(value.translation.width) > abs(value.translation.height) * 1.35 else { return }
                if value.translation.width > 48 {
                    onPreviousMonth()
                } else if value.translation.width < -48, canAdvanceMonth {
                    onNextMonth()
                }
            }
    }

    private var monthTitle: String {
        "\(calendar.component(.year, from: month))年\(calendar.component(.month, from: month))月"
    }

    private var isCurrentMonth: Bool {
        calendar.isDate(month, equalTo: .now, toGranularity: .month)
    }

    private var balanceColor: Color {
        summary.balance < .zero ? .fmRisk : .primary
    }
}
