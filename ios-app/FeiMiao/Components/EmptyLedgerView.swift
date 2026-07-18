import SwiftUI

struct EmptyLedgerView: View {
    var title = "还没有账单"
    var message = "记下第一笔，肥喵会从这里帮你整理。"
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        ContentUnavailableView {
            Label(title, systemImage: "cat.fill")
        } description: {
            Text(message)
        } actions: {
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(.borderedProminent)
            }
        }
    }
}
