import Foundation
import GRDB
import FeiMiaoDomain

public final class AppDatabase: @unchecked Sendable {
    public static let androidSchemaVersion = 40

    public let url: URL?
    let queue: DatabaseQueue

    public init(url: URL) throws {
        self.url = url
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        queue = try DatabaseQueue(path: url.path, configuration: Self.configuration())
        try migrateAndSeed()
    }

    public init(inMemory: Bool) throws {
        precondition(inMemory, "Use init(url:) for a persistent database")
        url = nil
        queue = try DatabaseQueue(configuration: Self.configuration())
        try migrateAndSeed()
    }

    public static func defaultURL(fileManager: FileManager = .default) throws -> URL {
        let root = try fileManager.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return root
            .appendingPathComponent("FeiMiao", isDirectory: true)
            .appendingPathComponent("feimiao.sqlite", isDirectory: false)
    }

    private static func configuration() -> Configuration {
        var configuration = Configuration()
        configuration.prepareDatabase { database in
            try database.execute(sql: "PRAGMA foreign_keys = ON")
        }
        return configuration
    }

    private func migrateAndSeed() throws {
        var migrator = DatabaseMigrator()
        migrator.registerMigration("core-v40") { db in
            try db.execute(sql: Self.schemaSQL)
            try db.execute(sql: "PRAGMA user_version = \(Self.androidSchemaVersion)")
        }
        migrator.registerMigration("core-uuid-indexes") { db in
            try db.execute(sql: Self.uuidIndexSQL)
        }
        migrator.registerMigration("core-query-indexes") { db in
            try db.execute(sql: Self.queryIndexSQL)
        }
        try migrator.migrate(queue)
        try queue.write { db in
            try Self.seedIfNeeded(db)
        }
    }

    private static func seedIfNeeded(_ db: Database) throws {
        let now = Int64(Date().timeIntervalSince1970 * 1_000)
        if try Int.fetchOne(db, sql: "SELECT COUNT(*) FROM books") == 0 {
            try db.execute(
                sql: """
                    INSERT INTO books
                    (uuid, name, icon, cover, remark, sort_order, created_ms, starred, include_in_total, updated_ms)
                    VALUES (?, '总账本', '📒', 'default.png', '', 0, ?, 1, 1, ?)
                    """,
                arguments: [UUID().uuidString, now, now]
            )
        }
        if try Int.fetchOne(db, sql: "SELECT COUNT(*) FROM accounts") == 0 {
            try db.execute(
                sql: """
                    INSERT INTO accounts
                    (uuid, name, currency_code, type, opening_balance, include_in_net_worth,
                     institution, sort_order, created_ms, updated_ms, status)
                    VALUES (?, '现金', 'CNY', 'cash', '0', 1, '', 0, ?, ?, 'active')
                    """,
                arguments: [UUID().uuidString, now, now]
            )
        }
        if try Int.fetchOne(db, sql: "SELECT COUNT(*) FROM categories") == 0 {
            let topLevel = CategoryCatalog.all.filter { $0.parentKey == nil }
            let children = CategoryCatalog.all.filter { $0.parentKey != nil }
            for (index, seed) in topLevel.enumerated() {
                try insertCategory(seed, parentID: nil, sortOrder: index, now: now, db: db)
            }
            for (index, seed) in children.enumerated() {
                let parentID = try Int64.fetchOne(
                    db,
                    sql: "SELECT id FROM categories WHERE key = ?",
                    arguments: [seed.parentKey]
                )
                try insertCategory(seed, parentID: parentID, sortOrder: index, now: now, db: db)
            }
        }
    }

    private static func insertCategory(
        _ seed: CategorySeed,
        parentID: Int64?,
        sortOrder: Int,
        now: Int64,
        db: Database
    ) throws {
        try db.execute(
            sql: """
                INSERT INTO categories
                (uuid, key, name_zh, name_en, emoji, kind, parent_id, hidden,
                 sort_order, created_ms, updated_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
            arguments: [
                "category-\(seed.key)", seed.key, seed.nameZh, seed.nameEn,
                seed.emoji, seed.kind.rawValue, parentID, sortOrder, now, now,
            ]
        )
    }

    private static let schemaSQL = """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS accounts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          uuid TEXT NOT NULL,
          name TEXT NOT NULL,
          currency_code TEXT NOT NULL DEFAULT 'CNY',
          type TEXT NOT NULL DEFAULT 'cash',
          opening_balance TEXT NOT NULL DEFAULT '0',
          include_in_net_worth INTEGER NOT NULL DEFAULT 1,
          institution TEXT NOT NULL DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'active',
          created_ms INTEGER NOT NULL,
          updated_ms INTEGER NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          deleted_at_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          uuid TEXT NOT NULL,
          key TEXT NOT NULL UNIQUE,
          name_zh TEXT NOT NULL,
          name_en TEXT NOT NULL,
          emoji TEXT NOT NULL DEFAULT '🏷️',
          kind TEXT NOT NULL,
          parent_id INTEGER REFERENCES categories(id),
          hidden INTEGER NOT NULL DEFAULT 0,
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_ms INTEGER NOT NULL,
          updated_ms INTEGER NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          deleted_at_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          uuid TEXT NOT NULL,
          name TEXT NOT NULL,
          icon TEXT NOT NULL DEFAULT '📒',
          cover TEXT NOT NULL DEFAULT '',
          remark TEXT NOT NULL DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_ms INTEGER NOT NULL,
          starred INTEGER NOT NULL DEFAULT 0,
          include_in_total INTEGER NOT NULL DEFAULT 1,
          updated_ms INTEGER NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          deleted_at_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          uuid TEXT NOT NULL,
          name TEXT NOT NULL,
          color INTEGER NOT NULL DEFAULT 4286351771,
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_ms INTEGER NOT NULL,
          updated_ms INTEGER NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          deleted_at_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS transactions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          uuid TEXT NOT NULL,
          book_id INTEGER REFERENCES books(id),
          kind TEXT NOT NULL,
          amount TEXT NOT NULL,
          currency_code TEXT NOT NULL DEFAULT 'CNY',
          category_id INTEGER REFERENCES categories(id),
          account_id INTEGER REFERENCES accounts(id),
          to_account_id INTEGER REFERENCES accounts(id),
          note TEXT NOT NULL DEFAULT '',
          date_ms INTEGER NOT NULL,
          time_precision TEXT NOT NULL DEFAULT 'exact',
          tags TEXT NOT NULL DEFAULT '',
          reimbursable INTEGER NOT NULL DEFAULT 0,
          image_path TEXT NOT NULL DEFAULT '',
          excluded INTEGER NOT NULL DEFAULT 0,
          refund_of INTEGER REFERENCES transactions(id),
          created_ms INTEGER NOT NULL,
          updated_ms INTEGER NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          deleted_at_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS app_settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date_ms DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_transactions_book ON transactions(book_id, date_ms DESC);
        CREATE INDEX IF NOT EXISTS idx_transactions_refund ON transactions(refund_of);
        CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id, sort_order);
        """

    private static let uuidIndexSQL = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_uuid ON accounts(uuid);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_uuid ON categories(uuid);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_books_uuid ON books(uuid);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_uuid ON tags(uuid);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_uuid ON transactions(uuid);
        """

    private static let queryIndexSQL = """
        CREATE INDEX IF NOT EXISTS idx_transactions_account
          ON transactions(account_id, is_deleted);
        CREATE INDEX IF NOT EXISTS idx_transactions_to_account
          ON transactions(to_account_id, is_deleted);
        """
}
