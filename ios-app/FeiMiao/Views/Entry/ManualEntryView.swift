import PhotosUI
import SwiftUI
import UIKit
import FeiMiaoDomain

struct ManualEntryView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    private let editing: LedgerTransaction?
    private let onSaved: () -> Void

    @State private var kind: TransactionKind
    @State private var amountText: String
    @State private var bookID: Int64?
    @State private var categoryID: Int64?
    @State private var accountID: Int64?
    @State private var toAccountID: Int64?
    @State private var note: String
    @State private var date: Date
    @State private var timePrecision: TransactionTimePrecision
    @State private var selectedTagIDs: Set<Int64>
    @State private var isReimbursable: Bool
    @State private var isExcluded: Bool
    @State private var imagePath: String
    @State private var pendingReceiptData: Data?
    @State private var photoItem: PhotosPickerItem?
    @State private var isSavingPhoto = false

    init(editing: LedgerTransaction? = nil, onSaved: @escaping () -> Void = {}) {
        self.editing = editing
        self.onSaved = onSaved
        _kind = State(initialValue: editing?.kind ?? .expense)
        _amountText = State(initialValue: editing?.amount.storageString ?? "")
        _bookID = State(initialValue: editing?.bookID)
        _categoryID = State(initialValue: editing?.categoryID)
        _accountID = State(initialValue: editing?.accountID)
        _toAccountID = State(initialValue: editing?.toAccountID)
        _note = State(initialValue: editing?.note ?? "")
        _date = State(initialValue: editing?.date ?? .now)
        _timePrecision = State(initialValue: editing?.timePrecision ?? .exact)
        _selectedTagIDs = State(initialValue: Set(editing?.tagIDs ?? []))
        _isReimbursable = State(initialValue: editing?.isReimbursable ?? false)
        _isExcluded = State(initialValue: editing?.isExcluded ?? false)
        _imagePath = State(initialValue: editing?.imagePath ?? "")
        _pendingReceiptData = State(initialValue: nil)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("类型", selection: $kind) {
                        ForEach(TransactionKind.allCases) { value in
                            Text(value.title).tag(value)
                        }
                    }
                    .pickerStyle(.segmented)

                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text("¥")
                            .font(.title2.weight(.semibold))
                            .foregroundStyle(.secondary)
                        TextField("0.00", text: $amountText)
                            .font(.system(size: 38, weight: .semibold, design: .rounded))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .accessibilityLabel("金额")
                            .accessibilityIdentifier("amount-field")
                    }
                    .padding(.vertical, 8)
                }

                Section("归属") {
                    if kind != .transfer {
                        NavigationLink {
                            CategorySelectionView(kind: kind, selection: $categoryID)
                        } label: {
                            LabeledContent("分类") {
                                Text(selectedCategoryTitle)
                                    .foregroundStyle(categoryID == nil ? .secondary : .primary)
                            }
                        }
                    }

                    Picker(kind == .transfer ? "转出账户" : "账户", selection: $accountID) {
                        Text("请选择").tag(Int64?.none)
                        ForEach(sourceAccounts) { account in
                            Text(accountPickerTitle(account)).tag(Int64?.some(account.id))
                        }
                    }

                    if kind == .transfer {
                        Picker("转入账户", selection: $toAccountID) {
                            Text("请选择").tag(Int64?.none)
                            ForEach(destinationAccounts) { account in
                                Text(accountPickerTitle(account)).tag(Int64?.some(account.id))
                            }
                        }
                    }

                    Picker("账本", selection: $bookID) {
                        ForEach(store.books) { book in
                            Text("\(book.icon) \(book.name)").tag(Int64?.some(book.id))
                        }
                    }
                }

                Section("时间与备注") {
                    if hasKnownTime {
                        DatePicker(
                            "日期时间",
                            selection: $date,
                            displayedComponents: [.date, .hourAndMinute]
                        )
                    } else {
                        DatePicker("日期", selection: $date, displayedComponents: .date)
                        HStack {
                            Label("原账单未记录具体时分", systemImage: "clock.badge.questionmark")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Button("补录时间", action: addExactTime)
                        }
                    }
                    TextField("写点备注", text: $note, axis: .vertical)
                        .lineLimit(1...4)
                        .submitLabel(.done)
                        .accessibilityIdentifier("note-field")
                    NavigationLink {
                        TagSelectionView(selection: $selectedTagIDs)
                    } label: {
                        LabeledContent("标签") {
                            Text(selectedTagTitle)
                                .foregroundStyle(selectedTagIDs.isEmpty ? .secondary : .primary)
                        }
                    }
                }

                Section("附件") {
                    PhotosPicker(selection: $photoItem, matching: .images) {
                        Label(
                            imagePath.isEmpty && pendingReceiptData == nil ? "添加图片" : "更换图片",
                            systemImage: "photo.badge.plus"
                        )
                    }
                    .disabled(isSavingPhoto)
                    if isSavingPhoto {
                        ProgressView("正在保存图片")
                    }
                    if let image = receiptImage {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFill()
                            .frame(height: 160)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .clipped()
                            .accessibilityLabel("账单附件预览")
                        Button("移除图片", role: .destructive) {
                            pendingReceiptData = nil
                            imagePath = ""
                        }
                    }
                }

                if kind == .expense {
                    Section("账单状态") {
                        Toggle("待报销", isOn: $isReimbursable)
                        Toggle("不计入收支", isOn: $isExcluded)
                    }
                }
            }
            .navigationTitle(editing == nil ? "记一笔" : "编辑账单")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if editing != nil {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("取消") { dismiss() }
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存", action: save)
                        .disabled(!canSave || isSavingPhoto)
                        .accessibilityIdentifier("save-transaction")
                }
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("保存", action: save)
                        .disabled(!canSave || isSavingPhoto)
                }
            }
            .onAppear {
                if editing == nil,
                   amountText.isEmpty,
                   note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    bookID = store.selectedBookID ?? store.defaultBookID
                } else if !store.books.contains(where: { $0.id == bookID }) {
                    bookID = store.selectedBookID ?? store.defaultBookID
                }
                if !sourceAccounts.contains(where: { $0.id == accountID }) {
                    accountID = sourceAccounts.first?.id
                }
                if let toAccountID,
                   !destinationAccounts.contains(where: { $0.id == toAccountID }) {
                    self.toAccountID = nil
                }
            }
            .onChange(of: kind) { _, newKind in
                if newKind == .transfer {
                    categoryID = nil
                    isReimbursable = false
                    isExcluded = false
                } else {
                    toAccountID = nil
                    if store.category(for: categoryID)?.kind != newKind { categoryID = nil }
                }
            }
            .onChange(of: photoItem) { _, newValue in
                guard let newValue else { return }
                isSavingPhoto = true
                Task { await loadPhoto(newValue) }
            }
        }
    }

    private var canSave: Bool {
        guard MoneyAmount(amountText).map({ $0 > .zero }) == true, accountID != nil, bookID != nil else {
            return false
        }
        if kind == .transfer {
            return toAccountID != nil && toAccountID != accountID
        }
        return true
    }

    private var hasKnownTime: Bool {
        timePrecision == .exact || timePrecision == .entryClock
    }

    private func addExactTime() {
        let calendar = Calendar.current
        let day = calendar.dateComponents([.year, .month, .day], from: date)
        let clock = calendar.dateComponents([.hour, .minute], from: Date.now)
        var combined = day
        combined.hour = clock.hour
        combined.minute = clock.minute
        if let updated = calendar.date(from: combined) {
            date = updated
        }
        timePrecision = .exact
    }

    private var sourceAccounts: [LedgerAccount] {
        accountsForPicker(preserving: editing?.accountID)
    }

    private var destinationAccounts: [LedgerAccount] {
        accountsForPicker(preserving: editing?.toAccountID)
    }

    private func accountsForPicker(preserving historicalID: Int64?) -> [LedgerAccount] {
        store.accounts.filter {
            $0.isAvailableForNewTransactions || $0.id == historicalID
        }
    }

    private func accountPickerTitle(_ account: LedgerAccount) -> String {
        account.isAvailableForNewTransactions ? account.name : "\(account.name)（已归档）"
    }

    private var selectedCategoryTitle: String {
        guard let category = store.category(for: categoryID) else { return "未分类" }
        return "\(category.emoji) \(category.nameZh)"
    }

    private var selectedTagTitle: String {
        let names = store.tags.filter { selectedTagIDs.contains($0.id) }.map(\.name)
        return names.isEmpty ? "未选择" : names.joined(separator: "、")
    }

    private var receiptImage: UIImage? {
        if let pendingReceiptData {
            return UIImage(data: pendingReceiptData)
        }
        guard !imagePath.isEmpty else { return nil }
        return UIImage(contentsOfFile: imagePath)
    }

    @MainActor
    private func loadPhoto(_ item: PhotosPickerItem) async {
        defer {
            isSavingPhoto = false
            photoItem = nil
        }
        do {
            let selectedData = try await item.loadTransferable(type: Data.self)
            if let data = selectedData {
                guard UIImage(data: data) != nil else {
                    throw CocoaError(.fileReadCorruptFile)
                }
                pendingReceiptData = data
            }
        } catch {
            store.presentedError = "图片保存失败：\(error.localizedDescription)"
        }
    }

    private func save() {
        guard canSave else { return }
        var finalImagePath = imagePath
        var newlyWrittenImagePath: String?
        if let pendingReceiptData {
            do {
                finalImagePath = try store.saveReceipt(pendingReceiptData)
                newlyWrittenImagePath = finalImagePath
            } catch {
                store.presentedError = "图片保存失败：\(error.localizedDescription)"
                return
            }
        }
        let draft = TransactionDraft(
            id: editing?.id,
            bookID: bookID,
            kind: kind,
            amountText: amountText,
            currencyCode: editing?.currencyCode ?? "CNY",
            categoryID: kind == .transfer ? nil : categoryID,
            accountID: accountID,
            toAccountID: kind == .transfer ? toAccountID : nil,
            note: note,
            date: date,
            timePrecision: timePrecision,
            tagIDs: selectedTagIDs.sorted(),
            isReimbursable: kind == .expense && isReimbursable,
            imagePath: finalImagePath,
            isExcluded: kind == .expense && isExcluded
        )
        guard store.saveTransaction(draft) != nil else {
            if let newlyWrittenImagePath {
                store.discardManagedReceipt(at: newlyWrittenImagePath)
            }
            return
        }
        if let editing,
           !editing.imagePath.isEmpty,
           editing.imagePath != finalImagePath {
            store.discardManagedReceipt(at: editing.imagePath)
        }
        pendingReceiptData = nil
        imagePath = finalImagePath
        if editing == nil { resetForNextEntry() }
        onSaved()
        if editing != nil { dismiss() }
    }

    private func resetForNextEntry() {
        amountText = ""
        note = ""
        categoryID = nil
        selectedTagIDs = []
        imagePath = ""
        pendingReceiptData = nil
        photoItem = nil
        isReimbursable = false
        isExcluded = false
        date = .now
        timePrecision = .exact
    }
}

private struct CategorySelectionView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    let kind: TransactionKind
    @Binding var selection: Int64?

    private var categories: [LedgerCategory] {
        store.categories.filter { $0.kind == kind && !$0.isHidden && !$0.isDeleted }
    }

    private var roots: [LedgerCategory] {
        categories.filter { $0.parentID == nil }
    }

    var body: some View {
        List {
            Button {
                selection = nil
                dismiss()
            } label: {
                HStack {
                    Label("未分类", systemImage: "questionmark.circle")
                    Spacer()
                    if selection == nil { Image(systemName: "checkmark") }
                }
            }
            ForEach(roots) { root in
                Section {
                    categoryButton(root)
                    ForEach(categories.filter { $0.parentID == root.id }) { child in
                        categoryButton(child)
                            .padding(.leading, 18)
                    }
                } header: {
                    Text("\(root.emoji) \(root.nameZh)")
                }
            }
        }
        .navigationTitle("选择分类")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func categoryButton(_ category: LedgerCategory) -> some View {
        Button {
            selection = category.id
            dismiss()
        } label: {
            HStack {
                Text(category.emoji)
                Text(category.nameZh)
                    .foregroundStyle(.primary)
                Spacer()
                if selection == category.id {
                    Image(systemName: "checkmark")
                        .foregroundStyle(Color.fmPrimary)
                }
            }
        }
    }
}

private struct TagSelectionView: View {
    @EnvironmentObject private var store: AppStore
    @Binding var selection: Set<Int64>

    var body: some View {
        List(store.tags) { tag in
            Button {
                if selection.contains(tag.id) {
                    selection.remove(tag.id)
                } else {
                    selection.insert(tag.id)
                }
            } label: {
                HStack {
                    Label(tag.name, systemImage: "tag")
                        .foregroundStyle(.primary)
                    Spacer()
                    if selection.contains(tag.id) {
                        Image(systemName: "checkmark")
                            .foregroundStyle(Color.fmPrimary)
                    }
                }
            }
        }
        .navigationTitle("标签")
        .navigationBarTitleDisplayMode(.inline)
    }
}
