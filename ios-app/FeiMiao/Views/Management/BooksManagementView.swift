import SwiftUI
import FeiMiaoDomain

struct BooksManagementView: View {
    @EnvironmentObject private var store: AppStore
    @State private var editorRoute: BookEditorRoute?
    @State private var pendingDeletion: LedgerBook?

    private var defaultBookID: Int64? {
        store.books.min { lhs, rhs in
            lhs.sortOrder == rhs.sortOrder ? lhs.id < rhs.id : lhs.sortOrder < rhs.sortOrder
        }?.id
    }

    var body: some View {
        List {
            Section {
                if store.books.isEmpty {
                    ContentUnavailableView(
                        "还没有账本",
                        systemImage: "books.vertical",
                        description: Text("新建账本后，可以把不同场景的账单分开管理。")
                    )
                    .frame(maxWidth: .infinity)
                    .listRowBackground(Color.clear)
                } else {
                    ForEach(store.books) { book in
                        bookRow(book)
                    }
                }
            } footer: {
                Text("删除普通账本时，其中的历史账单会迁移到总账本，不会丢失。")
            }
        }
        .navigationTitle("账本管理")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    editorRoute = BookEditorRoute(book: nil, isDefault: false)
                } label: {
                    Label("新建账本", systemImage: "plus")
                }
                .accessibilityIdentifier("add-book")
            }
        }
        .sheet(item: $editorRoute) { route in
            BookEditorView(book: route.book, isDefault: route.isDefault)
        }
        .confirmationDialog(
            "删除“\(pendingDeletion?.name ?? "")”？",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("删除并迁移账单", role: .destructive) {
                guard let book = pendingDeletion else { return }
                guard store.databaseURL != nil else {
                    store.presentedError = "账本数据库当前不可用，请稍后重试。"
                    pendingDeletion = nil
                    return
                }
                let wasSelected = store.selectedBookID == book.id
                store.presentedError = nil
                store.deleteBook(book.id)
                if wasSelected, store.presentedError == nil { store.setSelectedBook(nil) }
                pendingDeletion = nil
            }
            Button("取消", role: .cancel) { pendingDeletion = nil }
        } message: {
            Text("该账本中的账单会迁移到总账本，此操作不会删除历史账单。")
        }
    }

    private func bookRow(_ book: LedgerBook) -> some View {
        let isDefault = book.id == defaultBookID
        return Button {
            editorRoute = BookEditorRoute(book: book, isDefault: isDefault)
        } label: {
            HStack(spacing: 12) {
                BookCoverView(cover: book.cover, fallbackIcon: book.icon)
                    .frame(width: 42, height: 50)
                    .clipShape(RoundedRectangle(cornerRadius: 9))

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(book.name)
                            .font(.body.weight(.medium))
                            .foregroundStyle(.primary)
                        if isDefault {
                            Text("默认")
                                .font(.caption2.weight(.medium))
                                .foregroundStyle(.fmPrimary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.fmPrimarySoft, in: Capsule())
                        }
                    }
                    if !book.remark.isEmpty {
                        Text(book.remark)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    } else {
                        Text(book.includeInTotal ? "计入总账本" : "不计入总账本")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                if book.isStarred {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.fmIncome)
                        .accessibilityLabel("已加星")
                }
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("book-row-\(book.id)")
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            if !isDefault {
                Button("删除", role: .destructive) {
                    pendingDeletion = book
                }
            }
            Button("编辑") {
                editorRoute = BookEditorRoute(book: book, isDefault: isDefault)
            }
            .tint(.fmPrimary)
        }
        .swipeActions(edge: .leading, allowsFullSwipe: true) {
            Button {
                var updated = book
                updated.isStarred.toggle()
                store.updateBook(updated)
            } label: {
                Label(book.isStarred ? "取消加星" : "加星", systemImage: book.isStarred ? "star.slash" : "star")
            }
            .tint(.fmIncome)
        }
    }
}

private struct BookEditorRoute: Identifiable {
    let id = UUID()
    let book: LedgerBook?
    let isDefault: Bool
}

private struct BookEditorView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    private let book: LedgerBook?
    private let isDefault: Bool
    @State private var name: String
    @State private var icon: String
    @State private var cover: String
    @State private var remark: String
    @State private var includeInTotal: Bool
    @State private var isStarred: Bool

    init(book: LedgerBook?, isDefault: Bool) {
        self.book = book
        self.isDefault = isDefault
        _name = State(initialValue: book?.name ?? "")
        _icon = State(initialValue: book?.icon ?? "📒")
        _cover = State(initialValue: {
            guard let cover = book?.cover, !cover.isEmpty else { return "default.png" }
            return cover
        }())
        _remark = State(initialValue: book?.remark ?? "")
        _includeInTotal = State(initialValue: book?.includeInTotal ?? true)
        _isStarred = State(initialValue: book?.isStarred ?? false)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("账本信息") {
                    HStack {
                        TextField("图标", text: $icon)
                            .multilineTextAlignment(.center)
                            .frame(width: 54)
                        TextField("账本名称", text: $name)
                    }
                    TextField("备注（可选）", text: $remark, axis: .vertical)
                        .lineLimit(1...3)
                }

                Section("封面") {
                    ScrollView(.horizontal) {
                        HStack(spacing: 12) {
                            ForEach(BookCoverOption.all) { option in
                                Button {
                                    cover = option.token
                                } label: {
                                    VStack(spacing: 5) {
                                        BookCoverView(cover: option.token, fallbackIcon: icon)
                                            .frame(width: 54, height: 68)
                                            .clipShape(RoundedRectangle(cornerRadius: 10))
                                            .overlay {
                                                RoundedRectangle(cornerRadius: 10)
                                                    .stroke(
                                                        isSelected(option) ? Color.fmPrimary : Color.clear,
                                                        lineWidth: 3
                                                    )
                                            }
                                        Text(option.title)
                                            .font(.caption2)
                                            .foregroundStyle(isSelected(option) ? Color.fmPrimary : Color.secondary)
                                    }
                                    .frame(minWidth: 58, minHeight: 92)
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("\(option.title)封面")
                                .accessibilityAddTraits(isSelected(option) ? .isSelected : [])
                            }
                        }
                        .padding(.vertical, 2)
                    }
                    .scrollIndicators(.hidden)
                }

                Section {
                    Toggle("计入总账本", isOn: $includeInTotal)
                        .disabled(isDefault)
                    if book != nil {
                        Toggle("加星显示", isOn: $isStarred)
                    }
                } footer: {
                    Text(isDefault ? "总账本始终参与汇总，不能删除或排除。" : "关闭后，这个账本不会计入总账本的收支汇总。")
                }
            }
            .navigationTitle(book == nil ? "新建账本" : "编辑账本")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存", action: save)
                        .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }

    private func save() {
        let cleanIcon = icon.trimmingCharacters(in: .whitespacesAndNewlines)
        guard store.databaseURL != nil else {
            store.presentedError = "账本数据库当前不可用，请稍后重试。"
            return
        }
        store.presentedError = nil
        if var book {
            book.name = name
            book.icon = cleanIcon.isEmpty ? "📒" : cleanIcon
            book.cover = cover
            book.remark = remark
            book.includeInTotal = isDefault ? true : includeInTotal
            book.isStarred = isStarred
            store.updateBook(book)
        } else {
            store.createBook(
                name: name,
                icon: cleanIcon.isEmpty ? "📒" : cleanIcon,
                cover: cover,
                remark: remark,
                includeInTotal: includeInTotal
            )
        }
        if store.presentedError == nil { dismiss() }
    }

    private func isSelected(_ option: BookCoverOption) -> Bool {
        BookCoverOption.normalizedKey(for: cover)
            == BookCoverOption.normalizedKey(for: option.token)
    }
}
