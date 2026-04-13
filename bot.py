from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          ConversationHandler, ContextTypes, filters)
from sheets import (connect_sheets, add_transaction, add_client, add_supplier,
                   get_balance, get_person_balance, get_full_summary,
                   add_person, delete_person, get_last_records, delete_last_record,
                   get_all_clients, get_all_suppliers,
                   get_clients_total, get_suppliers_total,
                   get_all_employees, get_employee_names, add_employee, delete_employee,
                   add_employee_transaction, get_employee_balance,
                   get_all_bands, add_band, delete_band,
                   add_masrof_edari, add_masrof_okhra,
                   get_monthly_band_report, get_monthly_masrof_report,
                   get_weekly_employees_report, get_monthly_khazna_report,
                   get_person_transactions, generate_pdf_report)

TOKEN = "8603771009:AAE46Fv4QEU_tsSGlvnN0kPbD1ojDnZnVCA"
sheet = connect_sheets()

(AMOUNT, DESCRIPTION, NAME, NAME_AMOUNT, NAME_AMOUNT_TYPE, SELECT_RECORD,
 SARF_TYPE, MASROF_TYPE, MWZF_SALARY, MWZF_ACTION,
 MWZF_AMOUNT, OKHRA_AMOUNT, OKHRA_NOTE, MWZF_CONFIRM) = range(14)

# ============ الخزنة ============

async def dakhl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'dakhl'
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 إيه الوصف؟")
        return DESCRIPTION
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس، حاول تاني:")
        return AMOUNT

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    amount = context.user_data['amount']
    add_transaction(sheet, "دخل", amount, description)
    await update.message.reply_text(f"✅ تم تسجيل دخول: {amount} جنيه\n📝 {description}")
    return ConversationHandler.END

async def raseed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = get_balance(sheet)
    emoji = "📈" if balance >= 0 else "📉"
    await update.message.reply_text(f"{emoji} رصيد الخزنة: {balance} جنيه")

# ============ الصرف ============

async def sarf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💸 صرف لمورد"], ["👷 صرف لموظف"], ["📋 مصروفات متنوعة"]]
    await update.message.reply_text("اختار نوع الصرف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return SARF_TYPE

async def get_sarf_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "مورد" in choice:
        names = get_all_suppliers(sheet)
        if not names:
            await update.message.reply_text("❌ مفيش موردين، ضيف مورد الأول بـ /add_mwrd", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME
    elif "موظف" in choice:
        names = get_employee_names(sheet)
        if not names:
            await update.message.reply_text("❌ مفيش موظفين، ضيف موظف الأول بـ /add_mwzf", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwzf_sarf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME
    elif "مصروفات" in choice:
        keyboard = [["📌 مصروفات إدارية"], ["📝 مصروفات أخرى"]]
        await update.message.reply_text("اختار نوع المصروفات:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return MASROF_TYPE
    await update.message.reply_text("❌ اختيار غلط")
    return ConversationHandler.END

async def get_masrof_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "إدارية" in choice:
        bands = get_all_bands(sheet)
        if not bands:
            await update.message.reply_text("❌ مفيش بنود، ضيف بند الأول بـ /add_band", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'masrof_edari'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME
    elif "أخرى" in choice:
        context.user_data['action'] = 'masrof_okhra'
        await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
        return OKHRA_AMOUNT
    await update.message.reply_text("❌ اختيار غلط")
    return ConversationHandler.END

async def get_okhra_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 اكتب نوت عن المصروف:")
        return OKHRA_NOTE
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return OKHRA_AMOUNT

async def get_okhra_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    amount = context.user_data['amount']
    add_masrof_okhra(sheet, amount, note)
    await update.message.reply_text(f"✅ تم تسجيل مصروفات أخرى: {amount} جنيه\n📝 {note}")
    return ConversationHandler.END

# ============ العملاء ============

async def ameel_deen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'ameel_deen'
    if not names:
        await update.message.reply_text("❌ مفيش عملاء، ضيف عميل الأول بـ /add_ameel", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME

async def ameel_dafa3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'ameel_dafa3'
    if not names:
        await update.message.reply_text("❌ مفيش عملاء، ضيف عميل الأول بـ /add_ameel", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    action = context.user_data['action']
    if action == 'mwzf_sarf':
        keyboard = [["💰 مرتب"], ["💳 سلفة"], ["🎁 مكافأة"], ["✂️ خصم"]]
        await update.message.reply_text("اختار نوع الصرف للموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return MWZF_ACTION
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    return NAME_AMOUNT

async def get_name_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        action = context.user_data['action']
        name = context.user_data['name']
        if action == 'ameel_deen':
            add_client(sheet, name, amount, "دين")
            await update.message.reply_text(f"✅ تم تسجيل دين على {name}: {amount} جنيه")
        elif action == 'ameel_dafa3':
            add_client(sheet, name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع من {name}: {amount} جنيه")
        elif action == 'mwrd_dafa3':
            add_supplier(sheet, name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع لـ {name}: {amount} جنيه")
        elif action == 'mwrd_madyoniya':
            add_supplier(sheet, name, amount, "مديونية")
            await update.message.reply_text(f"✅ تم تسجيل مديونية لـ {name}: {amount} جنيه")
        elif action == 'masrof_edari':
            add_masrof_edari(sheet, name, amount)
            await update.message.reply_text(f"✅ تم تسجيل مصروفات إدارية - {name}: {amount} جنيه")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس، حاول تاني:")
        return NAME_AMOUNT

# ============ الموردين ============

async def mwrd_madyoniya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'mwrd_madyoniya'
    if not names:
        await update.message.reply_text("❌ مفيش موردين، ضيف مورد الأول بـ /add_mwrd", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME

async def hesab_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'hesab_ameel'
    if not names:
        await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def hesab_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'hesab_mwrd'
    if not names:
        await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def get_hesab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    action = context.user_data['action']
    if action == 'hesab_ameel':
        b = get_person_balance(sheet, "الخزنة_العملاء", name)
        if b > 0:
            await update.message.reply_text(f"👤 {name}\n💰 عليه: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"👤 {name}\n✅ ليه عندنا: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"👤 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())
    else:
        b = get_person_balance(sheet, "الخزنة_الموردين", name)
        if b > 0:
            await update.message.reply_text(f"🏭 {name}\n💰 ليه عندنا: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"🏭 {name}\n✅ دفعنا له زيادة: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"🏭 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ الإجماليات ============

async def madenoniyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total, details = get_suppliers_total(sheet)
    if not details:
        await update.message.reply_text("✅ مفيش مديونيات على الشركة دلوقتي")
        return
    msg = "💸 *إجمالي المديونيات اللي علينا:*\n\n"
    msg += "\n".join(details)
    msg += f"\n\n*الإجمالي: {total} جنيه*"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def feloos_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total, details = get_clients_total(sheet)
    if not details:
        await update.message.reply_text("📭 مفيش عملاء عندهم فلوس دلوقتي")
        return
    msg = "💰 *إجمالي الفلوس اللي للعملاء عندنا:*\n\n"
    msg += "\n".join(details)
    msg += f"\n\n*الإجمالي: {total} جنيه*"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ التقارير ============

async def taqrir_band(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bands = get_all_bands(sheet)
    context.user_data['action'] = 'taqrir_band'
    if not bands:
        await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[band] for band in bands]
    await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def taqrir_masrof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bands, okhra = get_monthly_masrof_report(sheet)
    month = date.today().strftime("%Y-%m")
    if not bands and okhra == 0:
        await update.message.reply_text("📭 مفيش مصروفات الشهر ده")
        return
    msg = f"📋 *تقرير المصروفات - {month}*\n\n"
    total = 0
    if bands:
        msg += "📌 *إدارية:*\n"
        for band, amount in bands.items():
            msg += f"  • {band}: {amount} جنيه\n"
            total += amount
    if okhra > 0:
        msg += f"\n📝 *أخرى:* {okhra} جنيه\n"
        total += okhra
    msg += f"\n💰 *الإجمالي: {total} جنيه*"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def taqrir_mwzfeen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = get_weekly_employees_report(sheet)
    if not report:
        await update.message.reply_text("📭 مفيش موظفين")
        return
    msg = "👷 *تقرير الموظفين الأسبوعي*\n\n"
    for emp in report:
        d = emp['data']
        msg += f"*{emp['name']}*\n"
        msg += f"  💰 المرتب: {d['salary']} | 🎁 مكافآت: {d['bonuses']}\n"
        msg += f"  💳 سلف: {d['advances']} | ✂️ خصم: {d['deductions']}\n"
        msg += f"  💵 الصافي المتبقي: {d['net']} جنيه\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def taqrir_khazna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_in, total_out = get_monthly_khazna_report(sheet)
    month = date.today().strftime("%Y-%m")
    net = total_in - total_out
    emoji = "📈" if net >= 0 else "📉"
    msg = (f"🏦 *تقرير الخزنة - {month}*\n\n"
           f"💚 إجمالي الدخل: {total_in} جنيه\n"
           f"🔴 إجمالي الصرف: {total_out} جنيه\n"
           f"{emoji} *الصافي: {net} جنيه*")
    await update.message.reply_text(msg, parse_mode='Markdown')

async def taqrir_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'taqrir_ameel'
    if not names:
        await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def taqrir_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'taqrir_mwrd'
    if not names:
        await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

# ============ الموظفين ============

async def add_mwzf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👷 اسم الموظف الجديد؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'add_mwzf'
    return NAME_AMOUNT_TYPE

async def get_mwzf_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        salary = float(update.message.text)
        name = context.user_data['name']
        result = add_employee(sheet, name, salary)
        if result:
            await update.message.reply_text(f"✅ تم إضافة موظف: {name}\n💰 المرتب الأسبوعي: {salary} جنيه")
        else:
            await update.message.reply_text(f"⚠️ الموظف {name} موجود بالفعل")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return MWZF_SALARY

async def get_mwzf_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    type_map = {"مرتب": "مرتب", "سلفة": "سلفة", "مكافأة": "مكافأة", "خصم": "خصم"}
    mwzf_type = next((v for k, v in type_map.items() if k in choice), None)
    if not mwzf_type:
        await update.message.reply_text("❌ اختيار غلط")
        return ConversationHandler.END
    context.user_data['mwzf_type'] = mwzf_type
    name = context.user_data['name']
    if mwzf_type == "مرتب":
        data = get_employee_balance(sheet, name)
        if data:
            net = data['net']
            if net <= 0:
                await update.message.reply_text(
                    f"⚠️ {name} مفيش مرتب متبقي!\n"
                    f"المرتب الأسبوعي: {data['salary']} جنيه\n"
                    f"سلف: {data['advances']} جنيه\n"
                    f"خصومات: {data['deductions']} جنيه\n"
                    f"الباقي: {net} جنيه",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
            context.user_data['mwzf_net'] = net
            keyboard = [["✅ تأكيد"], ["❌ إلغاء"]]
            await update.message.reply_text(
                f"👷 *{name}*\n\n"
                f"💰 المرتب الأسبوعي: {data['salary']} جنيه\n"
                f"🎁 مكافآت: {data['bonuses']} جنيه\n"
                f"💳 سلف: {data['advances']} جنيه\n"
                f"✂️ خصومات: {data['deductions']} جنيه\n"
                f"✅ تم صرف: {data['total_paid']} جنيه\n\n"
                f"💵 *الباقي: {net} جنيه*\n\nتأكيد الصرف؟",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return MWZF_CONFIRM
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    return MWZF_AMOUNT

async def get_mwzf_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    name = context.user_data['name']
    net = context.user_data['mwzf_net']
    if "تأكيد" in choice:
        add_employee_transaction(sheet, name, "مرتب", net)
        await update.message.reply_text(f"✅ تم صرف مرتب {name}: {net} جنيه", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def get_mwzf_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        name = context.user_data['name']
        mwzf_type = context.user_data['mwzf_type']
        add_employee_transaction(sheet, name, mwzf_type, amount)
        await update.message.reply_text(f"✅ تم تسجيل {mwzf_type} لـ {name}: {amount} جنيه")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return MWZF_AMOUNT

async def hesab_mwzf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_employee_names(sheet)
    context.user_data['action'] = 'hesab_mwzf'
    if not names:
        await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def del_mwzf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_employee_names(sheet)
    context.user_data['action'] = 'del_mwzf'
    if not names:
        await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👷 اختار الموظف اللي عايز تحذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

# ============ البنود ============

async def add_band_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 اسم البند الجديد؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'add_band'
    return NAME_AMOUNT_TYPE

async def del_band_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bands = get_all_bands(sheet)
    context.user_data['action'] = 'del_band'
    if not bands:
        await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[band] for band in bands]
    await update.message.reply_text("📌 اختار البند اللي عايز تحذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

# ============ إضافة وحذف عميل/مورد ============

async def add_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 اسم العميل الجديد؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'add_ameel'
    return NAME_AMOUNT_TYPE

async def add_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏭 اسم المورد الجديد؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'add_mwrd'
    return NAME_AMOUNT_TYPE

async def del_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'del_ameel'
    if not names:
        await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("👤 اختار العميل اللي عايز تحذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def del_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'del_mwrd'
    if not names:
        await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    keyboard = [[name] for name in names]
    await update.message.reply_text("🏭 اختار المورد اللي عايز تحذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

# ============ الفانكشن الرئيسية ============

async def get_hesab_or_add_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    name = update.message.text

    if action == 'add_ameel':
        result = add_person(sheet, name, "عميل")
        msg = f"✅ تم إضافة عميل: {name}" if result else f"⚠️ العميل {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwrd':
        result = add_person(sheet, name, "مورد")
        msg = f"✅ تم إضافة مورد: {name}" if result else f"⚠️ المورد {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_ameel':
        result = delete_person(sheet, name, "عميل")
        msg = f"✅ تم حذف العميل: {name}" if result else f"⚠️ العميل {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_mwrd':
        result = delete_person(sheet, name, "مورد")
        msg = f"✅ تم حذف المورد: {name}" if result else f"⚠️ المورد {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwzf':
        context.user_data['name'] = name
        await update.message.reply_text("💰 المرتب الأسبوعي؟")
        return MWZF_SALARY

    elif action == 'hesab_mwzf':
        data = get_employee_balance(sheet, name)
        if not data:
            await update.message.reply_text("❌ مش لاقي بيانات", reply_markup=ReplyKeyboardRemove())
        else:
            msg = (f"👷 *{name}*\n\n"
                   f"💰 المرتب الأسبوعي: {data['salary']} جنيه\n"
                   f"🎁 مكافآت: {data['bonuses']} جنيه\n"
                   f"💳 سلف: {data['advances']} جنيه\n"
                   f"✂️ خصومات: {data['deductions']} جنيه\n"
                   f"✅ تم صرف: {data['total_paid']} جنيه\n\n"
                   f"💵 *الصافي المتبقي: {data['net']} جنيه*")
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

    elif action == 'del_mwzf':
        result = delete_employee(sheet, name)
        msg = f"✅ تم حذف الموظف: {name}" if result else f"⚠️ الموظف {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_band':
        result = add_band(sheet, name)
        msg = f"✅ تم إضافة البند: {name}" if result else f"⚠️ البند {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_band':
        result = delete_band(sheet, name)
        msg = f"✅ تم حذف البند: {name}" if result else f"⚠️ البند {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'taqrir_band':
        from datetime import date
        total, details = get_monthly_band_report(sheet, name)
        month = date.today().strftime("%Y-%m")
        if not details:
            await update.message.reply_text(f"📭 مفيش مصروفات لبند {name} الشهر ده", reply_markup=ReplyKeyboardRemove())
        else:
            msg = f"📌 *تقرير {name} - {month}*\n\n"
            for d in details:
                msg += f"  • {d['date']} : {d['amount']} جنيه\n"
            msg += f"\n💰 *الإجمالي: {total} جنيه*"
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

    elif action in ['taqrir_ameel', 'taqrir_mwrd']:
        person_type = "عميل" if action == 'taqrir_ameel' else "مورد"
        transactions = get_person_transactions(sheet, name, person_type)
        if not transactions:
            await update.message.reply_text(f"📭 مفيش حركات لـ {name}", reply_markup=ReplyKeyboardRemove())
        else:
            balance = get_person_balance(
                sheet,
                "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين",
                name
            )
            await update.message.reply_text("⏳ جاري إنشاء التقرير...", reply_markup=ReplyKeyboardRemove())
            try:
                pdf_path = generate_pdf_report(name, person_type, transactions, balance)
                with open(pdf_path, 'rb') as f:
                    await update.message.reply_document(f, filename=f"تقرير_{name}.pdf")
                import os
                os.unlink(pdf_path)
            except Exception as e:
                await update.message.reply_text(f"❌ حصل خطأ في إنشاء PDF: {str(e)}")

    elif action == 'del_record_confirm':
        return await confirm_delete_record(update, context)

    else:
        return await get_hesab(update, context)

    return ConversationHandler.END

# ============ حذف حركة ============

async def del_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🏦 الخزنة"], ["👥 العملاء"], ["🏭 الموردين"]]
    await update.message.reply_text("اختار من أي شيت عايز تمسح؟", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return SELECT_RECORD

async def select_sheet_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "الخزنة" in choice:
        worksheet = "الخزنة"
    elif "العملاء" in choice:
        worksheet = "الخزنة_العملاء"
    elif "الموردين" in choice:
        worksheet = "الخزنة_الموردين"
    else:
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    context.user_data['del_worksheet'] = worksheet
    records = get_last_records(sheet, worksheet)
    if not records:
        await update.message.reply_text("❌ مفيش حركات", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    msg = "اختار رقم الحركة اللي عايز تمسحها:\n\n"
    for i, r in enumerate(records):
        if worksheet == "الخزنة":
            msg += f"{i+1}. {r['التاريخ']} | {r['النوع']} | {r['المبلغ']} | {r['الوصف']}\n"
        else:
            msg += f"{i+1}. {r['التاريخ']} | {r['الاسم']} | {r['النوع']} | {r['المبلغ']}\n"
    context.user_data['del_records'] = records
    context.user_data['action'] = 'del_record_confirm'
    keyboard = [[str(i+1) for i in range(len(records))]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def confirm_delete_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        choice = int(update.message.text) - 1
        records = context.user_data['del_records']
        worksheet = context.user_data['del_worksheet']
        ws_records = sheet.worksheet(worksheet).get_all_records()
        target = records[choice]
        for i, row in enumerate(ws_records):
            if row == target:
                delete_last_record(sheet, worksheet, i)
                await update.message.reply_text("✅ تم حذف الحركة", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        await update.message.reply_text("❌ مش لاقي الحركة دي", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def malakhas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_full_summary(sheet)
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ تشغيل البوت ============

app = ApplicationBuilder().token(TOKEN).build()

entry_points_list = [
    CommandHandler("dakhl", dakhl),
    CommandHandler("sarf", sarf),
    CommandHandler("ameel_deen", ameel_deen),
    CommandHandler("ameel_dafa3", ameel_dafa3),
    CommandHandler("mwrd_madyoniya", mwrd_madyoniya),
    CommandHandler("hesab_ameel", hesab_ameel),
    CommandHandler("hesab_mwrd", hesab_mwrd),
    CommandHandler("add_ameel", add_ameel),
    CommandHandler("add_mwrd", add_mwrd),
    CommandHandler("del_ameel", del_ameel),
    CommandHandler("del_mwrd", del_mwrd),
    CommandHandler("del_record", del_record),
    CommandHandler("add_mwzf", add_mwzf),
    CommandHandler("del_mwzf", del_mwzf),
    CommandHandler("hesab_mwzf", hesab_mwzf),
    CommandHandler("add_band", add_band_cmd),
    CommandHandler("del_band", del_band_cmd),
    CommandHandler("taqrir_band", taqrir_band),
    CommandHandler("taqrir_ameel", taqrir_ameel),
    CommandHandler("taqrir_mwrd", taqrir_mwrd),
]

conv_handler = ConversationHandler(
    entry_points=entry_points_list,
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        NAME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_amount)],
        NAME_AMOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hesab_or_add_del)],
        SELECT_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_sheet_to_delete)],
        SARF_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sarf_type)],
        MASROF_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_masrof_type)],
        MWZF_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_salary)],
        MWZF_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_action)],
        MWZF_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_amount)],
        MWZF_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_confirm)],
        OKHRA_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_okhra_amount)],
        OKHRA_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_okhra_note)],
    },
    fallbacks=entry_points_list + [CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("raseed", raseed))
app.add_handler(CommandHandler("malakhas", malakhas))
app.add_handler(CommandHandler("madenoniyat", madenoniyat))
app.add_handler(CommandHandler("feloos_ameel", feloos_ameel))
app.add_handler(CommandHandler("taqrir_masrof", taqrir_masrof))
app.add_handler(CommandHandler("taqrir_mwzfeen", taqrir_mwzfeen))
app.add_handler(CommandHandler("taqrir_khazna", taqrir_khazna))

print("✅ البوت شغال!")
app.run_polling()