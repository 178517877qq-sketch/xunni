import SwiftUI

struct BookMenu: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        Menu {
            Button {
                store.setSelectedBook(nil)
            } label: {
                Label("总账本", systemImage: store.selectedBookID == nil ? "checkmark" : "books.vertical")
            }
            ForEach(store.books.filter { $0.id != store.defaultBookID }) { book in
                Button {
                    store.setSelectedBook(book.id)
                } label: {
                    Label(
                        "\(book.icon) \(book.name)",
                        systemImage: store.selectedBookID == book.id ? "checkmark" : "book.closed"
                    )
                }
            }
        } label: {
            HStack(spacing: 5) {
                Text(selectedIcon)
                    .font(.system(size: 15))
                Text(selectedTitle)
                    .font(.system(size: 14, weight: .medium))
                    .lineLimit(1)
                    .frame(maxWidth: 120)
                Image(systemName: "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(Color.fmSecondaryText)
            }
            .foregroundStyle(.primary)
            .padding(.horizontal, 10)
            .frame(height: 36)
            .background(Color.fmCard, in: Capsule())
            .overlay { Capsule().stroke(Color.fmHairline, lineWidth: 0.5) }
            .shadow(color: Color.black.opacity(0.035), radius: 7, y: 2)
        }
        .buttonStyle(.feiMiaoPressable)
        .accessibilityIdentifier("book-menu")
    }

    private var selectedTitle: String {
        store.book(for: store.selectedBookID)?.name ?? "总账本"
    }

    private var selectedIcon: String {
        if let selectedBookID = store.selectedBookID {
            return store.book(for: selectedBookID)?.icon ?? "📒"
        }
        return store.book(for: store.defaultBookID)?.icon ?? "📒"
    }
}
