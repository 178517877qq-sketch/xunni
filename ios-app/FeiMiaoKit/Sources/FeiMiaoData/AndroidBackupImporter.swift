import CryptoKit
import Foundation
import GRDB
import ZIPFoundation
import FeiMiaoDomain

public struct AndroidBackupImportResult: Equatable, Sendable {
    public let databaseVersion: Int
    public let bookCount: Int
    public let accountCount: Int
    public let categoryCount: Int
    public let tagCount: Int
    public let transactionCount: Int
    public let receiptCount: Int
    public let safetyBackupPath: String?

    public init(
        databaseVersion: Int,
        bookCount: Int,
        accountCount: Int,
        categoryCount: Int,
        tagCount: Int,
        transactionCount: Int,
        receiptCount: Int,
        safetyBackupPath: String? = nil
    ) {
        self.databaseVersion = databaseVersion
        self.bookCount = bookCount
        self.accountCount = accountCount
        self.categoryCount = categoryCount
        self.tagCount = tagCount
        self.transactionCount = transactionCount
        self.receiptCount = receiptCount
        self.safetyBackupPath = safetyBackupPath
    }
}

public enum AndroidBackupImportError: LocalizedError, Equatable {
    case unsupportedFile
    case invalidArchive
    case unsafeArchivePath
    case invalidManifest
    case unsupportedBackupVersion(Int)
    case unsupportedDatabaseVersion(Int)
    case missingDatabase
    case checksumMismatch(String)
    case archiveTooLarge
    case invalidDatabase(String)

    public var errorDescription: String? {
        switch self {
        case .unsupportedFile:
            "请选择肥喵导出的 .zip 完整备份，或旧版 .db/.bak 数据库。"
        case .invalidArchive:
            "备份压缩包已损坏或无法读取。"
        case .unsafeArchivePath:
            "备份中包含不安全的文件路径。"
        case .invalidManifest:
            "备份清单无效。"
        case let .unsupportedBackupVersion(version):
            "暂不支持版本 \(version) 的备份包。"
        case let .unsupportedDatabaseVersion(version):
            "暂不支持数据库版本 \(version)。"
        case .missingDatabase:
            "备份中缺少 database/qingji.db。"
        case let .checksumMismatch(path):
            "备份文件校验失败：\(path)"
        case .archiveTooLarge:
            "备份包过大，已停止导入以保护设备存储。"
        case let .invalidDatabase(reason):
            "账本数据库无效：\(reason)"
        }
    }
}

/// Imports the Android v1-v40 core ledger into FeiMiao's own schema.
/// The Android file is always opened read-only and is never used as the live iOS database.
public final class AndroidBackupImporter: @unchecked Sendable {
    private static let supportedArchiveVersions = 1...2
    private static let maximumArchiveBytes: UInt64 = 536_870_912
    private static let maximumDatabaseBytes: UInt64 = 268_435_456
    private static let maximumAssetBytes: UInt64 = 67_108_864
    private static let maximumManifestBytes: UInt64 = 1_048_576
    private static let requiredTables: Set<String> = [
        "accounts", "books", "categories", "tags", "transactions",
    ]

    private let database: AppDatabase
    private let fileManager: FileManager

    public init(database: AppDatabase, fileManager: FileManager = .default) {
        self.database = database
        self.fileManager = fileManager
    }

    @discardableResult
    public func importBackup(
        from sourceURL: URL,
        receiptsDirectory: URL? = nil
    ) throws -> AndroidBackupImportResult {
        let workDirectory = fileManager.temporaryDirectory
            .appendingPathComponent("feimiao-android-import-\(UUID().uuidString)", isDirectory: true)
        try fileManager.createDirectory(at: workDirectory, withIntermediateDirectories: true)
        defer { try? fileManager.removeItem(at: workDirectory) }

        let payload = try loadPayload(from: sourceURL, into: workDirectory)

        let sourceDatabaseURL = payload.databaseURL ?? sourceURL

        var configuration = Configuration()
        configuration.readonly = true
        let sourceQueue: DatabaseQueue
        do {
            sourceQueue = try DatabaseQueue(path: sourceDatabaseURL.path, configuration: configuration)
        } catch {
            throw AndroidBackupImportError.invalidDatabase(error.localizedDescription)
        }

        var snapshot = try sourceQueue.read { source in
            try Self.readSnapshot(from: source)
        }
        if let manifestVersion = payload.databaseVersion, manifestVersion != snapshot.databaseVersion {
            throw AndroidBackupImportError.invalidManifest
        }
        guard snapshot.databaseVersion >= 1,
              snapshot.databaseVersion <= AppDatabase.androidSchemaVersion else {
            throw AndroidBackupImportError.unsupportedDatabaseVersion(snapshot.databaseVersion)
        }

        let receiptRoot = receiptsDirectory
            ?? database.url?.deletingLastPathComponent().appendingPathComponent("receipts", isDirectory: true)
        let stagedReceipts = try stageReceipts(payload.receipts, at: receiptRoot)
        let safetyBackupURL: URL?
        do {
            safetyBackupURL = try createSafetyBackup()
            for index in snapshot.transactions.indices {
                snapshot.transactions[index].imagePath = stagedReceipts.path(
                    forAndroidPath: snapshot.transactions[index].imagePath
                )
            }
            try replaceCoreData(with: snapshot)
        } catch {
            stagedReceipts.removeFromDisk(fileManager: fileManager)
            throw error
        }

        return AndroidBackupImportResult(
            databaseVersion: snapshot.databaseVersion,
            bookCount: snapshot.books.count,
            accountCount: snapshot.accounts.count,
            categoryCount: snapshot.categories.count,
            tagCount: snapshot.tags.count,
            transactionCount: snapshot.transactions.count,
            receiptCount: stagedReceipts.count,
            safetyBackupPath: safetyBackupURL?.path
        )
    }

    private func createSafetyBackup() throws -> URL? {
        guard let liveURL = database.url else { return nil }
        let directory = liveURL.deletingLastPathComponent().appendingPathComponent("backups", isDirectory: true)
        try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        let milliseconds = Int64(Date().timeIntervalSince1970 * 1_000)
        let suffix = UUID().uuidString.lowercased()
        let destination = directory.appendingPathComponent(
            "feimiao.pre-android-import.\(milliseconds).\(suffix).bak"
        )
        try database.queue.writeWithoutTransaction { live in
            try live.execute(sql: "VACUUM INTO ?", arguments: [destination.path])
        }

        let backups = try fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        )
        .filter { $0.lastPathComponent.hasPrefix("feimiao.pre-android-import.") }
        .sorted { lhs, rhs in
            let left = try? lhs.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate
            let right = try? rhs.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate
            return (left ?? .distantPast) > (right ?? .distantPast)
        }
        for obsolete in backups.dropFirst(3) {
            try? fileManager.removeItem(at: obsolete)
        }
        return destination
    }

    private func loadPayload(from sourceURL: URL, into workDirectory: URL) throws -> BackupPayload {
        let ext = sourceURL.pathExtension.lowercased()
        if ext == "db" || ext == "bak" || ext == "sqlite" {
            return BackupPayload(databaseURL: nil, databaseVersion: nil, receipts: [:])
        }
        guard ext == "zip" else { throw AndroidBackupImportError.unsupportedFile }

        let archive: Archive
        do {
            archive = try Archive(url: sourceURL, accessMode: .read)
        } catch {
            throw AndroidBackupImportError.invalidArchive
        }
        let entries = Array(archive)
        guard entries.count <= 10_000 else { throw AndroidBackupImportError.archiveTooLarge }

        var entryByPath: [String: Entry] = [:]
        var totalBytes: UInt64 = 0
        for entry in entries where entry.type == .file {
            guard Self.isSafeArchivePath(entry.path), entryByPath[entry.path] == nil else {
                throw AndroidBackupImportError.unsafeArchivePath
            }
            guard entry.uncompressedSize <= Self.maximumArchiveBytes - totalBytes else {
                throw AndroidBackupImportError.archiveTooLarge
            }
            totalBytes += entry.uncompressedSize
            entryByPath[entry.path] = entry
        }

        guard let manifestEntry = entryByPath["manifest.json"] else {
            throw AndroidBackupImportError.invalidManifest
        }
        guard manifestEntry.uncompressedSize <= Self.maximumManifestBytes else {
            throw AndroidBackupImportError.archiveTooLarge
        }
        let manifestData = try Self.data(for: manifestEntry, in: archive)
        guard
            let json = try? JSONSerialization.jsonObject(with: manifestData) as? [String: Any],
            json["format"] as? String == "feimiao-backup",
            let archiveVersion = json["version"] as? Int,
            let databaseVersion = json["databaseVersion"] as? Int,
            let rawChecksums = json["checksums"] as? [String: Any]
        else {
            throw AndroidBackupImportError.invalidManifest
        }
        guard Self.supportedArchiveVersions.contains(archiveVersion) else {
            throw AndroidBackupImportError.unsupportedBackupVersion(archiveVersion)
        }

        let checksums = rawChecksums.reduce(into: [String: String]()) { result, item in
            result[item.key] = item.value as? String
        }
        guard checksums.count == rawChecksums.count,
              checksums["database/qingji.db"] != nil else {
            throw AndroidBackupImportError.missingDatabase
        }
        let payloadPaths = Set(entryByPath.keys).subtracting(["manifest.json"])
        guard payloadPaths == Set(checksums.keys) else {
            throw AndroidBackupImportError.invalidManifest
        }

        var databaseURL: URL?
        var receipts: [String: URL] = [:]
        for (path, expectedHash) in checksums {
            guard Self.isSafePayloadPath(path), let entry = entryByPath[path] else {
                throw AndroidBackupImportError.unsafeArchivePath
            }
            let itemLimit = path == "database/qingji.db"
                ? Self.maximumDatabaseBytes
                : Self.maximumAssetBytes
            guard entry.uncompressedSize <= itemLimit else {
                throw AndroidBackupImportError.archiveTooLarge
            }
            let destination: URL?
            if path == "database/qingji.db" || path.hasPrefix("receipts/") {
                destination = workDirectory.appendingPathComponent("payload", isDirectory: true)
                    .appendingPathComponent(path)
            } else {
                // Asset-module media is outside batches 1-5. It is still streamed
                // through CRC/SHA verification, but is not retained in memory.
                destination = nil
            }
            let actualHash = try Self.extractAndHash(
                entry,
                from: archive,
                to: destination,
                maximumBytes: itemLimit,
                fileManager: fileManager
            )
            guard actualHash == expectedHash.lowercased() else {
                throw AndroidBackupImportError.checksumMismatch(path)
            }
            if path == "database/qingji.db" {
                databaseURL = destination
            } else if path.hasPrefix("receipts/"), let destination {
                receipts[String(path.dropFirst("receipts/".count))] = destination
            }
        }
        guard let databaseURL else { throw AndroidBackupImportError.missingDatabase }
        return BackupPayload(
            databaseURL: databaseURL,
            databaseVersion: databaseVersion,
            receipts: receipts
        )
    }

    private func stageReceipts(
        _ receipts: [String: URL],
        at root: URL?
    ) throws -> StagedReceipts {
        guard !receipts.isEmpty, let root else { return .empty }
        let directory = root.appendingPathComponent(
            "android-import-\(UUID().uuidString.lowercased())",
            isDirectory: true
        )
        var relativePaths: [String: String] = [:]
        var names: [String: [String]] = [:]
        do {
            for (relativePath, source) in receipts {
                guard Self.isSafeRelativePath(relativePath) else {
                    throw AndroidBackupImportError.unsafeArchivePath
                }
                let destination = directory.appendingPathComponent(relativePath)
                try fileManager.createDirectory(
                    at: destination.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try fileManager.copyItem(at: source, to: destination)
                let normalized = relativePath.replacingOccurrences(of: "\\", with: "/")
                relativePaths[normalized] = destination.path
                names[destination.lastPathComponent, default: []].append(destination.path)
            }
        } catch {
            try? fileManager.removeItem(at: directory)
            throw error
        }
        let uniqueNames = names.compactMapValues { $0.count == 1 ? $0[0] : nil }
        return StagedReceipts(
            directory: directory,
            pathsByRelativePath: relativePaths,
            pathsByUniqueName: uniqueNames
        )
    }

    private func replaceCoreData(with snapshot: AndroidSnapshot) throws {
        let bookIDs = Set(snapshot.books.map(\.id))
        let accountIDs = Set(snapshot.accounts.map(\.id))
        let categoryIDs = Set(snapshot.categories.map(\.id))
        let transactionIDs = Set(snapshot.transactions.map(\.id))
        guard !bookIDs.isEmpty else {
            throw AndroidBackupImportError.invalidDatabase("没有账本")
        }

        try database.queue.write { target in
            try target.execute(sql: "DELETE FROM transactions")
            try target.execute(sql: "DELETE FROM categories WHERE parent_id IS NOT NULL")
            try target.execute(sql: "DELETE FROM categories")
            try target.execute(sql: "DELETE FROM tags")
            try target.execute(sql: "DELETE FROM accounts")
            try target.execute(sql: "DELETE FROM books")

            for book in snapshot.books {
                try target.execute(
                    sql: """
                        INSERT INTO books
                        (id, uuid, name, icon, cover, remark, sort_order, created_ms, starred,
                         include_in_total, updated_ms, is_deleted, deleted_at_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                    arguments: [
                        book.id, book.uuid, book.name, book.icon, book.cover, book.remark,
                        book.sortOrder, book.createdMS, book.starred ? 1 : 0,
                        book.includeInTotal ? 1 : 0, book.updatedMS,
                        book.isDeleted ? 1 : 0, book.deletedAtMS,
                    ]
                )
            }
            for account in snapshot.accounts {
                try target.execute(
                    sql: """
                        INSERT INTO accounts
                        (id, uuid, name, currency_code, type, opening_balance, include_in_net_worth,
                         institution, sort_order, status, created_ms, updated_ms, is_deleted, deleted_at_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                    arguments: [
                        account.id, account.uuid, account.name, account.currencyCode, account.type,
                        account.openingBalance, account.includeInNetWorth ? 1 : 0,
                        account.institution, account.sortOrder, account.status,
                        account.createdMS, account.updatedMS,
                        account.isDeleted ? 1 : 0, account.deletedAtMS,
                    ]
                )
            }
            for category in snapshot.categories {
                try target.execute(
                    sql: """
                        INSERT INTO categories
                        (id, uuid, key, name_zh, name_en, emoji, kind, parent_id, hidden,
                         sort_order, created_ms, updated_ms, is_deleted, deleted_at_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
                        """,
                    arguments: [
                        category.id, category.uuid, category.key, category.nameZh, category.nameEn,
                        category.emoji, category.kind, category.hidden ? 1 : 0,
                        category.sortOrder, category.createdMS, category.updatedMS,
                        category.isDeleted ? 1 : 0, category.deletedAtMS,
                    ]
                )
            }
            let rootCategoryIDs = Set(snapshot.categories.filter { $0.parentID == nil }.map(\.id))
            for category in snapshot.categories {
                guard let parentID = category.parentID,
                      parentID != category.id,
                      rootCategoryIDs.contains(parentID) else { continue }
                try target.execute(
                    sql: "UPDATE categories SET parent_id = ? WHERE id = ?",
                    arguments: [parentID, category.id]
                )
            }
            for tag in snapshot.tags {
                try target.execute(
                    sql: """
                        INSERT INTO tags
                        (id, uuid, name, color, sort_order, created_ms, updated_ms, is_deleted, deleted_at_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                    arguments: [
                        tag.id, tag.uuid, tag.name, tag.color, tag.sortOrder,
                        tag.createdMS, tag.updatedMS, tag.isDeleted ? 1 : 0, tag.deletedAtMS,
                    ]
                )
            }
            let fallbackBookID = snapshot.books
                .filter { !$0.isDeleted }
                .min { lhs, rhs in
                    lhs.sortOrder == rhs.sortOrder ? lhs.id < rhs.id : lhs.sortOrder < rhs.sortOrder
                }?.id ?? snapshot.books[0].id
            for transaction in snapshot.transactions {
                let bookID = transaction.bookID.flatMap { bookIDs.contains($0) ? $0 : nil } ?? fallbackBookID
                let categoryID = transaction.categoryID.flatMap { categoryIDs.contains($0) ? $0 : nil }
                let accountID = transaction.accountID.flatMap { accountIDs.contains($0) ? $0 : nil }
                let toAccountID = transaction.toAccountID.flatMap { accountIDs.contains($0) ? $0 : nil }
                try target.execute(
                    sql: """
                        INSERT INTO transactions
                        (id, uuid, book_id, kind, amount, currency_code, category_id, account_id,
                         to_account_id, note, date_ms, time_precision, tags, reimbursable,
                         image_path, excluded, refund_of, created_ms, updated_ms, is_deleted, deleted_at_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                        """,
                    arguments: [
                        transaction.id, transaction.uuid, bookID, transaction.kind,
                        transaction.amount, transaction.currencyCode, categoryID, accountID,
                        toAccountID, transaction.note, transaction.dateMS,
                        transaction.timePrecision, transaction.tags, transaction.reimbursable ? 1 : 0,
                        transaction.imagePath, transaction.excluded ? 1 : 0,
                        transaction.createdMS, transaction.updatedMS,
                        transaction.isDeleted ? 1 : 0, transaction.deletedAtMS,
                    ]
                )
            }
            for transaction in snapshot.transactions {
                guard let refundOf = transaction.refundOf,
                      refundOf != transaction.id,
                      transactionIDs.contains(refundOf) else { continue }
                try target.execute(
                    sql: "UPDATE transactions SET refund_of = ? WHERE id = ?",
                    arguments: [refundOf, transaction.id]
                )
            }
            try target.execute(
                sql: "INSERT INTO app_settings(key, value) VALUES ('ios_selected_book', 'total') ON CONFLICT(key) DO UPDATE SET value = 'total'"
            )
        }
    }

    private static func readSnapshot(from source: Database) throws -> AndroidSnapshot {
        let tables = Set(try String.fetchAll(
            source,
            sql: "SELECT name FROM sqlite_master WHERE type = 'table'"
        ))
        let missing = requiredTables.subtracting(tables)
        guard missing.isEmpty else {
            throw AndroidBackupImportError.invalidDatabase(
                "缺少核心表：\(missing.sorted().joined(separator: "、"))"
            )
        }
        try validateColumns(source, table: "books", required: ["id", "name"])
        try validateColumns(source, table: "accounts", required: ["id", "name"])
        try validateColumns(
            source,
            table: "categories",
            required: ["id", "key", "name_zh", "name_en", "kind"]
        )
        try validateColumns(source, table: "tags", required: ["id", "name"])
        try validateColumns(
            source,
            table: "transactions",
            required: ["id", "kind", "amount", "date_ms"]
        )
        let version = try Int.fetchOne(source, sql: "PRAGMA user_version") ?? 0

        let books = try Row.fetchAll(source, sql: "SELECT * FROM books").map { row in
            let id: Int64 = try required(row, "id")
            return AndroidBook(
                id: id,
                uuid: nonEmpty(value(row, "uuid") as String?) ?? "android-book-\(id)",
                name: nonEmpty(value(row, "name") as String?) ?? "账本 \(id)",
                icon: nonEmpty(value(row, "icon") as String?) ?? "📒",
                cover: value(row, "cover") ?? "",
                remark: value(row, "remark") ?? "",
                sortOrder: value(row, "sort_order") ?? Int(id),
                createdMS: value(row, "created_ms") ?? 0,
                starred: (value(row, "starred") as Int? ?? 0) == 1,
                includeInTotal: (value(row, "include_in_total") as Int? ?? 1) == 1,
                updatedMS: value(row, "updated_ms") ?? 0,
                isDeleted: (value(row, "is_deleted") as Int? ?? 0) == 1,
                deletedAtMS: value(row, "deleted_at_ms")
            )
        }
        let accounts = try Row.fetchAll(source, sql: "SELECT * FROM accounts").map { row in
            let id: Int64 = try required(row, "id")
            let openingBalance: String = value(row, "opening_balance") ?? "0"
            guard MoneyAmount(openingBalance) != nil else {
                throw AndroidBackupImportError.invalidDatabase("账户 \(id) 的期初余额不是十进制金额")
            }
            return AndroidAccount(
                id: id,
                uuid: nonEmpty(value(row, "uuid") as String?) ?? "android-account-\(id)",
                name: nonEmpty(value(row, "name") as String?) ?? "账户 \(id)",
                currencyCode: nonEmpty(value(row, "currency_code") as String?) ?? "CNY",
                type: nonEmpty(value(row, "type") as String?) ?? "cash",
                openingBalance: openingBalance,
                includeInNetWorth: (value(row, "include_in_net_worth") as Int? ?? 1) == 1,
                institution: value(row, "institution") ?? "",
                sortOrder: value(row, "sort_order") ?? Int(id),
                status: normalizedAccountStatus(value(row, "status") as String?),
                createdMS: value(row, "created_ms") ?? 0,
                updatedMS: value(row, "updated_ms") ?? 0,
                isDeleted: (value(row, "is_deleted") as Int? ?? 0) == 1,
                deletedAtMS: value(row, "deleted_at_ms")
            )
        }
        let categories = try Row.fetchAll(source, sql: "SELECT * FROM categories").map { row in
            let id: Int64 = try required(row, "id")
            let key: String = nonEmpty(value(row, "key") as String?) ?? "android-category-\(id)"
            return AndroidCategory(
                id: id,
                uuid: nonEmpty(value(row, "uuid") as String?) ?? "category-\(key)",
                key: key,
                nameZh: nonEmpty(value(row, "name_zh") as String?) ?? "分类 \(id)",
                nameEn: nonEmpty(value(row, "name_en") as String?) ?? key,
                emoji: nonEmpty(value(row, "emoji") as String?) ?? CategoryCatalog.emoji(for: key),
                kind: normalizedKind(value(row, "kind")),
                parentID: value(row, "parent_id"),
                hidden: (value(row, "hidden") as Int? ?? 0) == 1,
                sortOrder: value(row, "sort_order") ?? Int(id),
                createdMS: value(row, "created_ms") ?? 0,
                updatedMS: value(row, "updated_ms") ?? 0,
                isDeleted: (value(row, "is_deleted") as Int? ?? 0) == 1,
                deletedAtMS: value(row, "deleted_at_ms")
            )
        }
        let tags = try Row.fetchAll(source, sql: "SELECT * FROM tags").map { row in
            let id: Int64 = try required(row, "id")
            return AndroidTag(
                id: id,
                uuid: nonEmpty(value(row, "uuid") as String?) ?? "android-tag-\(id)",
                name: nonEmpty(value(row, "name") as String?) ?? "标签 \(id)",
                color: value(row, "color") ?? 4_286_351_771,
                sortOrder: value(row, "sort_order") ?? Int(id),
                createdMS: value(row, "created_ms") ?? 0,
                updatedMS: value(row, "updated_ms") ?? 0,
                isDeleted: (value(row, "is_deleted") as Int? ?? 0) == 1,
                deletedAtMS: value(row, "deleted_at_ms")
            )
        }
        let transactions = try Row.fetchAll(source, sql: "SELECT * FROM transactions").map { row in
            let id: Int64 = try required(row, "id")
            let amount: String = try required(row, "amount")
            guard MoneyAmount(amount) != nil else {
                throw AndroidBackupImportError.invalidDatabase("账单 \(id) 的金额不是十进制金额")
            }
            return AndroidTransaction(
                id: id,
                uuid: nonEmpty(value(row, "uuid") as String?) ?? "android-transaction-\(id)",
                bookID: value(row, "book_id"),
                kind: normalizedKind(value(row, "kind")),
                amount: amount,
                currencyCode: nonEmpty(value(row, "currency_code") as String?) ?? "CNY",
                categoryID: value(row, "category_id"),
                accountID: value(row, "account_id"),
                toAccountID: value(row, "to_account_id"),
                note: value(row, "note") ?? "",
                dateMS: try required(row, "date_ms"),
                timePrecision: normalizedTimePrecision(value(row, "time_precision")),
                tags: value(row, "tags") ?? "",
                reimbursable: (value(row, "reimbursable") as Int? ?? 0) == 1,
                imagePath: value(row, "image_path") ?? "",
                excluded: (value(row, "excluded") as Int? ?? 0) == 1,
                refundOf: value(row, "refund_of"),
                createdMS: value(row, "created_ms") ?? (value(row, "date_ms") as Int64? ?? 0),
                updatedMS: value(row, "updated_ms") ?? 0,
                isDeleted: (value(row, "is_deleted") as Int? ?? 0) == 1,
                deletedAtMS: value(row, "deleted_at_ms")
            )
        }
        return AndroidSnapshot(
            databaseVersion: version,
            books: books,
            accounts: accounts,
            categories: categories,
            tags: tags,
            transactions: transactions
        )
    }

    private static func value<T: DatabaseValueConvertible>(_ row: Row, _ column: String) -> T? {
        guard row.columnNames.contains(column) else { return nil }
        return row[column]
    }

    private static func validateColumns(
        _ database: Database,
        table: String,
        required: Set<String>
    ) throws {
        let columns = Set(try Row.fetchAll(database, sql: "PRAGMA table_info(\(table))").compactMap {
            value($0, "name") as String?
        })
        let missing = required.subtracting(columns)
        guard missing.isEmpty else {
            throw AndroidBackupImportError.invalidDatabase(
                "\(table) 缺少列：\(missing.sorted().joined(separator: "、"))"
            )
        }
    }

    private static func required<T: DatabaseValueConvertible>(_ row: Row, _ column: String) throws -> T {
        guard let result: T = value(row, column) else {
            throw AndroidBackupImportError.invalidDatabase("\(column) 包含空值")
        }
        return result
    }

    private static func nonEmpty(_ value: String?) -> String? {
        guard let clean = value?.trimmingCharacters(in: .whitespacesAndNewlines), !clean.isEmpty else {
            return nil
        }
        return clean
    }

    private static func normalizedKind(_ raw: String?) -> String {
        guard let raw, TransactionKind(rawValue: raw) != nil else { return TransactionKind.expense.rawValue }
        return raw
    }

    private static func normalizedAccountStatus(_ raw: String?) -> String {
        guard let raw = nonEmpty(raw), LedgerAccountStatus(rawValue: raw) != nil else {
            return LedgerAccountStatus.active.rawValue
        }
        return raw
    }

    private static func normalizedTimePrecision(_ raw: String?) -> String {
        guard let raw, TransactionTimePrecision(rawValue: raw) != nil else {
            return TransactionTimePrecision.legacyUnknown.rawValue
        }
        return raw
    }

    private static func data(for entry: Entry, in archive: Archive) throws -> Data {
        var output = Data()
        output.reserveCapacity(Int(min(entry.uncompressedSize, UInt64(Int.max))))
        do {
            _ = try archive.extract(entry) { output.append($0) }
            return output
        } catch {
            throw AndroidBackupImportError.invalidArchive
        }
    }

    private static func extractAndHash(
        _ entry: Entry,
        from archive: Archive,
        to destination: URL?,
        maximumBytes: UInt64,
        fileManager: FileManager
    ) throws -> String {
        var output: FileHandle?
        if let destination {
            try fileManager.createDirectory(
                at: destination.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            guard fileManager.createFile(atPath: destination.path, contents: nil) else {
                throw AndroidBackupImportError.invalidArchive
            }
            output = try FileHandle(forWritingTo: destination)
        }
        defer { try? output?.close() }

        var hasher = SHA256()
        var extractedBytes: UInt64 = 0
        do {
            _ = try archive.extract(entry) { chunk in
                let chunkBytes = UInt64(chunk.count)
                guard chunkBytes <= maximumBytes - extractedBytes else {
                    throw AndroidBackupImportError.archiveTooLarge
                }
                extractedBytes += chunkBytes
                hasher.update(data: chunk)
                try output?.write(contentsOf: chunk)
            }
            try output?.synchronize()
        } catch let error as AndroidBackupImportError {
            if let destination { try? fileManager.removeItem(at: destination) }
            throw error
        } catch {
            if let destination { try? fileManager.removeItem(at: destination) }
            throw AndroidBackupImportError.invalidArchive
        }
        guard extractedBytes == entry.uncompressedSize else {
            if let destination { try? fileManager.removeItem(at: destination) }
            throw AndroidBackupImportError.invalidArchive
        }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }

    private static func isSafeArchivePath(_ path: String) -> Bool {
        path == "manifest.json" || isSafePayloadPath(path)
    }

    private static func isSafePayloadPath(_ path: String) -> Bool {
        guard path == "database/qingji.db"
                || path.hasPrefix("receipts/")
                || path.hasPrefix("asset_media/") else { return false }
        return isSafeRelativePath(path)
    }

    private static func isSafeRelativePath(_ path: String) -> Bool {
        guard !path.isEmpty,
              !path.hasPrefix("/"),
              !path.contains("\\"),
              !path.contains(":") else { return false }
        let pieces = path.split(separator: "/", omittingEmptySubsequences: false)
        return pieces.allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
}

private struct BackupPayload {
    var databaseURL: URL?
    var databaseVersion: Int?
    var receipts: [String: URL]
}

private struct StagedReceipts {
    var directory: URL?
    var pathsByRelativePath: [String: String]
    var pathsByUniqueName: [String: String]

    static let empty = StagedReceipts(
        directory: nil,
        pathsByRelativePath: [:],
        pathsByUniqueName: [:]
    )

    var count: Int { pathsByRelativePath.count }

    func path(forAndroidPath rawPath: String) -> String {
        guard !rawPath.isEmpty else { return "" }
        let normalized = rawPath.replacingOccurrences(of: "\\", with: "/")
        if let range = normalized.range(of: "/receipts/", options: .backwards) {
            let relative = String(normalized[range.upperBound...])
            if let exact = pathsByRelativePath[relative] { return exact }
        }
        let name = normalized.split(separator: "/").last.map { String($0) } ?? ""
        return pathsByUniqueName[name] ?? ""
    }

    func removeFromDisk(fileManager: FileManager) {
        guard let directory else { return }
        try? fileManager.removeItem(at: directory)
    }
}

private struct AndroidSnapshot {
    var databaseVersion: Int
    var books: [AndroidBook]
    var accounts: [AndroidAccount]
    var categories: [AndroidCategory]
    var tags: [AndroidTag]
    var transactions: [AndroidTransaction]
}

private struct AndroidBook {
    var id: Int64
    var uuid: String
    var name: String
    var icon: String
    var cover: String
    var remark: String
    var sortOrder: Int
    var createdMS: Int64
    var starred: Bool
    var includeInTotal: Bool
    var updatedMS: Int64
    var isDeleted: Bool
    var deletedAtMS: Int64?
}

private struct AndroidAccount {
    var id: Int64
    var uuid: String
    var name: String
    var currencyCode: String
    var type: String
    var openingBalance: String
    var includeInNetWorth: Bool
    var institution: String
    var sortOrder: Int
    var status: String
    var createdMS: Int64
    var updatedMS: Int64
    var isDeleted: Bool
    var deletedAtMS: Int64?
}

private struct AndroidCategory {
    var id: Int64
    var uuid: String
    var key: String
    var nameZh: String
    var nameEn: String
    var emoji: String
    var kind: String
    var parentID: Int64?
    var hidden: Bool
    var sortOrder: Int
    var createdMS: Int64
    var updatedMS: Int64
    var isDeleted: Bool
    var deletedAtMS: Int64?
}

private struct AndroidTag {
    var id: Int64
    var uuid: String
    var name: String
    var color: Int64
    var sortOrder: Int
    var createdMS: Int64
    var updatedMS: Int64
    var isDeleted: Bool
    var deletedAtMS: Int64?
}

private struct AndroidTransaction {
    var id: Int64
    var uuid: String
    var bookID: Int64?
    var kind: String
    var amount: String
    var currencyCode: String
    var categoryID: Int64?
    var accountID: Int64?
    var toAccountID: Int64?
    var note: String
    var dateMS: Int64
    var timePrecision: String
    var tags: String
    var reimbursable: Bool
    var imagePath: String
    var excluded: Bool
    var refundOf: Int64?
    var createdMS: Int64
    var updatedMS: Int64
    var isDeleted: Bool
    var deletedAtMS: Int64?
}
