import SwiftUI

struct HomeTransactionFilterControl: View {
    @Binding var selection: HomeTransactionFilter
    @Namespace private var selectionAnimation

    var body: some View {
        HStack(spacing: 4) {
            ForEach(HomeTransactionFilter.allCases) { option in
                Button {
                    withAnimation(.easeOut(duration: 0.22)) {
                        selection = option
                    }
                } label: {
                    Text(option.rawValue)
                        .font(.system(size: 13.5, weight: selection == option ? .medium : .regular))
                        .foregroundStyle(selection == option ? Color.primary : Color.fmSecondaryText)
                        .frame(maxWidth: .infinity)
                        .frame(height: 36)
                        .background {
                            if selection == option {
                                RoundedRectangle(cornerRadius: 11, style: .continuous)
                                    .fill(Color.fmSelectedCard)
                                    .overlay {
                                        RoundedRectangle(cornerRadius: 11, style: .continuous)
                                            .stroke(Color.fmHairline.opacity(1.35), lineWidth: 0.5)
                                    }
                                    .matchedGeometryEffect(id: "selected-home-filter", in: selectionAnimation)
                            }
                        }
                }
                .buttonStyle(.feiMiaoPressable)
                .accessibilityAddTraits(selection == option ? .isSelected : [])
            }
        }
        .padding(3)
        .background(Color.fmCard, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color.fmHairline, lineWidth: 0.5)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 10)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("账单筛选")
        .accessibilityIdentifier("home-filter-control")
    }
}
