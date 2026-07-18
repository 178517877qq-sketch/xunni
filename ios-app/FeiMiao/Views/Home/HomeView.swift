import SwiftUI
import FeiMiaoDomain

struct HomeView: View {
    @EnvironmentObject private var store: AppStore
    let openAdd: () -> Void
    @State private var editingTransaction: LedgerTransaction?

    var body: some View {
        NavigationStack {
            Group {
                if store.transactions.isEmpty {
                    EmptyLedgerView(actionTitle: "记一笔", action: openAdd)
                } else {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            summaryCard
                            recentTransactions
                        }
                        .padding(.horizontal)
                        .padding(.bottom, 24)
                    }
                    .background(Color(.systemGroupedBackground))
                    .refreshable { store.reloadAll() }
                }
            }
            .navigationTitle("肥喵记账")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { BookMenu() }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    NavigationLink {
                        SearchView()
                    } label: {
                        Image(systemName: "magnifyingglass")
                    }
                    Button(action: openAdd) {
                        Image(systemName: "plus")
                    }
                    .accessibilityIdentifier("home-add")
                }
            }
            .sheet(item: $editingTransaction) { item in
                ManualEntryView(editing: item) {
                    editingTransaction = nil
                }
            }
        }
    }

    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(Date.now.formatted(.dateTime.year().month(.wide)))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("本期支出")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(store.summary.expense.yuanText)
                        .font(.system(size: 30, weight: .semibold, design: .rounded))
                        .minimumScaleFactor(0.72)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 5) {
                    Text("收入")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(store.summary.income.yuanText)
                        .font(.headline.monospacedDigit())
                        .foregroundStyle(.fmIncome)
                    Text("结余 \(store.summary.balance.yuanText)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .feiMiaoCard()
    }

    private var recentTransactions: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("最近账单")
                    .font(.headline)
                Spacer()
                Text("最近 \(min(store.transactions.count, 8)) 笔")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 8)

            ForEach(Array(store.transactions.prefix(8).enumerated()), id: \.element.id) { index, item in
                Button {
                    editingTransaction = item
                } label: {
                    TransactionRow(transaction: item)
                        .padding(.vertical, 10)
                }
                .buttonStyle(.plain)
                if index < min(store.transactions.count, 8) - 1 {
                    Divider().padding(.leading, 54)
                }
            }
        }
        .feiMiaoCard()
    }
}
