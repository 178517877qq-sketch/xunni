import SwiftUI
import FeiMiaoDomain

struct CategoriesManagementView: View {
    @EnvironmentObject private var store: AppStore
    @State private var kind = TransactionKind.expense
    @State private var editorRoute: CategoryEditorRoute?
    @State private var pendingDeletion: LedgerCategory?

    private var categories: [LedgerCategory] {
        store.categories
            .filter { $0.kind == kind && !$0.isDeleted }
            .sorted(by: categoryOrder)
    }

    private var roots: [LedgerCategory] {
        categories.filter { $0.parentID == nil }
    }

    var body: some View {
        List {
            Section {
                Picker("收支类型", selection: $kind) {
                    Text("支出").tag(TransactionKind.expense)
                    Text("收入").tag(TransactionKind.income)
                }
                .pickerStyle(.segmented)
                .listRowInsets(EdgeInsets())
                .listRowBackground(Color.clear)
            }

            Section {
                if roots.isEmpty {
                    ContentUnavailableView(
                        "暂无\(kind.title)分类",
                        systemImage: "square.grid.2x2",
                        description: Text("先新增一级分类，再按需补充二级分类。")
                    )
                    .frame(maxWidth: .infinity)
                    .listRowBackground(Color.clear)
                } else {
                    ForEach(roots) { root in
                        categoryRow(root, isChild: false)
                        ForEach(children(of: root)) { child in
                            categoryRow(child, isChild: true)
                        }
                    }
                }
            } header: {
                Text("一级与二级分类")
            } footer: {
                Text("隐藏分类不会影响历史账单，只会从日常分类选择中移除。")
            }
        }
        .navigationTitle("分类管理")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    editorRoute = CategoryEditorRoute(category: nil, kind: kind)
                } label: {
                    Label("新增分类", systemImage: "plus")
                }
                .accessibilityIdentifier("add-category")
            }
        }
        .sheet(item: $editorRoute) { route in
            CategoryEditorView(category: route.category, kind: route.kind)
        }
        .confirmationDialog(
            "删除“\(pendingDeletion?.nameZh ?? "")”？",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("删除", role: .destructive) {
                guard let category = pendingDeletion else { return }
                store.deleteCategory(category.id)
                pendingDeletion = nil
            }
            Button("取消", role: .cancel) { pendingDeletion = nil }
        } message: {
            if let category = pendingDeletion, !children(of: category).isEmpty {
                Text("历史账单会变为未分类，它的二级分类会保留并提升为一级分类。")
            } else {
                Text("历史账单会保留，但会变为未分类。")
            }
        }
    }

    private func categoryRow(_ category: LedgerCategory, isChild: Bool) -> some View {
        Button {
            editorRoute = CategoryEditorRoute(category: category, kind: kind)
        } label: {
            HStack(spacing: 10) {
                if isChild {
                    Image(systemName: "arrow.turn.down.right")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .frame(width: 18)
                }
                Text(category.emoji.isEmpty ? "🏷️" : category.emoji)
                    .frame(width: 30, height: 30)
                    .background(Color(.tertiarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
                VStack(alignment: .leading, spacing: 2) {
                    Text(category.nameZh)
                        .font(isChild ? .body : .body.weight(.semibold))
                        .foregroundStyle(category.isHidden ? .secondary : .primary)
                    Text(isChild ? "二级分类" : "一级分类")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if category.isHidden {
                    Label("已隐藏", systemImage: "eye.slash")
                        .labelStyle(.iconOnly)
                        .foregroundStyle(.secondary)
                        .accessibilityLabel("已隐藏")
                }
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(.leading, isChild ? 18 : 0)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("category-row-\(category.id)")
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button("删除", role: .destructive) {
                pendingDeletion = category
            }
            Button("编辑") {
                editorRoute = CategoryEditorRoute(category: category, kind: kind)
            }
            .tint(.fmPrimary)
        }
        .swipeActions(edge: .leading, allowsFullSwipe: true) {
            Button {
                setVisibility(of: category, hidden: !category.isHidden)
            } label: {
                Label(category.isHidden ? "显示" : "隐藏", systemImage: category.isHidden ? "eye" : "eye.slash")
            }
            .tint(.gray)
        }
    }

    private func children(of category: LedgerCategory) -> [LedgerCategory] {
        categories.filter { $0.parentID == category.id }.sorted(by: categoryOrder)
    }

    private func categoryOrder(_ lhs: LedgerCategory, _ rhs: LedgerCategory) -> Bool {
        lhs.sortOrder == rhs.sortOrder ? lhs.id < rhs.id : lhs.sortOrder < rhs.sortOrder
    }

    private func setVisibility(of category: LedgerCategory, hidden: Bool) {
        guard store.databaseURL != nil else {
            store.presentedError = "账本数据库当前不可用，请稍后重试。"
            return
        }
        store.presentedError = nil
        let affected = category.parentID == nil
            ? [category] + children(of: category)
            : [category]
        for var item in affected {
            item.isHidden = hidden
            store.updateCategory(item)
            if store.presentedError != nil { break }
        }
    }
}

private struct CategoryEditorRoute: Identifiable {
    let id = UUID()
    let category: LedgerCategory?
    let kind: TransactionKind
}

private struct CategoryEditorView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    private let category: LedgerCategory?
    private let kind: TransactionKind
    @State private var name: String
    @State private var emoji: String
    @State private var makeChild: Bool
    @State private var parentID: Int64?
    @State private var isHidden: Bool

    init(category: LedgerCategory?, kind: TransactionKind) {
        self.category = category
        self.kind = kind
        _name = State(initialValue: category?.nameZh ?? "")
        _emoji = State(initialValue: category?.emoji ?? "🏷️")
        _makeChild = State(initialValue: category?.parentID != nil)
        _parentID = State(initialValue: category?.parentID)
        _isHidden = State(initialValue: category?.isHidden ?? false)
    }

    private var parentChoices: [LedgerCategory] {
        let preservedParentID = category?.parentID
        return store.categories
            .filter {
                $0.kind == kind && $0.parentID == nil
                    && (!$0.isHidden || $0.id == preservedParentID)
                    && !$0.isDeleted && $0.id != category?.id
            }
            .sorted {
                $0.sortOrder == $1.sortOrder ? $0.id < $1.id : $0.sortOrder < $1.sortOrder
            }
    }

    private var hasChildren: Bool {
        guard let category else { return false }
        return store.categories.contains { $0.parentID == category.id && !$0.isDeleted }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("分类信息") {
                    HStack {
                        TextField("图标", text: $emoji)
                            .multilineTextAlignment(.center)
                            .frame(width: 54)
                        TextField("分类名称", text: $name)
                    }
                }

                Section {
                    Toggle("设为二级分类", isOn: $makeChild)
                        .disabled(hasChildren || parentChoices.isEmpty)

                    if makeChild {
                        Picker("上级分类", selection: $parentID) {
                            ForEach(parentChoices) { parent in
                                Text(
                                    parent.isHidden
                                        ? "\(parent.emoji) \(parent.nameZh)（已隐藏）"
                                        : "\(parent.emoji) \(parent.nameZh)"
                                )
                                    .tag(Int64?.some(parent.id))
                            }
                        }
                    }
                } header: {
                    Text("层级")
                } footer: {
                    if hasChildren {
                        Text("该分类已有二级分类，因此不能再设为其他分类的二级分类。")
                    } else if parentChoices.isEmpty {
                        Text("当前没有可选的一级分类。")
                    } else {
                        Text("分类最多两级；二级分类必须归属于同一收支类型的一级分类。")
                    }
                }

                if category != nil {
                    Section {
                        Toggle("隐藏分类", isOn: $isHidden)
                    } footer: {
                        Text("隐藏后历史账单保持不变。")
                    }
                }
            }
            .navigationTitle(category == nil ? "新增\(kind.title)分类" : "编辑分类")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存", action: save)
                        .disabled(!canSave)
                }
            }
            .onAppear {
                if makeChild, !parentChoices.contains(where: { $0.id == parentID }) {
                    parentID = parentChoices.first?.id
                    if parentID == nil { makeChild = false }
                }
            }
            .onChange(of: makeChild) { _, isChild in
                if isChild {
                    if parentID == nil { parentID = parentChoices.first?.id }
                } else {
                    parentID = nil
                }
            }
        }
    }

    private var canSave: Bool {
        !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && (!makeChild || parentID != nil)
            && !(hasChildren && makeChild)
    }

    private func save() {
        guard canSave else { return }
        let cleanEmoji = emoji.trimmingCharacters(in: .whitespacesAndNewlines)
        guard store.databaseURL != nil else {
            store.presentedError = "账本数据库当前不可用，请稍后重试。"
            return
        }
        store.presentedError = nil
        if var category {
            let children = store.categories.filter { $0.parentID == category.id && !$0.isDeleted }
            let visibilityChanged = category.isHidden != isHidden
            category.nameZh = name
            category.emoji = cleanEmoji.isEmpty ? "🏷️" : cleanEmoji
            category.parentID = makeChild ? parentID : nil
            category.isHidden = isHidden
            store.updateCategory(category)
            if visibilityChanged, category.parentID == nil, store.presentedError == nil {
                for var child in children {
                    child.isHidden = isHidden
                    store.updateCategory(child)
                    if store.presentedError != nil { break }
                }
            }
        } else {
            store.createCategory(
                name: name,
                emoji: cleanEmoji.isEmpty ? "🏷️" : cleanEmoji,
                kind: kind,
                parentID: makeChild ? parentID : nil
            )
        }
        if store.presentedError == nil { dismiss() }
    }
}
