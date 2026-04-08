from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          ConversationHandler, ContextTypes, filters)
from sheets import (connect_sheets, add_transaction, add_client, add_supplier,
                   get_balance, get_person_balance, get_full_summary,
                   add_person, delete_person, get_last_records, 
                   delete_last_record, get_all_clients, get_all_suppliers)

TOKEN = "8603771009:AAE46Fv4QEU_tsSGlvnN0kPbD1ojDnZnVCA"
sheet = connect_sheets()

# مراحل المحادثة
AMOUNT, DESCRIPTION, NAME, NAME_AMOUNT, NAME_AMOUNT_TYPE , SELECT_RECORD= range(6)

# ============ الخزنة ============

async def dakhl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'dakhl'
    return AMOUNT

async def sarf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'sarf'
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
    action = context.user_data['action']
    
    if action == 'dakhl':
        add_transaction(sheet, "دخل", amount, description)
        await update.message.reply_text(f"✅ تم تسجيل دخول: {amount} جنيه\n📝 {description}")
    else:
        add_transaction(sheet, "صرف", amount, description)
        await update.message.reply_text(f"✅ تم تسجيل صرف: {amount} جنيه\n📝 {description}")
    
    return ConversationHandler.END

# ============ العملاء ============

async def ameel_deen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'ameel_deen'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("👤 اختار العميل:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👤 اسم العميل؟", reply_markup=ReplyKeyboardRemove())
    return NAME

async def ameel_dafa3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'ameel_dafa3'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("👤 اختار العميل:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👤 اسم العميل؟", reply_markup=ReplyKeyboardRemove())
    return NAME

# ============ الموردين ============

async def mwrd_madyoniya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'mwrd_madyoniya'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏭 اسم المورد؟", reply_markup=ReplyKeyboardRemove())
    return NAME

async def mwrd_dafa3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'mwrd_dafa3'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏭 اسم المورد؟", reply_markup=ReplyKeyboardRemove())
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("💰 كام المبلغ؟")
    return NAME_AMOUNT

async def get_name_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        action = context.user_data['action']
        name = context.user_data['name']

        if action == 'ameel_deen':
            add_client(sheet, name, amount, "دين")
            await update.message.reply_text(f"✅ تم تسجيل دين على {name}: {amount} جنيه")
        elif action == 'ameel_dafa3':
            add_client(sheet, name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع من {name}: {amount} جنيه")
        elif action == 'mwrd_madyoniya':
            add_supplier(sheet, name, amount, "مديونية")
            await update.message.reply_text(f"✅ تم تسجيل مديونية لـ {name}: {amount} جنيه")
        elif action == 'mwrd_dafa3':
            add_supplier(sheet, name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع لـ {name}: {amount} جنيه")

        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس، حاول تاني:")
        return NAME_AMOUNT

# ============ الاستعلام ============

async def raseed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = get_balance(sheet)
    emoji = "📈" if balance >= 0 else "📉"
    await update.message.reply_text(f"{emoji} رصيد الخزنة: {balance} جنيه")

async def hesab_ameel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_clients(sheet)
    context.user_data['action'] = 'hesab_ameel'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("👤 اختار العميل:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👤 اسم العميل؟", reply_markup=ReplyKeyboardRemove())
    return NAME_AMOUNT_TYPE

async def hesab_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = get_all_suppliers(sheet)
    context.user_data['action'] = 'hesab_mwrd'
    if names:
        keyboard = [[name] for name in names]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏭 اسم المورد؟", reply_markup=ReplyKeyboardRemove())
    return NAME_AMOUNT_TYPE

async def get_hesab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    action = context.user_data['action']

    if action == 'hesab_ameel':
        balance = get_person_balance(sheet, "الخزنة_العملاء", name)
        if balance > 0:
            await update.message.reply_text(f"👤 {name}\n💰 عليه: {balance} جنيه")
        elif balance < 0:
            await update.message.reply_text(f"👤 {name}\n✅ ليه عندنا: {abs(balance)} جنيه")
        else:
            await update.message.reply_text(f"👤 {name}\n✅ حسابه صفر")
    else:
        balance = get_person_balance(sheet, "الخزنة_الموردين", name)
        if balance > 0:
            await update.message.reply_text(f"🏭 {name}\n💰 عليه: {balance} جنيه")
        elif balance < 0:
            await update.message.reply_text(f"🏭 {name}\n✅ ليه عندنا: {abs(balance)} جنيه")
        else:
            await update.message.reply_text(f"🏭 {name}\n✅ حسابه صفر")

    return ConversationHandler.END

async def malakhas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_full_summary(sheet)
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
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
    await update.message.reply_text("👤 اسم العميل اللي عايز تحذفه؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'del_ameel'
    return NAME_AMOUNT_TYPE

async def del_mwrd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏭 اسم المورد اللي عايز تحذفه؟", reply_markup=ReplyKeyboardRemove())
    context.user_data['action'] = 'del_mwrd'
    return NAME_AMOUNT_TYPE

async def handle_add_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    action = context.user_data['action']

    if action == 'add_ameel':
        result = add_person(sheet, name, "عميل")
        if result:
            await update.message.reply_text(f"✅ تم إضافة عميل جديد: {name}")
        else:
            await update.message.reply_text(f"⚠️ العميل {name} موجود بالفعل")

    elif action == 'add_mwrd':
        result = add_person(sheet, name, "مورد")
        if result:
            await update.message.reply_text(f"✅ تم إضافة مورد جديد: {name}")
        else:
            await update.message.reply_text(f"⚠️ المورد {name} موجود بالفعل")

    elif action == 'del_ameel':
        result = delete_person(sheet, name, "عميل")
        if result:
            await update.message.reply_text(f"✅ تم حذف العميل: {name}")
        else:
            await update.message.reply_text(f"⚠️ العميل {name} مش موجود")

    elif action == 'del_mwrd':
        result = delete_person(sheet, name, "مورد")
        if result:
            await update.message.reply_text(f"✅ تم حذف المورد: {name}")
        else:
            await update.message.reply_text(f"⚠️ المورد {name} مش موجود")

    return ConversationHandler.END
async def get_hesab_or_add_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    if action in ['add_ameel', 'add_mwrd', 'del_ameel', 'del_mwrd']:
        return await handle_add_del(update, context)
    elif action == 'del_record_confirm':
        return await confirm_delete_record(update, context)
    else:
        return await get_hesab(update, context)
# ============ delete ============    
async def del_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🏦 الخزنة"],
        ["👥 العملاء"],
        ["🏭 الموردين"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("اختار من أي شيت عايز تمسح؟", reply_markup=reply_markup)
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
        await update.message.reply_text("❌ اختيار غلط")
        return ConversationHandler.END

    context.user_data['del_worksheet'] = worksheet
    records = get_last_records(sheet, worksheet)
    
    if not records:
        await update.message.reply_text("❌ مفيش حركات")
        return ConversationHandler.END

    msg = "اختار رقم الحركة اللي عايز تمسحها:\n\n"
    for i, r in enumerate(records):
        if worksheet == "الخزنة":
            msg += f"{i+1}. {r['التاريخ']} | {r['النوع']} | {r['المبلغ']} | {r['الوصف']}\n"
        else:
            msg += f"{i+1}. {r['التاريخ']} | {r['الاسم']} | {r['النوع']} | {r['المبلغ']}\n"

    context.user_data['del_records'] = records
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
        
        # إيجاد الصف الحقيقي في الشيت
        for i, row in enumerate(ws_records):
            if row == target:
                delete_last_record(sheet, worksheet, i)
                await update.message.reply_text("✅ تم حذف الحركة", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        
        await update.message.reply_text("❌ مش لاقي الحركة دي")
    except:
        await update.message.reply_text("❌ اختيار غلط")
    
    return ConversationHandler.END    
# ============ تشغيل البوت ============

app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("dakhl", dakhl),
        CommandHandler("sarf", sarf),
        CommandHandler("ameel_deen", ameel_deen),
        CommandHandler("ameel_dafa3", ameel_dafa3),
        CommandHandler("mwrd_madyoniya", mwrd_madyoniya),
        CommandHandler("mwrd_dafa3", mwrd_dafa3),
        CommandHandler("hesab_ameel", hesab_ameel),
        CommandHandler("hesab_mwrd", hesab_mwrd),
        CommandHandler("add_ameel", add_ameel),
        CommandHandler("add_mwrd", add_mwrd),
        CommandHandler("del_ameel", del_ameel),
        CommandHandler("del_mwrd", del_mwrd),
        CommandHandler("del_record", del_record),
    ],
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        NAME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_amount)],
        NAME_AMOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hesab_or_add_del)],
        SELECT_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_sheet_to_delete)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("raseed", raseed))
app.add_handler(CommandHandler("malakhas", malakhas))

print("✅ البوت شغال!")
app.run_polling()