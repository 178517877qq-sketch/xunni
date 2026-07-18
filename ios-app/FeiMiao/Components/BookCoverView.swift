import Foundation
import SwiftUI

struct BookCoverOption: Identifiable, Hashable {
    let token: String
    let title: String

    var id: String { token }

    static let all: [BookCoverOption] = [
        .init(token: "default.png", title: "日常"),
        .init(token: "dining.png", title: "餐饮"),
        .init(token: "shopping.png", title: "购物"),
        .init(token: "travel.png", title: "旅行"),
        .init(token: "pet.png", title: "宠物"),
        .init(token: "baby.png", title: "母婴"),
        .init(token: "family.png", title: "家庭"),
        .init(token: "business.png", title: "生意"),
        .init(token: "couple.png", title: "情侣"),
        .init(token: "multi.png", title: "综合"),
        .init(token: "beauty.png", title: "美好"),
    ]

    static func normalizedKey(for cover: String) -> String? {
        let normalized = cover.replacingOccurrences(of: "\\", with: "/")
        guard let filename = normalized.split(separator: "/").last.map(String.init),
              !filename.isEmpty else { return nil }
        let key = (filename as NSString).deletingPathExtension
        return all.contains { ($0.token as NSString).deletingPathExtension == key } ? key : nil
    }
}

struct BookCoverView: View {
    let cover: String
    let fallbackIcon: String

    var body: some View {
        Group {
            if let key = BookCoverOption.normalizedKey(for: cover) {
                Image(key)
                    .resizable()
                    .scaledToFill()
            } else {
                ZStack {
                    LinearGradient(
                        colors: [Color.fmPrimarySoft, Color.fmCard],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                    Text(fallbackIcon.isEmpty ? "📒" : fallbackIcon)
                        .font(.title2)
                }
            }
        }
        .clipped()
        .accessibilityHidden(true)
    }
}
