import Foundation
import XCTest
@testable import FeiMiaoData
@testable import FeiMiaoDomain

final class LedgerRepositoryTests: XCTestCase {
    func testCRUDPersistsWhenDatabaseIsReopened() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let url = directory.appendingPathComponent("ledger.sqlite")

        var firstDatabase: AppDatabase? = try AppDatabase(url: url)
        var firstRepository: LedgerRepository? = firstDatabase.map { LedgerRepository(database: $0) }
        let repository = try XCTUnwrap(firstRepository)
        let account = try repository.createAccount(
            name: "银行卡",
            type: "bank",
            openingBalance: try XCTUnwrap(MoneyAmount("200"))
        )
        let book = try repository.createBook(name: "旅行", icon: "🧳", remark: "暑假")
        let category = try repository.createCategory(name: "咖啡", emoji: "☕️", kind: .expense)
        let tag = try repository.createTag(name: "出差")
        let date = Date(timeIntervalSince1970: 1_720_000_123)
        let saved = try repository.saveTransaction(
            TransactionDraft(
                bookID: book.id,
                kind: .expense,
                amountText: "28.60",
                categoryID: category.id,
                accountID: account.id,
                note: "机场咖啡",
                date: date,
                timePrecision: .exact,
                tagIDs: [tag.id],
                isReimbursable: true,
                imagePath: "/tmp/receipt.jpg"
            )
        )
        firstRepository = nil
        firstDatabase = nil

        let reopened = LedgerRepository(database: try AppDatabase(url: url))
        let restored = try reopened.transaction(id: saved.id)
        XCTAssertEqual(restored.amount.storageString, "28.6")
        XCTAssertEqual(restored.note, "机场咖啡")
        XCTAssertEqual(restored.tagIDs, [tag.id])
        XCTAssertEqual(restored.timePrecision, .exact)
        XCTAssertTrue(restored.isReimbursable)
        XCTAssertEqual(restored.imagePath, "/tmp/receipt.jpg")
        XCTAssertEqual(try reopened.books().first { $0.id == book.id }?.remark, "暑假")
    }

    func testTotalLedgerOnlyAggregatesIncludedBooksAndExcludesFlaggedRows() throws {
        let repository = try inMemoryRepository()
        let defaultBookID = try repository.defaultBookID()
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        let included = try repository.createBook(name: "家庭", includeInTotal: true)
        let separate = try repository.createBook(name: "生意", includeInTotal: false)

        _ = try saveExpense(repository, amount: "5", bookID: defaultBookID, accountID: accountID)
        _ = try saveExpense(repository, amount: "10", bookID: included.id, accountID: accountID)
        _ = try saveExpense(repository, amount: "100", bookID: separate.id, accountID: accountID)
        _ = try repository.saveTransaction(
            TransactionDraft(
                bookID: defaultBookID,
                amountText: "999",
                accountID: accountID,
                note: "不计收支",
                isExcluded: true
            )
        )

        XCTAssertEqual(try repository.transactions().count, 3)
        XCTAssertEqual(try repository.summary().expense.storageString, "15")
        XCTAssertEqual(
            try repository.summary(filter: TransactionFilter(bookID: separate.id)).expense.storageString,
            "100"
        )
    }

    func testSearchCoversNoteCategoryAccountAndExactAmountText() throws {
        let repository = try inMemoryRepository()
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        let categoryID = try XCTUnwrap(repository.categories().first { $0.key == "dining_lunch" }?.id)
        _ = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                amountText: "18.60",
                categoryID: categoryID,
                accountID: accountID,
                note: "瑞幸咖啡"
            )
        )

        for query in ["瑞幸", "午餐", "现金", "18.6"] {
            XCTAssertEqual(
                try repository.transactions(filter: TransactionFilter(searchText: query)).count,
                1,
                "Query should match: \(query)"
            )
        }
        XCTAssertTrue(try repository.transactions(filter: TransactionFilter(searchText: "不存在")).isEmpty)
    }

    func testTransferPreservesCombinedAccountBalance() throws {
        let repository = try inMemoryRepository()
        var cash = try XCTUnwrap(repository.accounts().first)
        cash.openingBalance = try XCTUnwrap(MoneyAmount("100"))
        try repository.updateAccount(cash)
        let bank = try repository.createAccount(
            name: "银行卡",
            type: "bank",
            openingBalance: try XCTUnwrap(MoneyAmount("20"))
        )

        let categoryID = try XCTUnwrap(repository.categories().first?.id)
        let transfer = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                kind: .transfer,
                amountText: "30",
                categoryID: categoryID,
                accountID: cash.id,
                toAccountID: bank.id,
                note: "存入银行卡",
                isReimbursable: true
            )
        )

        let cashBalance = try repository.accountBalance(id: cash.id)
        let bankBalance = try repository.accountBalance(id: bank.id)
        XCTAssertEqual(cashBalance.storageString, "70")
        XCTAssertEqual(bankBalance.storageString, "50")
        XCTAssertEqual((cashBalance + bankBalance).storageString, "120")
        XCTAssertNil(transfer.categoryID)
        XCTAssertFalse(transfer.isReimbursable)
        XCTAssertEqual(try repository.summary().expense, .zero)
        XCTAssertEqual(try repository.summary().income, .zero)
    }

    func testSoftDeleteKeepsTombstonesAndTransactionPrecision() throws {
        let repository = try inMemoryRepository()
        let account = try repository.createAccount(name: "临时账户")
        let book = try repository.createBook(name: "临时账本")
        let category = try repository.createCategory(name: "临时分类", kind: .expense)
        let tag = try repository.createTag(name: "临时标签")
        let transaction = try repository.saveTransaction(
            TransactionDraft(
                bookID: book.id,
                amountText: "1",
                categoryID: category.id,
                accountID: account.id,
                timePrecision: .entryClock,
                tagIDs: [tag.id]
            )
        )

        try repository.deleteTransaction(id: transaction.id)
        try repository.deleteTag(id: tag.id)
        try repository.deleteCategory(id: category.id)
        try repository.deleteAccount(id: account.id)
        try repository.deleteBook(id: book.id)

        XCTAssertTrue(try repository.transaction(id: transaction.id).isDeleted)
        XCTAssertEqual(try repository.transaction(id: transaction.id).timePrecision, .entryClock)
        XCTAssertTrue(try XCTUnwrap(repository.tags(includeDeleted: true).first { $0.id == tag.id }).isDeleted)
        XCTAssertTrue(try XCTUnwrap(repository.categories(includeDeleted: true).first { $0.id == category.id }).isDeleted)
        XCTAssertTrue(try XCTUnwrap(repository.accounts(includeDeleted: true).first { $0.id == account.id }).isDeleted)
        XCTAssertTrue(try XCTUnwrap(repository.books(includeDeleted: true).first { $0.id == book.id }).isDeleted)
    }

    func testAccountWithHistoryCannotBeDeleted() throws {
        let repository = try inMemoryRepository()
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        _ = try saveExpense(
            repository,
            amount: "3",
            bookID: try repository.defaultBookID(),
            accountID: accountID
        )

        XCTAssertTrue(try repository.accountIsInUse(id: accountID))
        XCTAssertThrowsError(try repository.deleteAccount(id: accountID)) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .accountInUse)
        }
        XCTAssertNotNil(try repository.accounts().first { $0.id == accountID })
    }

    func testInvalidAccountStatusCannotMakeAnAccountDisappearFromManagement() throws {
        let repository = try inMemoryRepository()
        var account = try XCTUnwrap(repository.accounts().first)
        account.status = "unexpected-status"

        XCTAssertThrowsError(try repository.updateAccount(account)) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .invalidAccountStatus)
        }
        XCTAssertTrue(try XCTUnwrap(repository.accounts().first).isAvailableForNewTransactions)
    }

    func testArchivedAccountKeepsHistoryAndBalanceButIsUnavailableForNewEntries() throws {
        let repository = try inMemoryRepository()
        var account = try XCTUnwrap(repository.accounts().first)
        account.openingBalance = try XCTUnwrap(MoneyAmount("100"))
        try repository.updateAccount(account)
        let transaction = try saveExpense(
            repository,
            amount: "12.5",
            bookID: try repository.defaultBookID(),
            accountID: account.id
        )

        account.status = LedgerAccountStatus.archived.rawValue
        try repository.updateAccount(account)

        let archived = try XCTUnwrap(repository.accounts().first { $0.id == account.id })
        XCTAssertTrue(archived.isArchived)
        XCTAssertFalse(archived.isAvailableForNewTransactions)
        XCTAssertEqual(try repository.accountBalance(id: account.id).storageString, "87.5")
        XCTAssertEqual(
            try repository.transactions(filter: TransactionFilter(searchText: account.name)).count,
            1
        )
        XCTAssertNoThrow(
            try repository.saveTransaction(
                TransactionDraft(
                    id: transaction.id,
                    bookID: transaction.bookID,
                    kind: transaction.kind,
                    amountText: transaction.amount.storageString,
                    categoryID: transaction.categoryID,
                    accountID: transaction.accountID,
                    note: "只修改历史备注",
                    date: transaction.date,
                    timePrecision: transaction.timePrecision,
                    tagIDs: transaction.tagIDs,
                    isReimbursable: transaction.isReimbursable,
                    imagePath: transaction.imagePath,
                    isExcluded: transaction.isExcluded
                )
            )
        )
        XCTAssertThrowsError(
            try repository.saveTransaction(
                TransactionDraft(
                    bookID: try repository.defaultBookID(),
                    amountText: "1",
                    accountID: account.id,
                    note: "不能记到归档账户"
                )
            )
        ) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .inactiveAccount)
        }
        XCTAssertThrowsError(try repository.deleteAccount(id: account.id)) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .accountInUse)
        }
    }

    func testEditingLegacyTransactionCanPreserveUnknownTimePrecision() throws {
        let repository = try inMemoryRepository()
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        let original = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                amountText: "9.9",
                accountID: accountID,
                note: "旧账单",
                date: Date(timeIntervalSince1970: 1_720_000_000),
                timePrecision: .legacyUnknown
            )
        )

        _ = try repository.saveTransaction(
            TransactionDraft(
                id: original.id,
                bookID: original.bookID,
                kind: original.kind,
                amountText: original.amount.storageString,
                categoryID: original.categoryID,
                accountID: original.accountID,
                note: "只改备注",
                date: original.date,
                timePrecision: original.timePrecision,
                tagIDs: original.tagIDs,
                isReimbursable: original.isReimbursable,
                imagePath: original.imagePath,
                isExcluded: original.isExcluded
            )
        )

        XCTAssertEqual(try repository.transaction(id: original.id).timePrecision, .legacyUnknown)
    }

    func testReceiptReferenceTrackingProtectsSharedFiles() throws {
        let repository = try inMemoryRepository()
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        let bookID = try repository.defaultBookID()
        let sharedPath = "/managed/receipts/shared.jpg"
        let first = try repository.saveTransaction(
            TransactionDraft(
                bookID: bookID,
                amountText: "1",
                accountID: accountID,
                imagePath: sharedPath
            )
        )
        let second = try repository.saveTransaction(
            TransactionDraft(
                bookID: bookID,
                amountText: "2",
                accountID: accountID,
                imagePath: sharedPath
            )
        )

        XCTAssertTrue(try repository.receiptIsReferenced(sharedPath))
        try repository.deleteTransaction(id: first.id)
        XCTAssertTrue(try repository.receiptIsReferenced(sharedPath))
        try repository.deleteTransaction(id: second.id)
        XCTAssertFalse(try repository.receiptIsReferenced(sharedPath))
    }

    func testCategoryHierarchyIsLimitedToTwoLevelsAndOneKind() throws {
        let repository = try inMemoryRepository()
        let expenseRoot = try repository.createCategory(name: "支出根", kind: .expense)
        let expenseChild = try repository.createCategory(
            name: "支出子类",
            kind: .expense,
            parentID: expenseRoot.id
        )

        XCTAssertThrowsError(
            try repository.createCategory(name: "跨类型", kind: .income, parentID: expenseRoot.id)
        ) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .invalidCategoryParent)
        }
        XCTAssertThrowsError(
            try repository.createCategory(name: "第三级", kind: .expense, parentID: expenseChild.id)
        ) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .invalidCategoryParent)
        }

        var hiddenRoot = expenseRoot
        hiddenRoot.isHidden = true
        try repository.updateCategory(hiddenRoot)
        var hiddenChild = expenseChild
        hiddenChild.isHidden = true
        XCTAssertNoThrow(try repository.updateCategory(hiddenChild))
        XCTAssertThrowsError(
            try repository.createCategory(name: "隐藏根下的新分类", kind: .expense, parentID: expenseRoot.id)
        ) { error in
            XCTAssertEqual(error as? LedgerRepositoryError, .invalidCategoryParent)
        }
    }

    func testDefaultBookAlwaysRemainsInTotalLedger() throws {
        let repository = try inMemoryRepository()
        let defaultID = try repository.defaultBookID()
        var defaultBook = try XCTUnwrap(repository.books().first { $0.id == defaultID })
        defaultBook.includeInTotal = false

        try repository.updateBook(defaultBook)

        XCTAssertTrue(try XCTUnwrap(repository.books().first { $0.id == defaultID }).includeInTotal)
    }

    func testBasicSettingCanBeCreatedUpdatedAndRemoved() throws {
        let repository = try inMemoryRepository()
        XCTAssertNil(try repository.setting(for: "sample"))
        try repository.setSetting("first", for: "sample")
        XCTAssertEqual(try repository.setting(for: "sample"), "first")
        try repository.setSetting("second", for: "sample")
        XCTAssertEqual(try repository.setting(for: "sample"), "second")
        try repository.setSetting(nil, for: "sample")
        XCTAssertNil(try repository.setting(for: "sample"))
    }

    func testForeignKeysRemainEnabledForEveryConnection() throws {
        let repository = try inMemoryRepository()
        XCTAssertThrowsError(
            try repository.saveTransaction(
                TransactionDraft(
                    bookID: try repository.defaultBookID(),
                    amountText: "1",
                    accountID: 999_999
                )
            )
        )
        XCTAssertTrue(try repository.transactions().isEmpty)
    }

    private func inMemoryRepository() throws -> LedgerRepository {
        LedgerRepository(database: try AppDatabase(inMemory: true))
    }

    private func saveExpense(
        _ repository: LedgerRepository,
        amount: String,
        bookID: Int64,
        accountID: Int64
    ) throws -> LedgerTransaction {
        try repository.saveTransaction(
            TransactionDraft(
                bookID: bookID,
                amountText: amount,
                accountID: accountID,
                date: Date(timeIntervalSince1970: 1_720_000_000)
            )
        )
    }

    private func temporaryDirectory() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("FeiMiaoDataTests-\(UUID().uuidString)", isDirectory: true)
    }
}
