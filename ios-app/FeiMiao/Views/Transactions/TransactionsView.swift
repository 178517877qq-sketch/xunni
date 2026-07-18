import SwiftUI
import FeiMiaoDomain

struct TransactionsView: View {
    @EnvironmentObject private var store: AppStore
    @State private var selectedKind: TransactionKind?
    @State private var editingTransaction: LedgerTransaction?
    @State private var pendingDelete: LedgerTransaction?

    private var visibleTransactions: [LedgerTransaction] {
        guard let selectedKind else { return store.transactions }
        return store.transactions.filter { $0.kind == selectedKind }
    }

    var body: some View {
        NavigationStack {
            Group {
                if visibleTransactions.isEmpty {
                    EmptyLedgerView(
                        title: selectedKind == nil ? "还没有账单" : "这个分类还没有账单",
                        message: "切换筛选条件，或去记一笔。"
                    )
                } else {
                    List {
                        ForEach(groupTransactionsByDay(visibleTransactions)) { group in
                            Section {
                                ForEach(group.items) { item in
                                    Button {
                                        editingTransaction = item
                                    } label: {
                                        TransactionRow(transaction: item)
                                    }
                                    .buttonStyle(.plain)
                                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                        Button("删除", role: .destructive) { pendingDelete = item }
                                        Button("编辑") { editingTransaction = item }
                                            .tint(.fmPrimary)
                                    }
                                }
                            } header: {
                                HStack {
                                    Text(group.day.formatted(.dateTime.month().day().weekday(.abbreviated)))
                                    Spacer()
                                    Text("\(group.items.count) 笔")
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                    .refreshable { store.reloadAll() }
                }
            }
            .navigationTitle("明细")
            .safeAreaInset(edge: .top, spacing: 0) {
                Picker("账单类型", selection: $selectedKind) {
                    Text("全部").tag(TransactionKind?.none)
                    Text("支出").tag(TransactionKind?.some(.expense))
                    Text("收入").tag(TransactionKind?.some(.income))
                    Text("转账").tag(TransactionKind?.some(.transfer))
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 8)
                .background(.bar)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { BookMenu() }
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        SearchView()
                    } label: {
                        Image(systemName: "magnifyingglass")
                    }
                }
            }
            .sheet(item: $editingTransaction) { item in
                ManualEntryView(editing: item) {
                    editingTransaction = nil
                }
            }
            .confirmationDialog(
                "删除这笔账单？",
                isPresented: Binding(
                    get: { pendingDelete != nil },
                    set: { if !$0 { pendingDelete = nil } }
                ),
                titleVisibility: .visible
            ) {
                Button("删除", role: .destructive) {
                    if let pendingDelete { store.deleteTransaction(pendingDelete.id) }
                    pendingDelete = nil
                }
                Button("取消", role: .cancel) { pendingDelete = nil }
            }
        }
    }
}
