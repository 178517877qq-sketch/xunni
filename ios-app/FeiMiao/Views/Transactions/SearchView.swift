import SwiftUI
import FeiMiaoDomain

struct SearchView: View {
    @EnvironmentObject private var store: AppStore
    @State private var query = ""
    @State private var kind: TransactionKind?
    @State private var range = SearchRange.all
    @State private var results: [LedgerTransaction] = []
    @State private var editingTransaction: LedgerTransaction?
    @State private var searchTask: Task<Void, Never>?

    enum SearchRange: String, CaseIterable, Identifiable {
        case all = "全部时间"
        case month = "近 30 天"
        case year = "今年"

        var id: String { rawValue }
    }

    var body: some View {
        List {
            Section {
                Picker("类型", selection: $kind) {
                    Text("全部").tag(TransactionKind?.none)
                    Text("支出").tag(TransactionKind?.some(.expense))
                    Text("收入").tag(TransactionKind?.some(.income))
                    Text("转账").tag(TransactionKind?.some(.transfer))
                }
                .pickerStyle(.segmented)

                Picker("时间", selection: $range) {
                    ForEach(SearchRange.allCases) { option in
                        Text(option.rawValue).tag(option)
                    }
                }
            }

            if results.isEmpty {
                ContentUnavailableView.search(text: query)
                    .listRowBackground(Color.clear)
            } else {
                ForEach(groupTransactionsByDay(results)) { group in
                    Section(group.day.formatted(.dateTime.year().month().day())) {
                        ForEach(group.items) { item in
                            Button {
                                editingTransaction = item
                            } label: {
                                TransactionRow(transaction: item)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .navigationTitle("搜索")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $query, prompt: "备注、分类、账户或金额")
        .onAppear(perform: refresh)
        .onChange(of: query) { _, _ in scheduleRefresh() }
        .onChange(of: kind) { _, _ in refresh() }
        .onChange(of: range) { _, _ in refresh() }
        .onDisappear { searchTask?.cancel() }
        .sheet(item: $editingTransaction) { item in
            ManualEntryView(editing: item) {
                editingTransaction = nil
                refresh()
            }
        }
    }

    private func refresh() {
        let calendar = Calendar.current
        let startDate: Date?
        switch range {
        case .all:
            startDate = nil
        case .month:
            startDate = calendar.date(byAdding: .day, value: -30, to: .now)
        case .year:
            startDate = calendar.date(from: calendar.dateComponents([.year], from: .now))
        }
        results = store.transactions(
            matching: TransactionFilter(
                bookID: store.selectedBookID,
                kind: kind,
                searchText: query,
                startDate: startDate
            )
        )
    }

    private func scheduleRefresh() {
        searchTask?.cancel()
        searchTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 180_000_000)
            guard !Task.isCancelled else { return }
            refresh()
        }
    }
}
