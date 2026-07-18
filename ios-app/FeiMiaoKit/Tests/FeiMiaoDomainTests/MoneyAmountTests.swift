import XCTest
@testable import FeiMiaoDomain

final class MoneyAmountTests: XCTestCase {
    func testDecimalStorageRoundTripIsExact() throws {
        let value = try XCTUnwrap(MoneyAmount(" 1234567890.125 "))
        XCTAssertEqual(value.storageString, "1234567890.125")
        XCTAssertEqual(MoneyAmount(value.storageString), value)
    }

    func testArithmeticDoesNotUseBinaryFloatingPoint() throws {
        let first = try XCTUnwrap(MoneyAmount("0.1"))
        let second = try XCTUnwrap(MoneyAmount("0.2"))
        XCTAssertEqual((first + second).storageString, "0.3")
        XCTAssertEqual((second - first).storageString, "0.1")
    }

    func testInvalidStorageIsRejected() {
        XCTAssertNil(MoneyAmount(""))
        XCTAssertNil(MoneyAmount("12元"))
        XCTAssertNil(MoneyAmount("--1"))
    }

    func testDraftRequiresPositiveAmount() {
        XCTAssertNil(TransactionDraft(amountText: "0").validatedAmount)
        XCTAssertNil(TransactionDraft(amountText: "-1").validatedAmount)
        XCTAssertEqual(TransactionDraft(amountText: "18.90").validatedAmount?.storageString, "18.9")
    }

    func testTimePrecisionMatchesAndroidStorageKeys() {
        XCTAssertEqual(TransactionTimePrecision.exact.rawValue, "exact")
        XCTAssertEqual(TransactionTimePrecision.entryClock.rawValue, "entry_clock")
        XCTAssertEqual(TransactionTimePrecision.dateOnly.rawValue, "date_only")
        XCTAssertEqual(TransactionTimePrecision.legacyUnknown.rawValue, "legacy_unknown")
    }
}
