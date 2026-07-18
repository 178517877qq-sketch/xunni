import CryptoKit
import Foundation
import GRDB
import ZIPFoundation
import XCTest
@testable import FeiMiaoData
@testable import FeiMiaoDomain

final class AndroidBackupImporterTests: XCTestCase {
    func testRawAndroidDatabaseMapsCoreTablesAndLedgerSemantics() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("qingji.db")
        try makeAndroidDatabase(at: sourceURL)

        let destination = try AppDatabase(inMemory: true)
        let result = try AndroidBackupImporter(database: destination).importBackup(
            from: sourceURL,
            receiptsDirectory: directory.appendingPathComponent("receipts")
        )
        let repository = LedgerRepository(database: destination)

        XCTAssertEqual(result.databaseVersion, 40)
        XCTAssertEqual(result.bookCount, 2)
        XCTAssertEqual(result.accountCount, 2)
        XCTAssertEqual(result.categoryCount, 2)
        XCTAssertEqual(result.tagCount, 1)
        XCTAssertEqual(result.transactionCount, 4)
        XCTAssertEqual(result.receiptCount, 0)
        XCTAssertEqual(try repository.transactions().count, 3, "Attached refund rows stay hidden")
        XCTAssertEqual(try repository.summary().expense.storageString, "60")
        XCTAssertEqual(try repository.netAmount(transactionID: 3).storageString, "40")
        XCTAssertEqual(
            try repository.transactions(filter: TransactionFilter(searchText: "40")).map(\.id),
            [3]
        )
        XCTAssertEqual(try repository.accountBalance(id: 1).storageString, "10")
        XCTAssertEqual(try repository.accountBalance(id: 2).storageString, "30")
        XCTAssertEqual(try repository.transaction(id: 1).timePrecision, .exact)
        XCTAssertEqual(try repository.transaction(id: 1).tagIDs, [1])
        XCTAssertEqual(try repository.transaction(id: 1).imagePath, "")
        XCTAssertEqual(try repository.categories().first { $0.id == 2 }?.emoji, "🍱")
    }

    func testZipBackupVerifiesManifestAndRestoresReceiptPath() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("source.db")
        try makeAndroidDatabase(at: sourceURL)
        let receipt = Data("receipt-bytes".utf8)
        let zipURL = try makeBackupZip(
            in: directory,
            databaseURL: sourceURL,
            receiptData: receipt
        )
        let receiptRoot = directory.appendingPathComponent("ios-receipts")

        let destination = try AppDatabase(inMemory: true)
        let result = try AndroidBackupImporter(database: destination).importBackup(
            from: zipURL,
            receiptsDirectory: receiptRoot
        )
        let imported = try LedgerRepository(database: destination).transaction(id: 1)

        XCTAssertEqual(result.receiptCount, 1)
        XCTAssertFalse(imported.imagePath.isEmpty)
        XCTAssertTrue(FileManager.default.fileExists(atPath: imported.imagePath))
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: imported.imagePath)), receipt)
    }

    func testChecksumFailureDoesNotReplaceExistingLedger() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("source.db")
        try makeAndroidDatabase(at: sourceURL)
        let zipURL = try makeBackupZip(
            in: directory,
            databaseURL: sourceURL,
            receiptData: Data("receipt".utf8),
            corruptReceiptHash: true
        )

        let destination = try AppDatabase(inMemory: true)
        let repository = LedgerRepository(database: destination)
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        let existing = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                amountText: "9",
                accountID: accountID,
                note: "保留我"
            )
        )

        XCTAssertThrowsError(
            try AndroidBackupImporter(database: destination).importBackup(from: zipURL)
        ) { error in
            XCTAssertEqual(
                error as? AndroidBackupImportError,
                .checksumMismatch("receipts/receipt.jpg")
            )
        }
        XCTAssertEqual(try repository.transaction(id: existing.id).note, "保留我")
    }

    func testAssetMediaIsStreamVerifiedWithoutEnteringTheBatchOneToFiveSchema() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("source.db")
        try makeAndroidDatabase(at: sourceURL)
        let zipURL = try makeBackupZip(
            in: directory,
            databaseURL: sourceURL,
            receiptData: Data("receipt".utf8),
            assetMediaData: Data(repeating: 0xA5, count: 256 * 1_024)
        )

        let destination = try AppDatabase(inMemory: true)
        let result = try AndroidBackupImporter(database: destination).importBackup(
            from: zipURL,
            receiptsDirectory: directory.appendingPathComponent("receipts")
        )

        XCTAssertEqual(result.transactionCount, 4)
        XCTAssertEqual(result.receiptCount, 1)
        XCTAssertEqual(try LedgerRepository(database: destination).transactions().count, 3)
    }

    func testFutureDatabaseVersionIsRejectedBeforeReplacement() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("future.db")
        try makeAndroidDatabase(at: sourceURL, version: 41)

        let destination = try AppDatabase(inMemory: true)
        XCTAssertThrowsError(
            try AndroidBackupImporter(database: destination).importBackup(from: sourceURL)
        ) { error in
            XCTAssertEqual(error as? AndroidBackupImportError, .unsupportedDatabaseVersion(41))
        }
    }

    func testSuccessfulImportKeepsAConsistentSafetyBackupOfIOSData() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sourceURL = directory.appendingPathComponent("android.db")
        try makeAndroidDatabase(at: sourceURL)
        let destinationURL = directory.appendingPathComponent("ios/feimiao.sqlite")
        let destination = try AppDatabase(url: destinationURL)
        let repository = LedgerRepository(database: destination)
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        _ = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                amountText: "6",
                accountID: accountID,
                note: "导入前的 iOS 账单"
            )
        )

        let result = try AndroidBackupImporter(database: destination).importBackup(from: sourceURL)
        let backupPath = try XCTUnwrap(result.safetyBackupPath)
        XCTAssertTrue(FileManager.default.fileExists(atPath: backupPath))
        let backupRepository = LedgerRepository(
            database: try AppDatabase(url: URL(fileURLWithPath: backupPath))
        )
        XCTAssertEqual(try backupRepository.transactions().map(\.note), ["导入前的 iOS 账单"])
        XCTAssertEqual(try repository.transaction(id: 1).note, "午餐")
    }

    func testMalformedDatabaseCannotEraseCurrentData() throws {
        let directory = temporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let malformedURL = directory.appendingPathComponent("malformed.db")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let malformed = try DatabaseQueue(path: malformedURL.path)
        try malformed.write { db in
            try db.create(table: "books") { table in
                table.autoIncrementedPrimaryKey("id")
                table.column("name", .text).notNull()
            }
            try db.execute(sql: "PRAGMA user_version = 40")
        }

        let destination = try AppDatabase(inMemory: true)
        let repository = LedgerRepository(database: destination)
        let accountID = try XCTUnwrap(repository.accounts().first?.id)
        _ = try repository.saveTransaction(
            TransactionDraft(
                bookID: try repository.defaultBookID(),
                amountText: "7",
                accountID: accountID,
                note: "原有数据"
            )
        )

        XCTAssertThrowsError(
            try AndroidBackupImporter(database: destination).importBackup(from: malformedURL)
        )
        XCTAssertEqual(try repository.transactions().map(\.note), ["原有数据"])
    }

    private func makeAndroidDatabase(at url: URL, version: Int = 40) throws {
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        var configuration = Configuration()
        configuration.prepareDatabase { database in
            try database.execute(sql: "PRAGMA journal_mode = DELETE")
        }
        let queue = try DatabaseQueue(path: url.path, configuration: configuration)
        try queue.write { db in
            try db.execute(sql: """
                CREATE TABLE accounts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  uuid TEXT NOT NULL DEFAULT '',
                  name TEXT NOT NULL,
                  currency_code TEXT NOT NULL DEFAULT 'CNY',
                  type TEXT NOT NULL DEFAULT 'cash',
                  opening_balance TEXT NOT NULL DEFAULT '0',
                  include_in_net_worth INTEGER NOT NULL DEFAULT 1,
                  institution TEXT NOT NULL DEFAULT '',
                  sort_order INTEGER NOT NULL DEFAULT 0,
                  is_deleted INTEGER NOT NULL DEFAULT 0,
                  deleted_at_ms INTEGER,
                  created_ms INTEGER NOT NULL DEFAULT 0,
                  updated_ms INTEGER NOT NULL DEFAULT 0,
                  status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE TABLE categories (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT NOT NULL UNIQUE,
                  name_zh TEXT NOT NULL,
                  name_en TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  parent_id INTEGER,
                  hidden INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE books (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  icon TEXT NOT NULL DEFAULT '📒',
                  cover TEXT NOT NULL DEFAULT '',
                  remark TEXT NOT NULL DEFAULT '',
                  sort_order INTEGER NOT NULL DEFAULT 0,
                  created_ms INTEGER NOT NULL DEFAULT 0,
                  starred INTEGER NOT NULL DEFAULT 0,
                  include_in_total INTEGER NOT NULL DEFAULT 1,
                  uuid TEXT NOT NULL DEFAULT '',
                  updated_ms INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE tags (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  color INTEGER NOT NULL DEFAULT 4286351771
                );
                CREATE TABLE transactions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  book_id INTEGER,
                  kind TEXT NOT NULL,
                  amount TEXT NOT NULL,
                  currency_code TEXT NOT NULL DEFAULT 'CNY',
                  category_id INTEGER,
                  account_id INTEGER,
                  to_account_id INTEGER,
                  note TEXT NOT NULL DEFAULT '',
                  date_ms INTEGER NOT NULL,
                  time_precision TEXT NOT NULL DEFAULT 'legacy_unknown',
                  tags TEXT NOT NULL DEFAULT '',
                  reimbursable INTEGER NOT NULL DEFAULT 0,
                  image_path TEXT NOT NULL DEFAULT '',
                  excluded INTEGER NOT NULL DEFAULT 0,
                  uuid TEXT NOT NULL DEFAULT '',
                  updated_ms INTEGER NOT NULL DEFAULT 0,
                  refund_of INTEGER,
                  created_ms INTEGER NOT NULL DEFAULT 0
                );
                PRAGMA user_version = \(version);
                """)

            try db.execute(
                sql: "INSERT INTO books (id, name, icon, sort_order, created_ms, starred, include_in_total, uuid, updated_ms) VALUES (1, '总账本', '📒', 0, 1, 1, 1, 'book-1', 1), (2, '旅行', '🧳', 1, 2, 0, 1, 'book-2', 2)"
            )
            try db.execute(
                sql: """
                    INSERT INTO accounts
                    (id, uuid, name, type, opening_balance, sort_order, created_ms, updated_ms)
                    VALUES (1, 'account-1', '现金', 'cash', '100', 0, 1, 1),
                           (2, 'account-2', '银行卡', 'bank', '0', 1, 1, 1)
                    """
            )
            try db.execute(
                sql: "INSERT INTO categories (id, key, name_zh, name_en, kind, parent_id) VALUES (1, 'dining', '食品餐饮', 'Food', 'expense', NULL), (2, 'dining_lunch', '午餐', 'Lunch', 'expense', 1)"
            )
            try db.execute(sql: "INSERT INTO tags (id, name, color) VALUES (1, '旅行', 4286351771)")
            try db.execute(
                sql: """
                    INSERT INTO transactions
                    (id, book_id, kind, amount, category_id, account_id, to_account_id,
                     note, date_ms, time_precision, tags, image_path, uuid, updated_ms, refund_of, created_ms)
                    VALUES
                    (1, 1, 'expense', '20', 2, 1, NULL, '午餐', 1720000000000, 'exact', '1',
                     '/data/user/0/com.feimiao/files/receipts/receipt.jpg', 'tx-1', 10, NULL, 10),
                    (2, 1, 'transfer', '30', NULL, 1, 2, '存款', 1720000100000, 'entry_clock', '', '', 'tx-2', 11, NULL, 11),
                    (3, 2, 'expense', '50', 1, 1, NULL, '酒店', 1720000200000, 'date_only', '', '', 'tx-3', 12, NULL, 12),
                    (4, 2, 'expense', '-10', 1, 1, NULL, '退款', 1720000200000, 'date_only', '', '', 'tx-4', 13, 3, 13)
                    """
            )
        }
    }

    private func makeBackupZip(
        in directory: URL,
        databaseURL: URL,
        receiptData: Data,
        corruptReceiptHash: Bool = false,
        assetMediaData: Data? = nil
    ) throws -> URL {
        let root = directory.appendingPathComponent("payload-\(UUID().uuidString)", isDirectory: true)
        let databaseDestination = root.appendingPathComponent("database/qingji.db")
        let receiptDestination = root.appendingPathComponent("receipts/receipt.jpg")
        try FileManager.default.createDirectory(
            at: databaseDestination.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: receiptDestination.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try FileManager.default.copyItem(at: databaseURL, to: databaseDestination)
        try receiptData.write(to: receiptDestination)
        let databaseData = try Data(contentsOf: databaseDestination)
        var checksums = [
            "database/qingji.db": sha256(databaseData),
            "receipts/receipt.jpg": corruptReceiptHash ? String(repeating: "0", count: 64) : sha256(receiptData),
        ]
        if let assetMediaData {
            let assetDestination = root.appendingPathComponent("asset_media/future-module.bin")
            try FileManager.default.createDirectory(
                at: assetDestination.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try assetMediaData.write(to: assetDestination)
            checksums["asset_media/future-module.bin"] = sha256(assetMediaData)
        }
        let manifest: [String: Any] = [
            "format": "feimiao-backup",
            "version": 2,
            "createdAt": "2026-07-18T12:00:00Z",
            "databaseVersion": 40,
            "contains": ["database": true, "receipts": true, "assetMedia": assetMediaData != nil],
            "excludes": ["deepseek_api_key", "custom_ai_api_key"],
            "checksums": checksums,
        ]
        try JSONSerialization.data(withJSONObject: manifest, options: [.sortedKeys])
            .write(to: root.appendingPathComponent("manifest.json"))

        let zipURL = directory.appendingPathComponent("backup-\(UUID().uuidString).zip")
        let archive = try Archive(url: zipURL, accessMode: .create)
        try archive.addEntry(with: "database/qingji.db", relativeTo: root, compressionMethod: .deflate)
        try archive.addEntry(with: "receipts/receipt.jpg", relativeTo: root, compressionMethod: .deflate)
        if assetMediaData != nil {
            try archive.addEntry(
                with: "asset_media/future-module.bin",
                relativeTo: root,
                compressionMethod: .deflate
            )
        }
        try archive.addEntry(with: "manifest.json", relativeTo: root, compressionMethod: .deflate)
        return zipURL
    }

    private func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private func temporaryDirectory() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("AndroidBackupImporterTests-\(UUID().uuidString)", isDirectory: true)
    }
}
