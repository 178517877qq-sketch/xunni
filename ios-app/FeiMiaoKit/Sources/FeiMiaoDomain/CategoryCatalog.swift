import Foundation

public struct CategorySeed: Hashable, Codable {
    public var key: String
    public var nameZh: String
    public var nameEn: String
    public var emoji: String
    public var kind: TransactionKind
    public var parentKey: String?

    public init(
        _ key: String,
        _ nameZh: String,
        _ nameEn: String,
        _ emoji: String,
        _ kind: TransactionKind,
        parent: String? = nil
    ) {
        self.key = key
        self.nameZh = nameZh
        self.nameEn = nameEn
        self.emoji = emoji
        self.kind = kind
        self.parentKey = parent
    }
}

/// Stable category keys shared with Android DB v40.
public enum CategoryCatalog {
    public static let expenses: [CategorySeed] = [
        .init("dining", "食品餐饮", "Food", "🍜", .expense),
        .init("dining_breakfast", "早餐", "Breakfast", "🍳", .expense, parent: "dining"),
        .init("dining_lunch", "午餐", "Lunch", "🍱", .expense, parent: "dining"),
        .init("dining_dinner", "晚餐", "Dinner", "🍚", .expense, parent: "dining"),
        .init("dining_drink", "饮料酒水", "Drinks", "🧋", .expense, parent: "dining"),
        .init("dining_snack", "休闲零食", "Snacks", "🍿", .expense, parent: "dining"),
        .init("groceries", "生鲜食品", "Groceries", "🥬", .expense, parent: "dining"),
        .init("dining_treat", "请客吃饭", "Treat", "🍻", .expense, parent: "dining"),
        .init("dining_cook", "粮油调味", "Cooking", "🧂", .expense, parent: "dining"),
        .init("dining_tobacco", "烟草", "Tobacco", "🚬", .expense, parent: "dining"),

        .init("shopping", "购物消费", "Shopping", "🛍️", .expense),
        .init("shop_home", "日常家居", "Home", "🛋️", .expense, parent: "shopping"),
        .init("shop_beauty", "个护美妆", "Beauty", "💄", .expense, parent: "shopping"),
        .init("shop_digital", "手机数码", "Digital", "📱", .expense, parent: "shopping"),
        .init("shop_digital_acc", "数码配件", "Accessories", "🎧", .expense, parent: "shopping"),
        .init("subscription", "虚拟充值", "Top-up", "🎟️", .expense, parent: "shopping"),
        .init("shop_appliance", "生活电器", "Appliances", "📺", .expense, parent: "shopping"),
        .init("shop_watch", "配饰腕表", "Accessories", "⌚", .expense, parent: "shopping"),
        .init("shop_jewelry", "珠宝首饰", "Jewelry", "💍", .expense, parent: "shopping"),
        .init("shop_baby", "母婴玩具", "Baby", "🧸", .expense, parent: "shopping"),
        .init("shop_clothes", "服饰运动", "Clothing", "👟", .expense, parent: "shopping"),
        .init("pets", "宠物用品", "Pets", "🐾", .expense, parent: "shopping"),
        .init("shop_office", "办公用品", "Office", "📎", .expense, parent: "shopping"),

        .init("transport", "出行交通", "Transport", "🚌", .expense),
        .init("trans_taxi", "打车", "Taxi", "🚕", .expense, parent: "transport"),
        .init("trans_public", "公共交通", "Transit", "🚌", .expense, parent: "transport"),
        .init("trans_bike", "共享单车", "Bike", "🚲", .expense, parent: "transport"),
        .init("trans_train", "火车", "Train", "🚄", .expense, parent: "transport"),
        .init("trans_flight", "飞机", "Flight", "✈️", .expense, parent: "transport"),

        .init("car", "车辆支出", "Car", "🚗", .expense),
        .init("trans_fuel", "加油", "Fuel", "⛽", .expense, parent: "car"),
        .init("trans_park", "停车费", "Parking", "🅿️", .expense, parent: "car"),
        .init("house_park", "车位费", "Parking Lot", "🚙", .expense, parent: "car"),
        .init("trans_repair", "保养修车", "Car Service", "🔧", .expense, parent: "car"),
        .init("car_toll", "过路过桥", "Toll", "🛣️", .expense, parent: "car"),
        .init("car_wash", "洗车", "Car Wash", "🧼", .expense, parent: "car"),
        .init("car_tax", "车船税年检", "Car Tax", "📋", .expense, parent: "car"),

        .init("entertainment", "休闲娱乐", "Leisure", "🎮", .expense),
        .init("travel", "旅游度假", "Travel", "🧳", .expense, parent: "entertainment"),
        .init("ent_movie", "电影唱歌", "Movie/KTV", "🎤", .expense, parent: "entertainment"),
        .init("ent_sport", "运动健身", "Sports", "🏋️", .expense, parent: "entertainment"),
        .init("ent_spa", "足浴按摩", "Spa", "💆", .expense, parent: "entertainment"),
        .init("ent_game", "棋牌桌游", "Games", "🀄", .expense, parent: "entertainment"),
        .init("ent_bar", "酒吧", "Bar", "🍸", .expense, parent: "entertainment"),
        .init("ent_show", "演出", "Show", "🎭", .expense, parent: "entertainment"),
        .init("ent_photo", "摄影写真", "Photo", "📸", .expense, parent: "entertainment"),

        .init("housing", "居家住房", "Living", "🏠", .expense),
        .init("house_phone", "话费宽带", "Phone/Net", "📶", .expense, parent: "housing"),
        .init("utilities", "电费", "Electricity", "💡", .expense, parent: "housing"),
        .init("house_water", "水费", "Water", "🚰", .expense, parent: "housing"),
        .init("house_gas", "燃气费", "Gas", "🔥", .expense, parent: "housing"),
        .init("house_property", "物业费", "Property", "🏢", .expense, parent: "housing"),
        .init("house_rent", "房租", "Rent", "🏘️", .expense, parent: "housing"),
        .init("house_loan", "房贷利息", "Mortgage", "🏦", .expense, parent: "housing"),
        .init("house_clean", "家政清洁", "Cleaning", "🧹", .expense, parent: "housing"),
        .init("shop_deco", "装修维修", "Decor", "🧰", .expense, parent: "housing"),

        .init("medical", "医疗健康", "Medical", "💊", .expense),
        .init("med_drug", "药品", "Medicine", "💊", .expense, parent: "medical"),
        .init("med_clinic", "门诊挂号", "Clinic", "🩺", .expense, parent: "medical"),
        .init("med_hospital", "住院手术", "Hospital", "🏥", .expense, parent: "medical"),
        .init("med_dental", "牙科", "Dental", "🦷", .expense, parent: "medical"),
        .init("med_eye", "眼科配镜", "Optical", "👓", .expense, parent: "medical"),
        .init("med_mental", "心理咨询", "Mental", "🧠", .expense, parent: "medical"),
        .init("med_beauty", "医美", "Aesthetic", "💉", .expense, parent: "medical"),
        .init("med_health", "保健品", "Supplement", "🌿", .expense, parent: "medical"),
        .init("med_checkup", "体检", "Checkup", "📋", .expense, parent: "medical"),

        .init("education", "教育学习", "Education", "📚", .expense),
        .init("edu_book", "书籍", "Books", "📖", .expense, parent: "education"),
        .init("edu_course", "课程", "Course", "🎓", .expense, parent: "education"),
        .init("edu_tuition", "学费", "Tuition", "🏫", .expense, parent: "education"),
        .init("edu_exam", "考试考证", "Exam", "📝", .expense, parent: "education"),
        .init("edu_print", "文具打印", "Stationery", "🖨️", .expense, parent: "education"),

        .init("insurance", "保险保障", "Insurance", "🛡️", .expense),
        .init("ins_car", "车险", "Car Ins", "🚗", .expense, parent: "insurance"),
        .init("ins_medical", "医疗险", "Medical Ins", "⚕️", .expense, parent: "insurance"),
        .init("ins_critical", "重疾险", "Critical Ins", "🎗️", .expense, parent: "insurance"),
        .init("ins_accident", "意外险", "Accident Ins", "🚑", .expense, parent: "insurance"),
        .init("ins_life", "寿险", "Life Ins", "🕊️", .expense, parent: "insurance"),
        .init("ins_property", "财产险", "Property Ins", "🏠", .expense, parent: "insurance"),
        .init("ins_other", "其他保险", "Other Ins", "📑", .expense, parent: "insurance"),

        .init("gifts", "人情家庭", "Gifts", "🎁", .expense),
        .init("gift_red", "随礼红包", "Gift Money", "🧧", .expense, parent: "gifts"),
        .init("gift_present", "礼物", "Present", "🎀", .expense, parent: "gifts"),
        .init("gift_parents", "孝敬父母", "Parents", "👵", .expense, parent: "gifts"),

        .init("other", "其他", "Other", "📦", .expense),
        .init("other_fine", "罚款赔偿", "Fine", "⚖️", .expense, parent: "other"),
        .init("other_fee", "手续费", "Fee", "🧾", .expense, parent: "other"),
        .init("other_tax", "税费", "Tax", "🏛️", .expense, parent: "other"),
        .init("other_invest", "投资费用", "Invest Fee", "📉", .expense, parent: "other"),
        .init("other_loss", "意外损失", "Loss", "💥", .expense, parent: "other"),
        .init("other_charity", "慈善捐助", "Charity", "❤️", .expense, parent: "other"),
    ]

    public static let incomes: [CategorySeed] = [
        .init("salary", "工资薪酬", "Salary", "💰", .income),
        .init("inc_salary_base", "基本工资", "Base Pay", "💵", .income, parent: "salary"),
        .init("inc_salary_ot", "加班费", "Overtime", "⏰", .income, parent: "salary"),
        .init("inc_salary_allow", "补贴", "Allowance", "🎫", .income, parent: "salary"),
        .init("inc_salary_commission", "提成绩效", "Commission", "📊", .income, parent: "salary"),

        .init("bonus", "奖金奖励", "Bonus", "🏆", .income),
        .init("inc_bonus_year", "年终奖", "Year Bonus", "🧧", .income, parent: "bonus"),
        .init("inc_bonus_project", "项目奖金", "Project Bonus", "🏅", .income, parent: "bonus"),
        .init("inc_bonus_full", "全勤奖", "Attendance", "✅", .income, parent: "bonus"),

        .init("sideline", "副业收入", "Sideline", "💼", .income),
        .init("inc_parttime", "兼职", "Part-time", "🧑‍💻", .income, parent: "sideline"),
        .init("inc_freelance", "自由职业", "Freelance", "🎨", .income, parent: "sideline"),
        .init("inc_media", "自媒体", "Media", "📹", .income, parent: "sideline"),

        .init("investment", "投资理财", "Investment", "📈", .income),
        .init("inc_interest", "利息", "Interest", "🏦", .income, parent: "investment"),
        .init("inc_dividend", "分红", "Dividend", "💹", .income, parent: "investment"),
        .init("inc_gain", "投资收益", "Gain", "📊", .income, parent: "investment"),
        .init("inc_rent", "租金收入", "Rent Income", "🏘️", .income, parent: "investment"),

        .init("pension", "养老金", "Pension", "👴", .income),
        .init("familySupport", "家庭支持", "Family", "👪", .income),
        .init("redPacket", "礼金红包", "Red Packet", "🧧", .income),
        .init("inc_rp_wx", "微信红包", "WeChat RP", "💚", .income, parent: "redPacket"),
        .init("inc_rp_ali", "支付宝红包", "Alipay RP", "💙", .income, parent: "redPacket"),
        .init("inc_rp_gift", "人情红包", "Gift RP", "🧧", .income, parent: "redPacket"),
        .init("business", "经营收入", "Business", "🏪", .income),
        .init("refund", "退款报销", "Refund", "↩️", .income),
        .init("otherIncome", "其他收入", "Other", "💵", .income),
        .init("inc_prize", "中奖收入", "Prize", "🎰", .income, parent: "otherIncome"),
        .init("inc_subsidy", "政府补助", "Subsidy", "🏛️", .income, parent: "otherIncome"),
    ]

    public static let all = expenses + incomes

    public static func seed(for key: String?) -> CategorySeed? {
        guard let key else { return nil }
        return all.first { $0.key == key }
    }

    public static func emoji(for key: String?) -> String {
        seed(for: key)?.emoji ?? "🏷️"
    }
}
