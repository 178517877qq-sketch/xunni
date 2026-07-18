import SwiftUI
import UniformTypeIdentifiers
import FeiMiaoDomain

struct SettingsView: View {
    @EnvironmentObject private var store: AppStore
    @State private var showingBackupPicker = false
    @State private var pendingImportURL: URL?
    @State private var importSummary: String?

    var body: some View {
        NavigationStack {
            List {
                Section("账务资料") {
                    NavigationLink {
                        BooksManagementView()
                    } label: {
                        ManagementLinkLabel(
                            title: "账本管理",
                            subtitle: "\(store.books.count) 个账本",
                            systemImage: "books.vertical",
                            tint: .fmPrimary
                        )
                    }

                    NavigationLink {
                        AccountsManagementView()
                    } label: {
                        ManagementLinkLabel(
                            title: "账户管理",
                            subtitle: "\(store.accounts.count) 个账户",
                            systemImage: "wallet.bifold",
                            tint: .fmPrimary
                        )
                    }

                    NavigationLink {
                        CategoriesManagementView()
                    } label: {
                        ManagementLinkLabel(
                            title: "分类管理",
                            subtitle: categorySummary,
                            systemImage: "square.grid.2x2",
                            tint: .fmIncome
                        )
                    }

                    NavigationLink {
                        TagsManagementView()
                    } label: {
                        ManagementLinkLabel(
                            title: "标签管理",
                            subtitle: "\(store.tags.count) 个标签",
                            systemImage: "tag",
                            tint: .fmHealthy
                        )
                    }
                }

                Section("数据与隐私") {
                    Button {
                        showingBackupPicker = true
                    } label: {
                        Label("导入 Android 肥喵备份", systemImage: "square.and.arrow.down")
                    }
                    .disabled(store.isImportingBackup)

                    if store.isImportingBackup {
                        HStack(spacing: 10) {
                            ProgressView()
                            Text("正在校验并导入…")
                                .foregroundStyle(.secondary)
                        }
                    }

                    LabeledContent {
                        Text("仅本机")
                            .foregroundStyle(.secondary)
                    } label: {
                        Label("数据存储", systemImage: "internaldrive")
                    }

                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "lock.shield")
                            .foregroundStyle(.fmHealthy)
                            .frame(width: 24)
                        VStack(alignment: .leading, spacing: 3) {
                            Text("账务数据保存在你的设备上")
                            Text("当前版本不会在后台上传账本、账户或账单。")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("关于") {
                    LabeledContent("应用", value: "肥喵记账")
                    LabeledContent("版本", value: versionText)
                }
            }
            .navigationTitle("设置")
            .fileImporter(
                isPresented: $showingBackupPicker,
                allowedContentTypes: [.zip, .data]
            ) { result in
                switch result {
                case let .success(url):
                    pendingImportURL = url
                case let .failure(error):
                    store.presentedError = "无法读取备份：\(error.localizedDescription)"
                }
            }
            .confirmationDialog(
                "用 Android 备份替换当前账务数据？",
                isPresented: Binding(
                    get: { pendingImportURL != nil },
                    set: { if !$0 { pendingImportURL = nil } }
                ),
                titleVisibility: .visible
            ) {
                Button("替换并导入", role: .destructive) {
                    guard let url = pendingImportURL else { return }
                    pendingImportURL = nil
                    Task {
                        guard let result = await store.importAndroidBackup(from: url) else { return }
                        let backupNote = result.safetyBackupPath == nil ? "" : " 原有 iOS 数据已保留安全备份。"
                        importSummary = "已导入 \(result.transactionCount) 笔账单、\(result.bookCount) 个账本、\(result.accountCount) 个账户和 \(result.receiptCount) 张收据。\(backupNote)"
                    }
                }
                Button("取消", role: .cancel) { pendingImportURL = nil }
            } message: {
                Text("当前 iOS 账本会被替换。导入前会完整校验备份清单和文件哈希；API Key 不会从 Android 备份带入。")
            }
            .alert(
                "导入完成",
                isPresented: Binding(
                    get: { importSummary != nil },
                    set: { if !$0 { importSummary = nil } }
                )
            ) {
                Button("好", role: .cancel) { importSummary = nil }
            } message: {
                Text(importSummary ?? "")
            }
        }
    }

    private var categorySummary: String {
        let active = store.categories.filter { !$0.isDeleted }
        let rootCount = active.filter { $0.parentID == nil }.count
        return "\(rootCount) 个一级 · \(active.count - rootCount) 个二级"
    }

    private var versionText: String {
        let version = (Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String) ?? "开发版"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String
        guard let build, !build.isEmpty else { return version }
        return "\(version) (\(build))"
    }
}

private struct ManagementLinkLabel: View {
    let title: String
    let subtitle: String
    let systemImage: String
    let tint: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.body.weight(.semibold))
                .foregroundStyle(tint)
                .frame(width: 32, height: 32)
                .background(tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .foregroundStyle(.primary)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}
