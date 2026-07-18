import XCTest
@testable import FeiMiaoDomain

final class CategoryCatalogTests: XCTestCase {
    func testKeysAreUniqueAndChildrenHaveParents() {
        let all = CategoryCatalog.all
        XCTAssertEqual(Set(all.map(\.key)).count, all.count)
        let keys = Set(all.map(\.key))
        for item in all {
            if let parent = item.parentKey {
                XCTAssertTrue(keys.contains(parent), "Missing parent \(parent) for \(item.key)")
                XCTAssertEqual(CategoryCatalog.seed(for: parent)?.kind, item.kind)
            }
        }
    }

    func testAndroidStableKeysRemainAvailable() {
        XCTAssertEqual(CategoryCatalog.seed(for: "dining")?.nameZh, "食品餐饮")
        XCTAssertEqual(CategoryCatalog.seed(for: "trans_public")?.parentKey, "transport")
        XCTAssertEqual(CategoryCatalog.seed(for: "salary")?.kind, .income)
        XCTAssertEqual(CategoryCatalog.emoji(for: "missing-key"), "🏷️")
    }
}
