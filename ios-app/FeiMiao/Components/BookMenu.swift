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
                Text(selectedTitle)
                    .font(.subheadline.weight(.semibold))
                Image(systemName: "chevron.down")
                    .font(.caption2.weight(.bold))
            }
            .foregroundStyle(.primary)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color(.secondarySystemBackground), in: Capsule())
        }
        .accessibilityIdentifier("book-menu")
    }

    private var selectedTitle: String {
        store.book(for: store.selectedBookID)?.name ?? "总账本"
    }
}
