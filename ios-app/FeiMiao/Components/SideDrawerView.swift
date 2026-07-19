import SwiftUI
import UIKit
import FeiMiaoDomain

enum AppDrawerDestination: String, Identifiable, Hashable {
    case transactions
    case accounts
    case books
    case categories
    case tags
    case settings

    var id: String { rawValue }
}

struct SideDrawerView: View {
    @EnvironmentObject private var store: AppStore

    let width: CGFloat
    let onSelect: (AppDrawerDestination) -> Void
    let onClose: () -> Void

    @State private var showsUpcoming = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            brandHeader

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 2) {
                    unavailableRow(
                        "统计数据",
                        systemImage: "chart.bar.xaxis"
                    )
                    destinationButton(
                        "资产管理",
                        systemImage: "wallet.bifold",
                        destination: .accounts
                    )
                    unavailableRow(
                        "预算管理",
                        systemImage: "calendar"
                    )
                    unavailableRow(
                        "存钱目标",
                        systemImage: "target"
                    )
                    unavailableRow(
                        "喵助手",
                        systemImage: "sparkles"
                    )

                    moreSection

                    Divider()
                        .overlay(Color.fmHairline)
                        .padding(.horizontal, FeiMiaoSpacing.large)
                        .padding(.vertical, FeiMiaoSpacing.small)

                    Text("我的账本")
                        .font(FeiMiaoType.sectionLabel)
                        .foregroundStyle(Color.fmSecondaryText)
                        .padding(.horizontal, 20)
                        .padding(.bottom, 6)

                    ForEach(store.books) { book in
                        bookButton(book)
                    }
                }
                .padding(.bottom, FeiMiaoSpacing.small)
            }

            bottomActions
        }
        .frame(width: width, alignment: .leading)
        .background {
            FeiMiaoPageBackground()
                .ignoresSafeArea()
        }
    }

    private var brandHeader: some View {
        HStack {
            if let logo = loadBrandLogo() {
                Image(uiImage: logo)
                    .resizable()
                    .scaledToFit()
                    .frame(height: 36)
                    .accessibilityLabel("肥喵记账")
            } else {
                Text("肥喵记账")
                    .font(.system(size: 29, weight: .semibold, design: .serif))
                    .foregroundStyle(.primary)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.leading, 8)
        .padding(.trailing, 14)
        .padding(.top, 18)
        .padding(.bottom, 16)
    }

    private var moreSection: some View {
        VStack(alignment: .leading, spacing: 2) {
            Button {
                withAnimation(FeiMiaoMotion.enter) {
                    showsUpcoming.toggle()
                }
            } label: {
                HStack(spacing: FeiMiaoSpacing.medium) {
                    Image(systemName: "ellipsis")
                        .frame(width: 24)
                    Text(showsUpcoming ? "收起" : "更多")
                    Spacer()
                    Image(systemName: showsUpcoming ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundStyle(Color.fmHintText)
                }
                .font(FeiMiaoType.body)
                .foregroundStyle(Color.fmSecondaryText)
                .frame(minHeight: 44)
                .padding(.horizontal, 20)
                .contentShape(Rectangle())
            }
            .buttonStyle(.feiMiaoPressable)

            if showsUpcoming {
                destinationButton(
                    "分类管理",
                    systemImage: "square.grid.2x2",
                    destination: .categories
                )
                destinationButton(
                    "标签管理",
                    systemImage: "tag",
                    destination: .tags
                )
                destinationButton(
                    "导入导出",
                    systemImage: "square.and.arrow.down",
                    destination: .settings
                )
                unavailableRow("待报销", systemImage: "receipt")
                unavailableRow("定时记账", systemImage: "clock.arrow.circlepath")
                unavailableRow("自动记账", systemImage: "bell")
            }
        }
    }

    private var bottomActions: some View {
        HStack {
            Button {
                onSelect(.books)
            } label: {
                Label("新建账本", systemImage: "square.and.pencil")
                    .font(FeiMiaoType.body)
                    .foregroundStyle(.primary)
                    .padding(.horizontal, 16)
                    .frame(minHeight: 44)
                    .background(Color.fmCard, in: Capsule())
                    .overlay {
                        Capsule().stroke(Color.fmHairline, lineWidth: 0.5)
                    }
            }
            .buttonStyle(.feiMiaoPressable)

            Spacer()

            Button {
                onSelect(.settings)
            } label: {
                Image(systemName: "gearshape")
                    .font(.system(size: 19, weight: .medium))
                    .foregroundStyle(.primary)
                    .frame(width: 44, height: 44)
                    .background(Color.fmCard, in: Circle())
                    .overlay {
                        Circle().stroke(Color.fmHairline, lineWidth: 0.5)
                    }
            }
            .buttonStyle(.feiMiaoPressable)
            .accessibilityLabel("设置")
        }
        .padding(.horizontal, FeiMiaoSpacing.large)
        .padding(.top, FeiMiaoSpacing.small)
        .padding(.bottom, FeiMiaoSpacing.large)
    }

    private func destinationButton(
        _ title: String,
        systemImage: String,
        destination: AppDrawerDestination
    ) -> some View {
        Button {
            onSelect(destination)
        } label: {
            drawerRow(title, systemImage: systemImage)
        }
        .buttonStyle(.feiMiaoPressable)
        .accessibilityIdentifier("drawer-\(destination.rawValue)")
    }

    private func unavailableRow(_ title: String, systemImage: String) -> some View {
        drawerRow(title, systemImage: systemImage)
            .opacity(0.46)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title)，暂未开放")
    }

    private func drawerRow(_ title: String, systemImage: String) -> some View {
        HStack(spacing: FeiMiaoSpacing.medium) {
            Image(systemName: systemImage)
                .font(.system(size: 18, weight: .regular))
                .frame(width: 24)
            Text(title)
                .font(FeiMiaoType.body)
            Spacer()
        }
        .foregroundStyle(.primary)
        .frame(minHeight: 44)
        .padding(.horizontal, 20)
        .contentShape(Rectangle())
    }

    private func bookButton(_ book: LedgerBook) -> some View {
        let isSelected = store.selectedBookID == book.id
            || (store.selectedBookID == nil && book.id == store.defaultBookID)
        return Button {
            store.setSelectedBook(book.id == store.defaultBookID ? nil : book.id)
            onClose()
        } label: {
            HStack(spacing: FeiMiaoSpacing.medium) {
                BookCoverView(cover: book.cover, fallbackIcon: book.icon)
                    .frame(width: 34, height: 42)
                    .clipShape(
                        RoundedRectangle(
                            cornerRadius: FeiMiaoRadius.badge,
                            style: .continuous
                        )
                    )
                VStack(alignment: .leading, spacing: 2) {
                    Text(book.name)
                        .font(FeiMiaoType.body)
                    if !book.remark.isEmpty {
                        Text(book.remark)
                            .font(FeiMiaoType.caption)
                            .foregroundStyle(Color.fmHintText)
                            .lineLimit(1)
                    }
                }
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color.fmPrimary)
                }
            }
            .foregroundStyle(.primary)
            .padding(.horizontal, 20)
            .frame(minHeight: 54)
            .contentShape(Rectangle())
        }
        .buttonStyle(.feiMiaoPressable)
        .accessibilityIdentifier("drawer-book-\(book.id)")
    }

    private func loadBrandLogo() -> UIImage? {
        if let image = UIImage(named: FeiMiaoAssetName.brandLogo) {
            return image
        }
        let locations: [URL?] = [
            Bundle.main.url(forResource: FeiMiaoAssetName.brandLogo, withExtension: "png"),
            Bundle.main.url(
                forResource: FeiMiaoAssetName.brandLogo,
                withExtension: "png",
                subdirectory: "Brand"
            ),
        ]
        return locations.compactMap { $0 }.lazy.compactMap {
            UIImage(contentsOfFile: $0.path)
        }.first
    }
}
