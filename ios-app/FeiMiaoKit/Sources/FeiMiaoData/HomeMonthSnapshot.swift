import Foundation
import FeiMiaoDomain

/// A consistent, read-only projection of one ledger month for the home screen.
///
/// `LedgerTransaction` predates strict concurrency adoption. The contained
/// values are immutable copies produced by one GRDB read, so the snapshot is
/// safe to transfer back to the main actor.
public struct HomeMonthSnapshot: @unchecked Sendable {
    public let bookID: Int64?
    public let monthStart: Date
    public let nextMonthStart: Date
    public let transactions: [LedgerTransaction]
    public let summary: LedgerSummary
    public let netAmounts: [Int64: MoneyAmount]

    public init(
        bookID: Int64?,
        monthStart: Date,
        nextMonthStart: Date,
        transactions: [LedgerTransaction],
        summary: LedgerSummary,
        netAmounts: [Int64: MoneyAmount]
    ) {
        self.bookID = bookID
        self.monthStart = monthStart
        self.nextMonthStart = nextMonthStart
        self.transactions = transactions
        self.summary = summary
        self.netAmounts = netAmounts
    }
}
