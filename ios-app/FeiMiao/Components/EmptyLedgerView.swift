import SwiftUI

struct EmptyLedgerView: View {
    var title = "还没有账单"
    var message = "记下第一笔，肥喵会从这里帮你整理。"
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: 10) {
            MascotView(mood: .empty, size: 168, animated: true)

            Text(title)
                .font(.system(size: 17, weight: .medium))
                .foregroundStyle(Color.primary)

            Text(message)
                .font(.system(size: 13, weight: .regular))
                .foregroundStyle(Color.fmSecondaryText)
                .multilineTextAlignment(.center)

            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(Color.primary)
                    .padding(.horizontal, 18)
                    .frame(height: 40)
                    .background(Color.fmCard, in: Capsule())
                    .overlay { Capsule().stroke(Color.fmHairline, lineWidth: 0.5) }
                    .buttonStyle(.feiMiaoPressable)
                    .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(24)
        .background(FeiMiaoPageBackground().ignoresSafeArea())
        .accessibilityElement(children: .contain)
    }
}
