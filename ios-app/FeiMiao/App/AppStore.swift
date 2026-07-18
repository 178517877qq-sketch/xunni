import Foundation
import SwiftUI
import FeiMiaoData
import FeiMiaoDomain

@MainActor
final class AppStore: ObservableObject {
    @Published private(set) var books: [LedgerBook] = []
    @Published private(set) var accounts: [LedgerAccount] = []
    @Published private(set) var categories: [LedgerCategory] = []
    @Published private(set) var tags: [LedgerTag] = []
    @Published private(set) var transactions: [LedgerTransaction] = []
    @Published private(set) var summary = LedgerSummary()
    @Published private(set) var netAmounts: [Int64: MoneyAmount] = [:]
    @Published private(set) var accountBalances: [Int64: MoneyAmount] = [:]
    @Published private(set) var isImportingBackup = false
    @Published private(set) var isReady = false
    @Published var selectedBookID: Int64?
    @Published var presentedError: String?

    private(set) var repository: LedgerRepository?
    private(set) var databaseURL: URL?

    init() {
        Task { await bootstrap() }
    }

    private func bootstrap() async {
        do {
            let result = try await Task.detached(priority: .userInitiated) {
                let url = try AppDatabase.defaultURL()
                let database = try AppDatabase(url: url)
                return (url, LedgerRepository(database: database))
            }.value
            let (url, repository) = result
            databaseURL = url
            self.repository = repository
            reloadAll()
        } catch {
            databaseURL = nil
            repository = nil
            presentedError = "无法打开账本：\(error.localizedDescription)"
        }
        isReady = true
    }

    var defaultBookID: Int64? {
        books.min {
            if $0.sortOrder == $1.sortOrder { return $0.id < $1.id }
            return $0.sortOrder < $1.sortOrder
        }?.id
    }

    func setSelectedBook(_ id: Int64?) {
        selectedBookID = id
        do {
            try repository?.setSetting(id.map { String($0) } ?? "total", for: "ios_selected_book")
        } catch {
            report(error)
        }
        reloadLedger()
    }

    func reloadAll() {
        guard let repository else { return }
        do {
            books = try repository.books()
            accounts = try repository.accounts()
            categories = try repository.categories(includeHidden: true)
            tags = try repository.tags()
            if selectedBookID == nil,
               let stored = try repository.setting(for: "ios_selected_book"),
               stored != "total",
               let storedID = Int64(stored),
               books.contains(where: { $0.id == storedID }) {
                selectedBookID = storedID
            } else if let selectedBookID,
                      !books.contains(where: { $0.id == selectedBookID }) {
                self.selectedBookID = nil
                try repository.setSetting("total", for: "ios_selected_book")
            }
            try reloadLedgerThrowing(repository: repository)
        } catch {
            report(error)
        }
    }

    func reloadLedger() {
        guard let repository else { return }
        do {
            try reloadLedgerThrowing(repository: repository)
        } catch {
            report(error)
        }
    }

    private func reloadLedgerThrowing(repository: LedgerRepository) throws {
        let filter = TransactionFilter(bookID: selectedBookID)
        let records = try repository.transactions(filter: filter)
        transactions = records
        let calendar = Calendar.current
        let monthStart = calendar.date(
            from: calendar.dateComponents([.year, .month], from: .now)
        )
        let nextMonth = monthStart.flatMap { calendar.date(byAdding: .month, value: 1, to: $0) }
        summary = try repository.summary(
            filter: TransactionFilter(
                bookID: selectedBookID,
                startDate: monthStart,
                endDate: nextMonth?.addingTimeInterval(-0.001)
            )
        )
        netAmounts = try repository.netAmounts(for: records)
        accountBalances = try repository.accountBalances()
    }

    func transactions(matching filter: TransactionFilter) -> [LedgerTransaction] {
        guard let repository else { return [] }
        do {
            return try repository.transactions(filter: filter)
        } catch {
            report(error)
            return []
        }
    }

    @discardableResult
    func saveTransaction(_ draft: TransactionDraft) -> LedgerTransaction? {
        guard let repository else { return nil }
        do {
            let record = try repository.saveTransaction(draft)
            reloadAll()
            return record
        } catch {
            report(error)
            return nil
        }
    }

    func deleteTransaction(_ id: Int64) {
        perform {
            try repository?.deleteTransaction(id: id)
        }
    }

    func createBook(name: String, icon: String, cover: String, remark: String, includeInTotal: Bool) {
        perform {
            try repository?.createBook(
                name: name,
                icon: icon,
                cover: cover,
                remark: remark,
                includeInTotal: includeInTotal
            )
        }
    }

    func updateBook(_ book: LedgerBook) {
        perform { try repository?.updateBook(book) }
    }

    func deleteBook(_ id: Int64) {
        perform { try repository?.deleteBook(id: id) }
    }

    func createAccount(
        name: String,
        type: String,
        openingBalance: MoneyAmount,
        includeInNetWorth: Bool,
        institution: String
    ) {
        perform {
            try repository?.createAccount(
                name: name,
                type: type,
                openingBalance: openingBalance,
                includeInNetWorth: includeInNetWorth,
                institution: institution
            )
        }
    }

    func updateAccount(_ account: LedgerAccount) {
        perform { try repository?.updateAccount(account) }
    }

    func deleteAccount(_ id: Int64) {
        perform { try repository?.deleteAccount(id: id) }
    }

    func accountIsInUse(_ id: Int64) -> Bool? {
        guard let repository else { return nil }
        do {
            return try repository.accountIsInUse(id: id)
        } catch {
            report(error)
            return nil
        }
    }

    func createCategory(name: String, emoji: String, kind: TransactionKind, parentID: Int64?) {
        perform {
            try repository?.createCategory(name: name, emoji: emoji, kind: kind, parentID: parentID)
        }
    }

    func updateCategory(_ category: LedgerCategory) {
        perform { try repository?.updateCategory(category) }
    }

    func deleteCategory(_ id: Int64) {
        perform { try repository?.deleteCategory(id: id) }
    }

    func createTag(name: String, colorARGB: Int64) {
        perform { try repository?.createTag(name: name, colorARGB: colorARGB) }
    }

    func updateTag(_ tag: LedgerTag) {
        perform { try repository?.updateTag(tag) }
    }

    func deleteTag(_ id: Int64) {
        perform { try repository?.deleteTag(id: id) }
    }

    func saveReceipt(_ data: Data) throws -> String {
        guard let databaseURL else {
            throw CocoaError(.fileNoSuchFile)
        }
        let directory = databaseURL.deletingLastPathComponent().appendingPathComponent("receipts", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let url = directory.appendingPathComponent("\(UUID().uuidString.lowercased()).jpg")
        try data.write(to: url, options: .atomic)
        return url.path
    }

    /// Removes only files managed by this app's receipts directory. Imported
    /// legacy paths outside the sandbox are never touched.
    func discardManagedReceipt(at path: String) {
        guard let databaseURL, !path.isEmpty else { return }
        do {
            if try repository?.receiptIsReferenced(path) == true { return }
        } catch {
            report(error)
            return
        }
        let root = databaseURL.deletingLastPathComponent()
            .appendingPathComponent("receipts", isDirectory: true)
            .standardizedFileURL
        let candidate = URL(fileURLWithPath: path).standardizedFileURL
        let rootPrefix = root.path.hasSuffix("/") ? root.path : root.path + "/"
        guard candidate.path.hasPrefix(rootPrefix) else { return }
        do {
            if FileManager.default.fileExists(atPath: candidate.path) {
                try FileManager.default.removeItem(at: candidate)
            }
        } catch {
            report(error)
        }
    }

    func importAndroidBackup(from url: URL) async -> AndroidBackupImportResult? {
        guard let repository, !isImportingBackup else { return nil }
        isImportingBackup = true
        let accessedSecurityScope = url.startAccessingSecurityScopedResource()
        defer {
            if accessedSecurityScope { url.stopAccessingSecurityScopedResource() }
            isImportingBackup = false
        }
        do {
            let database = repository.database
            let result = try await Task.detached(priority: .userInitiated) {
                try AndroidBackupImporter(database: database).importBackup(from: url)
            }.value
            selectedBookID = nil
            reloadAll()
            return result
        } catch {
            report(error)
            return nil
        }
    }

    func category(for id: Int64?) -> LedgerCategory? {
        guard let id else { return nil }
        return categories.first { $0.id == id }
    }

    func account(for id: Int64?) -> LedgerAccount? {
        guard let id else { return nil }
        return accounts.first { $0.id == id }
    }

    func book(for id: Int64?) -> LedgerBook? {
        guard let id else { return nil }
        return books.first { $0.id == id }
    }

    func netAmount(for transaction: LedgerTransaction) -> MoneyAmount {
        netAmounts[transaction.id] ?? transaction.amount
    }

    private func perform(_ operation: () throws -> Void) {
        do {
            try operation()
            reloadAll()
        } catch {
            report(error)
        }
    }

    private func report(_ error: Error) {
        presentedError = error.localizedDescription
    }
}
