from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          ConversationHandler, ContextTypes, filters)
from telegram.error import Conflict
from datetime import date, datetime, timedelta
from database import (init_db, add_transaction, add_client, add_supplier,
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
                   get_person_transactions, generate_pdf_report,
                   get_daily_khazna_report,
                   get_user_company_id, get_user_companies_by_telegram, add_company, get_all_companies,
                   add_user_account, remove_user_account, link_telegram_to_user, get_company_users, update_user_password)
import os
import re

def normalize_text(text):
    if not text:
        return text
    return text.replace('١','1').replace('٢','2').replace('٣','3').replace('٤','4').replace('٥','5').replace('٦','6').replace('٧','7').replace('٨','8').replace('٩','9').replace('٠','0')

def parse_amount(text):
    text = normalize_text(text)
    text = text.replace(',', '.')
    match = re.search(r'[-+]?\d*\.?\d+', text)
    if match:
        return float(match.group())
    raise ValueError("Invalid number format")

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is required")

ADMIN_ID = os.environ.get("ADMIN_ID")

print("=" * 60)
print("🚀 تشغيل البوت")
print(f"📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

init_db()

(MAIN_ACTION, AMOUNT, DESCRIPTION, NAME, NAME_AMOUNT, NAME_AMOUNT_TYPE,
 SELECT_RECORD, SARF_TYPE, MASROF_TYPE, MWZF_SALARY, MWZF_ACTION,
 MWZF_AMOUNT, OKHRA_AMOUNT, OKHRA_NOTE, MWZF_CONFIRM, DAY_SELECT) = range(16)

# ============ Middleware ============

async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    telegram_id = update.effective_user.id
    companies = get_user_companies_by_telegram(telegram_id)
    if not companies:
        if str(telegram_id) != str(ADMIN_ID):
            await update.message.reply_text("🚫 حسابك مش مربوط بأي شركة. ابعت كلمة المرور (الباسورد) اللي خدتها من الإدارة عشان يتفعل:", reply_markup=ReplyKeyboardRemove())
        return None

    current_company_id = context.user_data.get('company_id')
    allowed_ids = {c['id'] for c in companies}
    if current_company_id in allowed_ids:
        return current_company_id

    if len(companies) == 1:
        context.user_data['company_id'] = companies[0]['id']
        context.user_data['company_name'] = companies[0]['name']
        return companies[0]['id']

    await ask_user_to_select_company(update, context, companies)
    return None

async def ask_user_to_select_company(update: Update, context: ContextTypes.DEFAULT_TYPE, companies):
    context.user_data['awaiting_company_selection'] = True
    context.user_data['company_options'] = {c['name']: c['id'] for c in companies}
    keyboard = [[c['name']] for c in companies]
    await update.message.reply_text(
        "🏢 عندك أكتر من شركة. اختار الشركة اللي هتشتغل عليها:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

async def select_company_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    companies = get_user_companies_by_telegram(telegram_id)
    if not companies:
        await update.message.reply_text("🚫 حسابك مش مربوط بأي شركة. ابعت الباسورد هنا عشان الربط.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if len(companies) == 1:
        context.user_data['company_id'] = companies[0]['id']
        context.user_data['company_name'] = companies[0]['name']
        await update.message.reply_text(f"✅ شركتك الحالية: {companies[0]['name']}", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    await ask_user_to_select_company(update, context, companies)
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    if str(telegram_id) == str(ADMIN_ID):
        await update.message.reply_text("👑 أهلاً بيك يا أدمن! استخدم /admin لفتح لوحة التحكم.")
    companies = get_user_companies_by_telegram(telegram_id)
    if companies:
        if len(companies) == 1:
            context.user_data['company_id'] = companies[0]['id']
            context.user_data['company_name'] = companies[0]['name']
            await update.message.reply_text("👋 أهلاً بيك! حسابك متسجل وجاهز.\nاضغط على الأوامر عشان تبدأ:\n/3mlaa - العملاء\n/mwrdeen - الموردين\n/mwzfeen - الموظفين\n/dakhl - الدخل\n/sarf - الصرف\n/taqarir - التقارير\n/eedadat - الإعدادات\n/company - تغيير الشركة")
        else:
            await ask_user_to_select_company(update, context, companies)
    else:
        await update.message.reply_text("🚫 حسابك مش مربوط. ابعت كلمة المرور (الباسورد) اللي خدتها من الإدارة هنا:")

async def handle_unlinked_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = normalize_text(update.message.text)

    if context.user_data.get('awaiting_company_selection'):
        options = context.user_data.get('company_options', {})
        company_id = options.get(text)
        if not company_id:
            await update.message.reply_text("❌ اختيار غير صحيح. اختار شركة من الأزرار المعروضة.")
            return ConversationHandler.END
        context.user_data['company_id'] = company_id
        context.user_data['company_name'] = text
        context.user_data['awaiting_company_selection'] = False
        context.user_data.pop('company_options', None)
        await update.message.reply_text(f"✅ تم اختيار الشركة: {text}\nتقدر تبدأ بالأوامر دلوقتي. مثال: /3mlaa", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if get_user_company_id(telegram_id):
        await update.message.reply_text("اضغط على أحد الأوامر من القائمة عشان تبدأ، مثلاً /3mlaa\nولو عايز تغيّر الشركة استخدم /company")
        return ConversationHandler.END

    res = link_telegram_to_user(text, telegram_id)
    if res == "success":
        companies = get_user_companies_by_telegram(telegram_id)
        if len(companies) > 1:
            await ask_user_to_select_company(update, context, companies)
        else:
            if companies:
                context.user_data['company_id'] = companies[0]['id']
                context.user_data['company_name'] = companies[0]['name']
            await update.message.reply_text("✅ تم ربط حسابك بنجاح! تقدر دلوقتي تختار الأوامر من القائمة:\n/3mlaa\n/mwrdeen\n/mwzfeen\n/dakhl\n/sarf\n/taqarir\n/eedadat\n/company")
    elif res == "invalid":
        await update.message.reply_text("❌ كلمة المرور غلط. تأكد منها وابعتها تاني:")
    elif res == "linked":
        await update.message.reply_text("⚠️ كلمة المرور دي مربوطة بحساب تاني. تواصل مع الإدارة.")
    elif res == "already_has_account":
        await update.message.reply_text("⚠️ حسابك ده مربوط بشركة بالفعل.")
    return ConversationHandler.END

# ============ القوائم الرئيسية ============

async def ameel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [
        ["➕ إضافة عميل", "🗑️ حذف عميل"],
        ["💸 تسجيل دين", "💰 تسجيل دفع"],
        ["✂️ خصم من رصيد", "📊 حساب عميل"]
    ]
    await update.message.reply_text("👥 قائمة العملاء:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def mwrd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [
        ["➕ إضافة مورد", "🗑️ حذف مورد"],
        ["📋 تسجيل مديونية", "💸 تسجيل دفع لمورد"],
        ["📊 حساب مورد"]
    ]
    await update.message.reply_text("🏭 قائمة الموردين:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def mwzf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [
        ["➕ إضافة موظف", "🗑️ حذف موظف"],
        ["💵 صرف موظف", "📊 حساب موظف"]
    ]
    await update.message.reply_text("👷 قائمة الموظفين:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def dakhl_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [["👤 دفعة من عميل"], ["💰 دخل يدوي للخزنة"]]
    await update.message.reply_text("💰 اختار نوع الدخل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def sarf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [["🏭 صرف لمورد"], ["👷 صرف لموظف"], ["📋 مصروفات متنوعة"]]
    await update.message.reply_text("💸 اختار نوع الصرف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def taqrir_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [
        ["📌 تقرير بند", "📋 تقرير مصروفات"],
        ["👷 تقرير موظفين", "🏦 تقرير خزنة"],
        ["👤 تقرير عميل", "🏭 تقرير مورد"],
        ["📅 تقرير يومي"]
    ]
    await update.message.reply_text("📊 اختار التقرير:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def eedadat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context): return ConversationHandler.END
    keyboard = [
        ["➕ إضافة بند", "🗑️ حذف بند"],
        ["🗑️ حذف حركة", "📊 ملخص"],
        ["💰 رصيد الخزنة", "💸 إجمالي المديونيات"],
        ["💵 فلوس العملاء"]
    ]
    await update.message.reply_text("⚙️ الإعدادات:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

# ============ معالج الاختيارات ============

async def handle_main_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    company_id = context.user_data.get('company_id')

    # ===== العملاء =====
    if choice == "➕ إضافة عميل":
        await update.message.reply_text("👤 اسم العميل الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_ameel'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف عميل":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "💸 تسجيل دين":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_deen'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "💰 تسجيل دفع":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب عميل":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'hesab_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE
        
    elif choice == "✂️ خصم من رصيد":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_khasem'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    # ===== الموردين =====
    elif choice == "➕ إضافة مورد":
        await update.message.reply_text("🏭 اسم المورد الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_mwrd'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف مورد":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_mwrd'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📋 تسجيل مديونية":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_madyoniya'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "💸 تسجيل دفع لمورد":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب مورد":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'hesab_mwrd'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    # ===== الموظفين =====
    elif choice == "➕ إضافة موظف":
        await update.message.reply_text("👷 اسم الموظف الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_mwzf'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف موظف":
        names = get_employee_names(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_mwzf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "💵 صرف موظف":
        names = get_employee_names(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwzf_sarf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب موظف":
        names = get_employee_names(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'hesab_mwzf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    # ===== الدخل =====
    elif choice == "👤 دفعة من عميل":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "💰 دخل يدوي للخزنة":
        await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'dakhl'
        return AMOUNT

    # ===== الصرف =====
    elif choice == "🏭 صرف لمورد":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "👷 صرف لموظف":
        names = get_employee_names(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwzf_sarf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📋 مصروفات متنوعة":
        keyboard = [["📌 مصروفات إدارية"], ["📝 مصروفات أخرى"]]
        await update.message.reply_text("اختار نوع المصروفات:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return MASROF_TYPE

    # ===== التقارير =====
    elif choice == "📌 تقرير بند":
        bands = get_all_bands(company_id)
        if not bands:
            await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_band'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📋 تقرير مصروفات":
        bands, okhra = get_monthly_masrof_report(company_id)
        month = date.today().strftime("%Y-%m")
        if not bands and okhra == 0:
            await update.message.reply_text("📭 مفيش مصروفات الشهر ده", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
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
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "👷 تقرير موظفين":
        report = get_weekly_employees_report(company_id)
        if not report:
            await update.message.reply_text("📭 مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "👷 *تقرير الموظفين*\n\n"
        for emp in report:
            d = emp['data']
            carryover = d.get('carryover', 0)
            msg += f"*{emp['name']}*\n"
            msg += f"  💰 المرتب الأسبوعي: {d['salary']} جنيه\n"
            if carryover > 0:
                msg += f"  ↩️ مرحَّل من الأسبوع السابق: +{carryover:.0f} جنيه\n"
            elif carryover < 0:
                msg += f"  ↩️ سلفة مرحَّلة: {carryover:.0f} جنيه\n"
            if d['bonuses'] > 0:
                msg += f"  🎁 مكافآت: {d['bonuses']} جنيه\n"
            if d['advances'] > 0:
                msg += f"  💳 سلف: {d['advances']} جنيه\n"
            if d['deductions'] > 0:
                msg += f"  ✂️ خصم: {d['deductions']} جنيه\n"
            if d.get('cur_paid', 0) > 0:
                msg += f"  ✅ تم صرف الأسبوع دا: {d['cur_paid']} جنيه\n"
            msg += f"  💵 *الصافي المتبقي: {d['net']} جنيه*\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "🏦 تقرير خزنة":
        total_in, total_out = get_monthly_khazna_report(company_id)
        month = date.today().strftime("%Y-%m")
        net = total_in - total_out
        emoji = "📈" if net >= 0 else "📉"
        msg = (f"🏦 *تقرير الخزنة - {month}*\n\n"
               f"💚 إجمالي الدخل: {total_in} جنيه\n"
               f"🔴 إجمالي الصرف: {total_out} جنيه\n"
               f"{emoji} *الصافي: {net} جنيه*")
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "👤 تقرير عميل":
        names = get_all_clients(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "🏭 تقرير مورد":
        names = get_all_suppliers(company_id)
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_mwrd'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📅 تقرير يومي":
        today = date.today()
        days_since_saturday = (today.weekday() - 5) % 7
        week_start = today - timedelta(days=days_since_saturday)
        days_ar = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        keyboard = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            keyboard.append([f"{days_ar[i]} - {day.strftime('%Y-%m-%d')}"])
        context.user_data['action'] = 'taqrir_yawmi'
        await update.message.reply_text("📅 اختار اليوم:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return DAY_SELECT

    # ===== الإعدادات =====
    elif choice == "➕ إضافة بند":
        await update.message.reply_text("📌 اسم البند الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_band'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف بند":
        bands = get_all_bands(company_id)
        if not bands:
            await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_band'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف حركة":
        keyboard = [["🏦 الخزنة"], ["👥 العملاء"], ["🏭 الموردين"]]
        await update.message.reply_text("اختار من أي جدول؟", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return SELECT_RECORD

    elif choice == "📊 ملخص":
        msg = get_full_summary(company_id)
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💰 رصيد الخزنة":
        balance = get_balance(company_id)
        emoji = "📈" if balance >= 0 else "📉"
        await update.message.reply_text(f"{emoji} رصيد الخزنة: {balance} جنيه", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💸 إجمالي المديونيات":
        total, details = get_suppliers_total(company_id)
        if not details:
            await update.message.reply_text("✅ مفيش مديونيات", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "💸 *إجمالي المديونيات:*\n\n" + "\n".join(details) + f"\n\n*الإجمالي: {total} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💵 فلوس العملاء":
        total, details = get_clients_total(company_id)
        if not details:
            await update.message.reply_text("📭 مفيش فلوس للعملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "💰 *فلوس العملاء:*\n\n" + "\n".join(details) + f"\n\n*الإجمالي: {total} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ التقرير اليومي ============

async def handle_day_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = context.user_data['company_id']
        choice = update.message.text
        parts = choice.split(" - ")
        selected_date = parts[1].strip()
        day_name = parts[0].strip()
        records, total_in, total_out = get_daily_khazna_report(selected_date, company_id)
        if not records:
            await update.message.reply_text(f"📭 مفيش حركات يوم {day_name}", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        net = total_in - total_out
        emoji = "📈" if net >= 0 else "📉"
        msg = f"📅 *تقرير يوم {day_name} - {selected_date}*\n\n"
        for r in records:
            icon = "💚" if r['type'] == 'دخل' else "🔴"
            msg += f"{icon} {r['type']}: {r['amount']} جنيه - {r['description']}\n"
        msg += f"\n💚 إجمالي الدخل: {total_in} جنيه"
        msg += f"\n🔴 إجمالي الصرف: {total_out} جنيه"
        msg += f"\n{emoji} *الصافي: {net} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {str(e)}", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ الاسم والمبلغ والوصف ============

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    action = context.user_data['action']
    if action == 'mwzf_sarf':
        keyboard = [["💰 مرتب"], ["💳 سلفة"], ["🎁 مكافأة"], ["✂️ خصم"]]
        await update.message.reply_text("اختار نوع الصرف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return MWZF_ACTION
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    return NAME_AMOUNT

async def get_name_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = context.user_data['company_id']
        amount = parse_amount(update.message.text)
        action = context.user_data['action']
        name = context.user_data['name']
        if action == 'ameel_deen':
            add_client(name, amount, "دين", company_id)
            await update.message.reply_text(f"✅ تم تسجيل دين على {name}: {amount} جنيه")
        elif action == 'ameel_dafa3':
            add_client(name, amount, "دفع", company_id)
            await update.message.reply_text(f"✅ تم تسجيل دفع من {name}: {amount} جنيه")
        elif action == 'ameel_khasem':
            add_client(name, amount, "خصم", company_id)
            await update.message.reply_text(f"✅ تم خصم {amount} جنيه من رصيد {name}")
        elif action == 'mwrd_dafa3':
            add_supplier(name, amount, "دفع", company_id)
            await update.message.reply_text(f"✅ تم تسجيل دفع لـ {name}: {amount} جنيه")
        elif action == 'mwrd_madyoniya':
            add_supplier(name, amount, "مديونية", company_id)
            await update.message.reply_text(f"✅ تم تسجيل مديونية لـ {name}: {amount} جنيه")
        elif action == 'masrof_edari':
            add_masrof_edari(name, amount, company_id)
            await update.message.reply_text(f"✅ تم تسجيل مصروفات إدارية - {name}: {amount} جنيه")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return NAME_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 إيه الوصف؟")
        return DESCRIPTION
    except ValueError:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return AMOUNT

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    description = update.message.text
    amount = context.user_data['amount']
    add_transaction("دخل", amount, description, company_id)
    await update.message.reply_text(f"✅ تم تسجيل دخول: {amount} جنيه\n📝 {description}")
    return ConversationHandler.END

# ============ المصروفات والموظفين ============

async def get_masrof_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    choice = update.message.text
    if "إدارية" in choice:
        bands = get_all_bands(company_id)
        if not bands:
            await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'masrof_edari'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME
    elif "أخرى" in choice:
        context.user_data['action'] = 'masrof_okhra'
        await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
        return OKHRA_AMOUNT
    return ConversationHandler.END

async def get_okhra_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 اكتب نوت:")
        return OKHRA_NOTE
    except ValueError:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return OKHRA_AMOUNT

async def get_okhra_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    note = update.message.text
    amount = context.user_data['amount']
    add_masrof_okhra(amount, note, company_id)
    await update.message.reply_text(f"✅ تم تسجيل مصروفات أخرى: {amount} جنيه\n📝 {note}")
    return ConversationHandler.END

async def get_mwzf_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    choice = update.message.text
    type_map = {"مرتب": "مرتب", "سلفة": "سلفة", "مكافأة": "مكافأة", "خصم": "خصم"}
    mwzf_type = next((v for k, v in type_map.items() if k in choice), None)
    if not mwzf_type:
        await update.message.reply_text("❌ اختيار غلط")
        return ConversationHandler.END
    context.user_data['mwzf_type'] = mwzf_type
    name = context.user_data['name']
    if mwzf_type == "مرتب":
        data = get_employee_balance(name, company_id)
        if data:
            net = data['net']
            if net <= 0:
                await update.message.reply_text(
                    f"⚠️ {name} مفيش مرتب متبقي!\nالباقي: {net} جنيه",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
            context.user_data['mwzf_net'] = net
            keyboard = [["✅ تأكيد"], ["❌ إلغاء"]]
            carryover = data.get('carryover', 0)
            lines = f"👷 *{name}*\n\n💰 المرتب الأسبوعي: {data['salary']} جنيه\n"
            if carryover > 0:
                lines += f"↩️ مرحَّل من الأسبوع السابق: +{carryover:.0f} جنيه\n"
            elif carryover < 0:
                lines += f"↩️ سلفة مرحَّلة من الأسبوع الجاي: {carryover:.0f} جنيه\n"
            if data['bonuses'] > 0:
                lines += f"🎁 مكافآت: {data['bonuses']} جنيه\n"
            if data['advances'] > 0:
                lines += f"💳 سلف: {data['advances']} جنيه\n"
            if data['deductions'] > 0:
                lines += f"✂️ خصم: {data['deductions']} جنيه\n"
            if data.get('cur_paid', 0) > 0:
                lines += f"✅ تم صرف الأسبوع دا: {data['cur_paid']} جنيه\n"
            lines += f"\n💵 *الباقي: {net} جنيه*\n\nتأكيد الصرف؟"
            await update.message.reply_text(
                lines,
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return MWZF_CONFIRM
    await update.message.reply_text("💰 كام المبلغ؟", reply_markup=ReplyKeyboardRemove())
    return MWZF_AMOUNT

async def get_mwzf_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    choice = update.message.text
    name = context.user_data['name']
    net = context.user_data['mwzf_net']
    if "تأكيد" in choice:
        add_employee_transaction(name, "مرتب", net, company_id)
        await update.message.reply_text(f"✅ تم صرف مرتب {name}: {net} جنيه", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def get_mwzf_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = context.user_data['company_id']
        amount = parse_amount(update.message.text)
        name = context.user_data['name']
        mwzf_type = context.user_data['mwzf_type']
        add_employee_transaction(name, mwzf_type, amount, company_id)
        await update.message.reply_text(f"✅ تم تسجيل {mwzf_type} لـ {name}: {amount} جنيه")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return MWZF_AMOUNT

async def get_mwzf_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = context.user_data['company_id']
        salary = parse_amount(update.message.text)
        name = context.user_data['name']
        result = add_employee(name, salary, company_id)
        if result:
            await update.message.reply_text(f"✅ تم إضافة موظف: {name}\n💰 المرتب الأسبوعي: {salary} جنيه")
        else:
            await update.message.reply_text(f"⚠️ الموظف {name} موجود بالفعل")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return MWZF_SALARY

# ============ الفانكشن الرئيسية ============

async def get_hesab_or_add_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    action = context.user_data.get('action')
    name = update.message.text

    if action == 'add_ameel':
        result = add_person(name, "عميل", company_id)
        msg = f"✅ تم إضافة عميل: {name}" if result else f"⚠️ العميل {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_ameel':
        result = delete_person(name, "عميل", company_id)
        msg = f"✅ تم حذف العميل: {name}" if result else f"⚠️ العميل {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwrd':
        result = add_person(name, "مورد", company_id)
        msg = f"✅ تم إضافة مورد: {name}" if result else f"⚠️ المورد {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_mwrd':
        result = delete_person(name, "مورد", company_id)
        msg = f"✅ تم حذف المورد: {name}" if result else f"⚠️ المورد {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwzf':
        context.user_data['name'] = name
        await update.message.reply_text("💰 المرتب الأسبوعي؟")
        return MWZF_SALARY

    elif action == 'del_mwzf':
        result = delete_employee(name, company_id)
        msg = f"✅ تم حذف الموظف: {name}" if result else f"⚠️ الموظف {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_ameel':
        b = get_person_balance("عميل", name, company_id)
        if b > 0:
            await update.message.reply_text(f"👤 {name}\n💰 عليه: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"👤 {name}\n✅ ليه عندنا: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"👤 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_mwrd':
        b = get_person_balance("مورد", name, company_id)
        if b > 0:
            await update.message.reply_text(f"🏭 {name}\n💰 ليه عندنا: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"🏭 {name}\n✅ دفعنا له زيادة: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"🏭 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_mwzf':
        data = get_employee_balance(name, company_id)
        if not data:
            await update.message.reply_text("❌ مش لاقي بيانات", reply_markup=ReplyKeyboardRemove())
        else:
            carryover = data.get('carryover', 0)
            msg = f"👷 *{name}*\n\n💰 المرتب الأسبوعي: {data['salary']} جنيه\n"
            if carryover > 0:
                msg += f"↩️ مرحَّل من أسبوع سابق: +{carryover:.0f} جنيه\n"
            elif carryover < 0:
                msg += f"↩️ سلفة مرحَّلة: {carryover:.0f} جنيه\n"
            if data['bonuses'] > 0:
                msg += f"🎁 مكافآت: {data['bonuses']} جنيه\n"
            if data['advances'] > 0:
                msg += f"💳 سلف: {data['advances']} جنيه\n"
            if data['deductions'] > 0:
                msg += f"✂️ خصومات: {data['deductions']} جنيه\n"
            if data.get('cur_paid', 0) > 0:
                msg += f"✅ تم صرف الأسبوع دا: {data['cur_paid']} جنيه\n"
            msg += f"\n💵 *الصافي المتبقي: {data['net']} جنيه*"
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

    elif action == 'add_band':
        result = add_band(name, company_id)
        msg = f"✅ تم إضافة البند: {name}" if result else f"⚠️ البند {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_band':
        result = delete_band(name, company_id)
        msg = f"✅ تم حذف البند: {name}" if result else f"⚠️ البند {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'taqrir_band':
        total, details = get_monthly_band_report(name, company_id)
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
        transactions = get_person_transactions(name, person_type, company_id)
        if not transactions:
            await update.message.reply_text(f"📭 مفيش حركات لـ {name}", reply_markup=ReplyKeyboardRemove())
        else:
            balance = get_person_balance(person_type, name, company_id)
            await update.message.reply_text("⏳ جاري إنشاء التقرير...", reply_markup=ReplyKeyboardRemove())
            try:
                pdf_path = generate_pdf_report(name, person_type, transactions, balance)
                with open(pdf_path, 'rb') as f:
                    await update.message.reply_document(f, filename=f"تقرير_{name}.pdf")
                os.unlink(pdf_path)
            except Exception as e:
                status = "عليه" if balance > 0 else "ليه عندنا" if balance < 0 else "صفر"
                msg = f"📊 *تقرير {person_type}: {name}*\n\n"
                for t in transactions:
                    icon = "💸" if t['type'] in ['دين', 'مديونية'] else "💰"
                    msg += f"{icon} {t['date']} | {t['type']} | {t['amount']} جنيه\n"
                msg += f"\n💰 *الرصيد: {abs(balance)} جنيه ({status})*"
                await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

    elif action == 'del_record_confirm':
        return await confirm_delete_record(update, context)

    return ConversationHandler.END

# ============ حذف حركة ============

async def select_sheet_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company_id = context.user_data['company_id']
    choice = update.message.text
    if "الخزنة" in choice and "العملاء" not in choice and "الموردين" not in choice:
        table_name = "khazna"
        person_type_filter = None
    elif "العملاء" in choice:
        table_name = "person_transactions"
        person_type_filter = "عميل"
    elif "الموردين" in choice:
        table_name = "person_transactions"
        person_type_filter = "مورد"
    else:
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data['del_table'] = table_name
    context.user_data['del_person_type'] = person_type_filter
    records = get_last_records(table_name, company_id, 5, person_type=person_type_filter)
    if not records:
        await update.message.reply_text("❌ مفيش حركات", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    msg = "اختار رقم الحركة:\n\n"
    for i, r in enumerate(records):
        if table_name == "khazna":
            msg += f"{i+1}. {r['date']} | {r['type']} | {r['amount']} | {r['description']}\n"
        else:
            msg += f"{i+1}. {r['date']} | {r['person_name']} | {r['trans_type']} | {r['amount']}\n"
    context.user_data['del_records'] = records
    context.user_data['action'] = 'del_record_confirm'
    keyboard = [[str(i+1) for i in range(len(records))]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return NAME_AMOUNT_TYPE

async def confirm_delete_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = context.user_data['company_id']
        choice = int(update.message.text) - 1
        records = context.user_data['del_records']
        table_name = context.user_data['del_table']
        target = records[choice]
        delete_last_record(table_name, target['id'], company_id)
        await update.message.reply_text("✅ تم حذف الحركة", reply_markup=ReplyKeyboardRemove())
    except (ValueError, IndexError):
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ============ لوحة تحكم الأدمن ============

(ADMIN_MAIN, ADMIN_ADD_COMPANY_NAME, ADMIN_ADD_COMPANY_PASS, 
 ADMIN_ADD_USER_COMPANY, ADMIN_ADD_USER_NAME, ADMIN_ADD_USER_PASS,
 ADMIN_SHOW_USERS_COMPANY, ADMIN_DEL_USER_ID,
 ADMIN_CHANGE_PASS_ID, ADMIN_CHANGE_PASS_NEW) = range(100, 110)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or str(update.effective_user.id) != str(ADMIN_ID):
        return ConversationHandler.END
    keyboard = [
        ["➕ إضافة شركة", "📋 عرض الشركات"],
        ["➕ إضافة حساب موظف", "📋 عرض موظفين شركة"],
        ["🔑 تغيير باسورد موظف", "🗑️ حذف حساب موظف"],
        ["❌ إلغاء"]
    ]
    await update.message.reply_text("👑 لوحة تحكم الإدارة:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ADMIN_MAIN

async def admin_handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "➕ إضافة شركة":
        await update.message.reply_text("📝 اكتب اسم الشركة الجديدة:", reply_markup=ReplyKeyboardRemove())
        return ADMIN_ADD_COMPANY_NAME
    elif choice == "📋 عرض الشركات":
        companies = get_all_companies()
        if not companies:
            await update.message.reply_text("📭 مفيش شركات متسجلة.", reply_markup=ReplyKeyboardRemove())
        else:
            msg = "🏢 *قائمة الشركات:*\n\n"
            for c in companies:
                msg += f"🔹 {c['id']} - {c['name']} (يوزرات: {c['user_count']})\nباسورد الداشبورد: `{c['dashboard_password']}`\n\n"
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif choice == "➕ إضافة حساب موظف":
        companies = get_all_companies()
        if not companies:
            await update.message.reply_text("❌ مفيش شركات، ضيف شركة الأول.")
            return ConversationHandler.END
        msg = "🏢 اختار رقم الشركة اللي هتضيف فيها الموظف:\n\n"
        for c in companies:
            msg += f"{c['id']} - {c['name']}\n"
        await update.message.reply_text(msg)
        return ADMIN_ADD_USER_COMPANY
    elif choice == "📋 عرض موظفين شركة":
        await update.message.reply_text("🏢 اكتب رقم الشركة اللي عايز تعرض موظفينها:")
        return ADMIN_SHOW_USERS_COMPANY
    elif choice == "🔑 تغيير باسورد موظف":
        await update.message.reply_text("🔑 ابعت الـ ID بتاع الحساب اللي عايز تغير الباسورد بتاعه (هتلاقيه في عرض الموظفين):", reply_markup=ReplyKeyboardRemove())
        return ADMIN_CHANGE_PASS_ID
    elif choice == "🗑️ حذف حساب موظف":
        await update.message.reply_text("🗑️ ابعت الـ ID بتاع الحساب اللي عايز تحذفه (هتلاقيه في عرض الموظفين):", reply_markup=ReplyKeyboardRemove())
        return ADMIN_DEL_USER_ID
    elif choice == "❌ إلغاء":
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    return ConversationHandler.END

async def admin_add_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_company_name'] = update.message.text
    await update.message.reply_text("🔑 اكتب باسورد الداشبورد للشركة دي:")
    return ADMIN_ADD_COMPANY_PASS

async def admin_add_company_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = normalize_text(update.message.text)
    name = context.user_data['new_company_name']
    cid = add_company(name, password)
    if cid:
        await update.message.reply_text(f"✅ تم إضافة شركة {name} بنجاح برقم {cid}\nالباسورد: {password}")
    else:
        await update.message.reply_text(f"⚠️ الشركة دي موجودة قبل كده.")
    return ConversationHandler.END

async def admin_add_user_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = int(update.message.text)
        context.user_data['new_user_company_id'] = company_id
        await update.message.reply_text("👤 اكتب اسم الموظف (الاسم بس):")
        return ADMIN_ADD_USER_NAME
    except ValueError:
        await update.message.reply_text("❌ اكتب أرقام بس للشركة:")
        return ADMIN_ADD_USER_COMPANY

async def admin_add_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_user_name'] = update.message.text
    await update.message.reply_text("🔑 اكتب كلمة مرور (باسورد) قوية ومميزة للموظف ده عشان يدخل بيها:")
    return ADMIN_ADD_USER_PASS

async def admin_add_user_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = normalize_text(update.message.text)
    company_id = context.user_data['new_user_company_id']
    username = context.user_data['new_user_name']
    
    if add_user_account(company_id, username, password):
        await update.message.reply_text(f"✅ تم إنشاء حساب الموظف بنجاح!\n\n🏢 رقم الشركة: {company_id}\n👤 الاسم: {username}\n🔑 الباسورد: `{password}`\n\nابعت الباسورد ده للموظف عشان يسجل بيه.", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ حصلت مشكلة! ممكن الباسورد ده متسجل قبل كده، جرب باسورد تاني.")
    return ConversationHandler.END

async def admin_show_users_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        company_id = int(update.message.text)
        users = get_company_users(company_id)
        if not users:
            await update.message.reply_text(f"📭 مفيش موظفين متسجلين في الشركة رقم {company_id}")
        else:
            msg = f"👥 *موظفين الشركة {company_id}:*\n\n"
            for u in users:
                linked = "✅ (مربوط)" if u['telegram_id'] else "⏳ (مش مربوط)"
                msg += f"ID: {u['id']} | الاسم: {u['username']} | الباسورد: `{u['password']}` | {linked}\n"
            await update.message.reply_text(msg, parse_mode='Markdown')
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ اكتب أرقام بس:")
        return ADMIN_SHOW_USERS_COMPANY

async def admin_del_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text)
        if remove_user_account(user_id=user_id):
            await update.message.reply_text(f"✅ تم حذف الحساب رقم {user_id} بنجاح.")
        else:
            await update.message.reply_text("❌ الحساب ده مش موجود.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ اكتب أرقام بس للـ ID:")
        return ADMIN_DEL_USER_ID

async def admin_change_pass_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text)
        context.user_data['change_pass_user_id'] = user_id
        await update.message.reply_text("🔑 اكتب الباسورد الجديد للموظف ده:")
        return ADMIN_CHANGE_PASS_NEW
    except ValueError:
        await update.message.reply_text("❌ اكتب أرقام بس للـ ID:")
        return ADMIN_CHANGE_PASS_ID

async def admin_change_pass_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_password = normalize_text(update.message.text)
    user_id = context.user_data['change_pass_user_id']
    if update_user_password(user_id, new_password):
        await update.message.reply_text(f"✅ تم تغيير الباسورد بنجاح للحساب رقم {user_id}.\nالباسورد الجديد: `{new_password}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ حصلت مشكلة! ممكن الباسورد ده مستخدم قبل كده أو الـ ID غلط.")
    return ConversationHandler.END

# ============ تشغيل البوت ============

app = ApplicationBuilder().token(TOKEN).build()

entry_points_list = [
    CommandHandler("start", start),
    CommandHandler("company", select_company_command),
    CommandHandler("3mlaa", ameel_menu),
    CommandHandler("mwrdeen", mwrd_menu),
    CommandHandler("mwzfeen", mwzf_menu),
    CommandHandler("dakhl", dakhl_menu),
    CommandHandler("sarf", sarf_menu),
    CommandHandler("taqarir", taqrir_menu),
    CommandHandler("eedadat", eedadat_menu),
]

conv_handler = ConversationHandler(
    entry_points=entry_points_list + [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unlinked_password)],
    states={
        MAIN_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_action)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        NAME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_amount)],
        NAME_AMOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hesab_or_add_del)],
        SELECT_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_sheet_to_delete)],
        MASROF_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_masrof_type)],
        MWZF_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_salary)],
        MWZF_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_action)],
        MWZF_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_amount)],
        MWZF_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mwzf_confirm)],
        OKHRA_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_okhra_amount)],
        OKHRA_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_okhra_note)],
        DAY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_day_select)],
    },
    fallbacks=entry_points_list + [CommandHandler("cancel", cancel)]
)

admin_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("admin", admin_menu), MessageHandler(filters.Regex("^👑 لوحة الإدارة$"), admin_menu)],
    states={
        ADMIN_MAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_main)],
        ADMIN_ADD_COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_company_name)],
        ADMIN_ADD_COMPANY_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_company_pass)],
        ADMIN_ADD_USER_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_user_company)],
        ADMIN_ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_user_name)],
        ADMIN_ADD_USER_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_user_pass)],
        ADMIN_SHOW_USERS_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_show_users_company)],
        ADMIN_DEL_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_del_user_id)],
        ADMIN_CHANGE_PASS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_change_pass_id)],
        ADMIN_CHANGE_PASS_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_change_pass_new)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(admin_conv_handler)
app.add_handler(conv_handler)

async def error_callback(update, context):
    error = context.error
    if isinstance(error, Conflict):
        print(f"⚠️ Conflict: {error}")
        import sys
        sys.exit(1)
    else:
        print(f"❌ خطأ: {error}")
        import traceback
        traceback.print_exc()

app.add_error_handler(error_callback)

if __name__ == "__main__":
    try:
        print("✅ البوت شغال!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n✋ تم إيقاف البوت")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
