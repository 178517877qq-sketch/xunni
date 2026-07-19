import SwiftUI

struct HomeRecordInputBar: View {
    let openManualEntry: () -> Void

    var body: some View {
        ParityGlassSurface(
            radius: 24,
            blurred: true,
            fillColor: .fmCard,
            padding: EdgeInsets(top: 14, leading: 14, bottom: 10, trailing: 10),
            castsShadow: true
        ) {
            VStack(alignment: .leading, spacing: 10) {
                Button(action: openManualEntry) {
                    Text("记一记")
                        .font(.system(size: 17, weight: .regular))
                        .foregroundStyle(Color.primary.opacity(0.55))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.feiMiaoPressable)

                HStack(spacing: 6) {
                    toolButton(systemImage: "plus", label: "打开手动记账")

                    Button(action: openManualEntry) {
                        HStack(spacing: 6) {
                            Image(systemName: "square.and.pencil")
                                .font(.system(size: 13, weight: .regular))
                            Text("手动记账")
                                .font(.system(size: 13, weight: .regular))
                        }
                        .foregroundStyle(Color.fmSecondaryText)
                        .padding(.horizontal, 11)
                        .frame(height: 32)
                        .background(Color.fmCard, in: Capsule())
                        .overlay { Capsule().stroke(Color.fmHairline, lineWidth: 0.5) }
                    }
                    .buttonStyle(.feiMiaoPressable)

                    Spacer()

                    toolButton(systemImage: "arrow.up", label: "记账")
                }
            }
        }
        .accessibilityIdentifier("home-record-input")
    }

    private func toolButton(systemImage: String, label: String) -> some View {
        Button(action: openManualEntry) {
            Image(systemName: systemImage)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(Color.fmSecondaryText)
                .frame(width: 32, height: 32)
                .background(Color.fmCard, in: Circle())
                .overlay { Circle().stroke(Color.fmHairline, lineWidth: 0.5) }
                .contentShape(Circle())
        }
        .buttonStyle(.feiMiaoPressable)
        .accessibilityLabel(label)
    }
}
