import SwiftUI
import FeiMiaoDomain

struct HomeView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.colorScheme) private var colorScheme

    let openDrawer: () -> Void
    let openAdd: () -> Void

    @State private var filter = HomeTransactionFilter.all
    @State private var editingTransaction: LedgerTransaction?
    @State private var showingMonthPicker = false

    private var filteredTransactions: [LedgerTransaction] {
        switch filter {
        case .all:
            store.homeTransactions
        case .expense:
            store.homeTransactions.filter { $0.kind == .expense }
        case .income:
            store.homeTransactions.filter { $0.kind == .income }
        }
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            FeiMiaoPageBackground()
                .ignoresSafeArea()

            ScrollView {
                LazyVStack(spacing: 0) {
                    homeToolbar

                    HomeSummaryCard(
                        month: store.selectedHomeMonth,
                        summary: store.homeSummary,
                        canAdvanceMonth: store.canAdvanceHomeMonth,
                        onPreviousMonth: { store.stepHomeMonth(by: -1) },
                        onNextMonth: { store.stepHomeMonth(by: 1) },
                        onChooseMonth: { showingMonthPicker = true },
                        onReturnToCurrentMonth: { store.resetHomeMonthToCurrent() }
                    )

                    HomeTransactionFilterControl(selection: $filter)

                    if filteredTransactions.isEmpty {
                        HomeEmptyState(
                            isFirstUse: store.isReady && !store.hasAnyTransactions,
                            isLoading: store.isHomeLoading || !store.isReady,
                            selectedFilter: filter
                        )
                    } else {
                        LazyVStack(spacing: 0) {
                            ForEach(groupTransactionsByDay(filteredTransactions)) { group in
                                TransactionDayCard(
                                    group: group,
                                    netAmount: { store.netAmount(forHomeTransaction: $0) },
                                    onSelect: { editingTransaction = $0 }
                                )
                            }
                        }
                    }
                }
                .padding(.bottom, 154)
            }
            .scrollIndicators(.hidden)
            .refreshable { store.reloadAll() }

            bottomEntryOverlay
        }
        .toolbar(.hidden, for: .navigationBar)
        .sheet(item: $editingTransaction) { item in
            ManualEntryView(editing: item) {
                editingTransaction = nil
            }
        }
        .sheet(isPresented: $showingMonthPicker) {
            HomeMonthPickerSheet(
                selectedMonth: store.selectedHomeMonth,
                onSelect: { store.setSelectedHomeMonth($0) }
            )
        }
        .accessibilityIdentifier("home-screen")
    }

    private var homeToolbar: some View {
        HStack(spacing: 10) {
            HomeMenuButton(action: openDrawer)

            Spacer(minLength: 4)
            NavigationLink {
                SearchView()
            } label: {
                HomeCircleButtonLabel(
                    systemImage: "magnifyingglass",
                    accessibilityLabel: "搜索"
                )
            }
            .buttonStyle(.feiMiaoPressable)
            .accessibilityIdentifier("home-search")

            BookMenu()
        }
        .frame(height: 48)
        .padding(.horizontal, 16)
        .padding(.top, 4)
    }

    private var bottomEntryOverlay: some View {
        VStack(spacing: 0) {
            LinearGradient(
                colors: [
                    bottomFadeColor.opacity(0),
                    bottomFadeColor.opacity(0.86),
                    bottomFadeColor,
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .frame(height: 52)
            .allowsHitTesting(false)

            HomeRecordInputBar(openManualEntry: openAdd)
                .allowsHitTesting(store.isReady)
                .padding(.horizontal, 12)
                .padding(.bottom, 6)
                .background(bottomFadeColor)
        }
    }

    private var bottomFadeColor: Color {
        colorScheme == .dark ? .fmPageBase : .fmPageBottom
    }
}

enum HomeTransactionFilter: String, CaseIterable, Identifiable {
    case all = "全部"
    case expense = "支出"
    case income = "收入"

    var id: Self { self }
}

private struct HomeEmptyState: View {
    let isFirstUse: Bool
    let isLoading: Bool
    let selectedFilter: HomeTransactionFilter

    var body: some View {
        VStack(spacing: 8) {
            if isLoading {
                ProgressView()
                    .tint(.fmPrimary)
                    .frame(width: 184, height: 184)
                    .accessibilityLabel("正在读取本月账单")
            } else {
                MascotView(mood: .empty, size: 184, animated: true)
            }
            if !isLoading && isFirstUse {
                Text("点下面的输入框，记下第一笔试试喵")
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(Color.fmSecondaryText)
            } else if !isLoading && selectedFilter != .all {
                Text("这个月还没有\(selectedFilter.rawValue)记录")
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(Color.fmHintText)
            }
        }
        .frame(maxWidth: .infinity)
        .frame(minHeight: 270)
        .padding(.horizontal, 24)
        .accessibilityElement(children: .combine)
    }
}

private struct HomeMenuButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 3) {
                menuLine(width: 16)
                menuLine(width: 16)
                menuLine(width: 8)
            }
            .frame(width: 38, height: 38)
            .background(Color.fmCard, in: Circle())
            .overlay { Circle().stroke(Color.fmHairline, lineWidth: 0.5) }
            .shadow(color: Color.black.opacity(0.035), radius: 7, y: 2)
            .contentShape(Circle())
        }
        .buttonStyle(.feiMiaoPressable)
        .accessibilityLabel("打开菜单")
    }

    private func menuLine(width: CGFloat) -> some View {
        Capsule()
            .fill(Color.primary.opacity(0.70))
            .frame(width: width, height: 1.5)
    }
}

struct HomeCircleButtonLabel: View {
    let systemImage: String
    let accessibilityLabel: String

    var body: some View {
        Image(systemName: systemImage)
            .font(.system(size: 17, weight: .medium))
            .foregroundStyle(Color.primary.opacity(0.76))
            .frame(width: 38, height: 38)
            .background(Color.fmCard, in: Circle())
            .overlay {
                Circle().stroke(Color.fmHairline, lineWidth: 0.5)
            }
            .shadow(color: Color.black.opacity(0.035), radius: 7, y: 2)
            .contentShape(Circle())
            .accessibilityLabel(accessibilityLabel)
    }
}

private struct HomeMonthPickerSheet: View {
    @Environment(\.dismiss) private var dismiss

    let selectedMonth: Date
    let onSelect: (Date) -> Void

    @State private var displayedYear: Int

    private let calendar = Calendar.current
    private let columns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 3)

    init(selectedMonth: Date, onSelect: @escaping (Date) -> Void) {
        self.selectedMonth = selectedMonth
        self.onSelect = onSelect
        _displayedYear = State(initialValue: Calendar.current.component(.year, from: selectedMonth))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 14) {
                HStack {
                    Button { displayedYear -= 1 } label: {
                        Image(systemName: "chevron.left")
                            .frame(width: 36, height: 36)
                    }
                    Spacer()
                    Text("\(displayedYear)年")
                        .font(.system(size: 17, weight: .medium))
                    Spacer()
                    Button { displayedYear += 1 } label: {
                        Image(systemName: "chevron.right")
                            .frame(width: 36, height: 36)
                    }
                    .disabled(displayedYear >= calendar.component(.year, from: .now))
                }

                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(1...12, id: \.self) { month in
                        monthButton(month)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
            .background(FeiMiaoPageBackground().ignoresSafeArea())
            .navigationTitle("选择月份")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("回到本月") {
                        onSelect(.now)
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium])
        .presentationDragIndicator(.hidden)
    }

    private func monthButton(_ month: Int) -> some View {
        let candidate = calendar.date(from: DateComponents(year: displayedYear, month: month, day: 1)) ?? .now
        let selected = calendar.component(.year, from: selectedMonth) == displayedYear
            && calendar.component(.month, from: selectedMonth) == month
        let isFuture = candidate > startOfCurrentMonth

        return Button {
            onSelect(candidate)
            dismiss()
        } label: {
            Text("\(month)月")
                .font(.system(size: 14, weight: selected ? .semibold : .regular))
                .foregroundStyle(selected ? Color.primary : Color.primary.opacity(isFuture ? 0.28 : 0.72))
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(selected ? Color.fmSelectedCard : Color.fmCard)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .stroke(selected ? Color.fmPrimary.opacity(0.38) : Color.fmHairline, lineWidth: 0.5)
                }
        }
        .buttonStyle(.feiMiaoPressable)
        .disabled(isFuture)
    }

    private var startOfCurrentMonth: Date {
        calendar.date(from: calendar.dateComponents([.year, .month], from: .now)) ?? .now
    }
}
