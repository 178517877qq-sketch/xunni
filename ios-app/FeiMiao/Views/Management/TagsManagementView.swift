import SwiftUI
import FeiMiaoDomain

struct TagsManagementView: View {
    @EnvironmentObject private var store: AppStore
    @State private var editorRoute: TagEditorRoute?
    @State private var pendingDeletion: LedgerTag?

    var body: some View {
        List {
            Section {
                if store.tags.isEmpty {
                    ContentUnavailableView(
                        "还没有标签",
                        systemImage: "tag",
                        description: Text("用标签补充跨分类场景，例如旅行、家庭或工作。")
                    )
                    .frame(maxWidth: .infinity)
                    .listRowBackground(Color.clear)
                } else {
                    ForEach(store.tags) { tag in
                        tagRow(tag)
                    }
                }
            } footer: {
                Text("删除标签不会删除历史账单。")
            }
        }
        .navigationTitle("标签管理")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    editorRoute = TagEditorRoute(tag: nil)
                } label: {
                    Label("新增标签", systemImage: "plus")
                }
                .accessibilityIdentifier("add-tag")
            }
        }
        .sheet(item: $editorRoute) { route in
            TagEditorView(tag: route.tag)
        }
        .confirmationDialog(
            "删除“\(pendingDeletion?.name ?? "")”？",
            isPresented: Binding(
                get: { pendingDeletion != nil },
                set: { if !$0 { pendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("删除", role: .destructive) {
                guard let tag = pendingDeletion else { return }
                store.deleteTag(tag.id)
                pendingDeletion = nil
            }
            Button("取消", role: .cancel) { pendingDeletion = nil }
        } message: {
            Text("账单会保留，只是不再显示这个标签。")
        }
    }

    private func tagRow(_ tag: LedgerTag) -> some View {
        Button {
            editorRoute = TagEditorRoute(tag: tag)
        } label: {
            HStack(spacing: 12) {
                Circle()
                    .fill(Color(tagARGB: tag.colorARGB))
                    .frame(width: 12, height: 12)
                Text(tag.name)
                    .foregroundStyle(.primary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("tag-row-\(tag.id)")
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button("删除", role: .destructive) {
                pendingDeletion = tag
            }
            Button("编辑") {
                editorRoute = TagEditorRoute(tag: tag)
            }
            .tint(.fmPrimary)
        }
    }
}

private struct TagEditorRoute: Identifiable {
    let id = UUID()
    let tag: LedgerTag?
}

private struct TagEditorView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    private let tag: LedgerTag?
    @State private var name: String
    @State private var colorARGB: Int64

    init(tag: LedgerTag?) {
        self.tag = tag
        _name = State(initialValue: tag?.name ?? "")
        _colorARGB = State(initialValue: tag?.colorARGB ?? TagColorPreset.palette[0].id)
    }

    private var colorChoices: [TagColorPreset] {
        if TagColorPreset.palette.contains(where: { $0.id == colorARGB }) {
            return TagColorPreset.palette
        }
        return [TagColorPreset(id: colorARGB, title: "当前颜色")] + TagColorPreset.palette
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("标签名称") {
                    TextField("例如：旅行", text: $name)
                }

                Section("标签颜色") {
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 16) {
                        ForEach(colorChoices) { preset in
                            Button {
                                colorARGB = preset.id
                            } label: {
                                ZStack {
                                    Circle()
                                        .fill(Color(tagARGB: preset.id))
                                        .frame(width: 34, height: 34)
                                    if colorARGB == preset.id {
                                        Image(systemName: "checkmark")
                                            .font(.caption.bold())
                                            .foregroundStyle(.white)
                                        }
                                }
                                .frame(minWidth: 44, minHeight: 44)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel(preset.title)
                            .accessibilityAddTraits(colorARGB == preset.id ? .isSelected : [])
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle(tag == nil ? "新增标签" : "编辑标签")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存", action: save)
                        .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }

    private func save() {
        guard store.databaseURL != nil else {
            store.presentedError = "账本数据库当前不可用，请稍后重试。"
            return
        }
        store.presentedError = nil
        if var tag {
            tag.name = name
            tag.colorARGB = colorARGB
            store.updateTag(tag)
        } else {
            store.createTag(name: name, colorARGB: colorARGB)
        }
        if store.presentedError == nil { dismiss() }
    }
}

private struct TagColorPreset: Identifiable {
    let id: Int64
    let title: String

    static let palette: [Self] = [
        .init(id: 0xFF4A617D, title: "蓝灰"),
        .init(id: 0xFF6E7F96, title: "雾蓝"),
        .init(id: 0xFFA36E3A, title: "铜金"),
        .init(id: 0xFFD17842, title: "暖橙"),
        .init(id: 0xFF4C8C65, title: "健康绿"),
        .init(id: 0xFF7B6A9B, title: "灰紫"),
        .init(id: 0xFFB05D6B, title: "豆沙"),
        .init(id: 0xFF5D8585, title: "青灰"),
        .init(id: 0xFF8A7654, title: "棕褐"),
        .init(id: 0xFF68707A, title: "中性灰"),
        .init(id: 0xFF3F76A6, title: "湖蓝"),
        .init(id: 0xFF93604D, title: "陶土"),
    ]
}

private extension Color {
    init(tagARGB value: Int64) {
        let alpha = Double((value >> 24) & 0xFF) / 255
        let red = Double((value >> 16) & 0xFF) / 255
        let green = Double((value >> 8) & 0xFF) / 255
        let blue = Double(value & 0xFF) / 255
        self.init(.sRGB, red: red, green: green, blue: blue, opacity: alpha)
    }
}
