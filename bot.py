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
                   get_daily_khazna_report)
import os
import time

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is required")

print("=" * 60)
print("🚀 تشغيل الدردشة الآلية")
print(f"📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🔌 معرف العملية: {os.getpid()}")
print("=" * 60)

init_db()

from manual_import import import_from_csv
from database import get_db

conn = get_db()
cursor = conn.cursor()

# check if data already exists
cursor.execute("SELECT COUNT(*) FROM persons")
count = cursor.fetchone()[0]

if count == 0:
    print("🚀 First time setup: importing CSV...")
    try:
        import_from_csv()
        print("✅ Import finished")
    except Exception as e:
        print(f"❌ Error during import: {e}")
else:
    print("✅ Data already exists, skipping import")

conn.close()

(MAIN_ACTION, AMOUNT, DESCRIPTION, NAME, NAME_AMOUNT, NAME_AMOUNT_TYPE,
 SELECT_RECORD, SARF_TYPE, MASROF_TYPE, MWZF_SALARY, MWZF_ACTION,
 MWZF_AMOUNT, OKHRA_AMOUNT, OKHRA_NOTE, MWZF_CONFIRM, DAY_SELECT) = range(16)

# ============ أوامر العملاء ============

async def ameel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ إضافة عميل", "🗑️ حذف عميل"],
        ["💸 تسجيل دين", "💰 تسجيل دفع"],
        ["📊 حساب عميل"]
    ]
    await update.message.reply_text("👥 قائمة العملاء:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def mwrd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ إضافة مورد", "🗑️ حذف مورد"],
        ["📋 تسجيل مديونية", "💸 تسجيل دفع لمورد"],
        ["📊 حساب مورد"]
    ]
    await update.message.reply_text("🏭 قائمة الموردين:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def mwzf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ إضافة موظف", "🗑️ حذف موظف"],
        ["💵 صرف موظف", "📊 حساب موظف"]
    ]
    await update.message.reply_text("👷 قائمة الموظفين:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def dakhl_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["👤 دفعة من عميل"],
        ["💰 دخل يدوي للخزنة"]
    ]
    await update.message.reply_text("💰 اختار نوع الدخل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def sarf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🏭 صرف لمورد"],
        ["👷 صرف لموظف"],
        ["📋 مصروفات متنوعة"]
    ]
    await update.message.reply_text("💸 اختار نوع الصرف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def taqrir_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📌 تقرير بند", "📋 تقرير مصروفات"],
        ["👷 تقرير موظفين", "🏦 تقرير خزنة"],
        ["👤 تقرير عميل", "🏭 تقرير مورد"],
        ["📅 تقرير يومي"]
    ]
    await update.message.reply_text("📊 اختار التقرير:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

async def eedadat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ إضافة بند", "🗑️ حذف بند"],
        ["🗑️ حذف حركة", "📊 ملخص"],
        ["💰 رصيد الخزنة", "💸 إجمالي المديونيات"],
        ["💵 فلوس العملاء"]
    ]
    await update.message.reply_text("⚙️ الإعدادات والمزيد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return MAIN_ACTION

# ============ معالج الاختيارات الرئيسية ============

async def handle_main_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    # ===== العملاء =====
    if choice == "➕ إضافة عميل":
        await update.message.reply_text("👤 اسم العميل الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_ameel'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف عميل":
        names = get_all_clients()
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "💸 تسجيل دين":
        names = get_all_clients()
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_deen'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "💰 تسجيل دفع":
        names = get_all_clients()
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'ameel_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب عميل":
        names = get_all_clients()
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'hesab_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    # ===== الموردين =====
    elif choice == "➕ إضافة مورد":
        await update.message.reply_text("🏭 اسم المورد الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_mwrd'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف مورد":
        names = get_all_suppliers()
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_mwrd'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📋 تسجيل مديونية":
        names = get_all_suppliers()
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_madyoniya'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "💸 تسجيل دفع لمورد":
        names = get_all_suppliers()
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب مورد":
        names = get_all_suppliers()
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
        names = get_employee_names()
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_mwzf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "💵 صرف موظف":
        names = get_employee_names()
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwzf_sarf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "📊 حساب موظف":
        names = get_employee_names()
        if not names:
            await update.message.reply_text("❌ مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'hesab_mwzf'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👷 اختار الموظف:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    # ===== الدخل =====
    elif choice == "👤 دفعة من عميل":
        names = get_all_clients()
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
        names = get_all_suppliers()
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'mwrd_dafa3'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME

    elif choice == "👷 صرف لموظف":
        names = get_employee_names()
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
        bands = get_all_bands()
        if not bands:
            await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_band'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📋 تقرير مصروفات":
        bands, okhra = get_monthly_masrof_report()
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
        report = get_weekly_employees_report()
        if not report:
            await update.message.reply_text("📭 مفيش موظفين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "👷 *تقرير الموظفين الأسبوعي*\n\n"
        for emp in report:
            d = emp['data']
            msg += f"*{emp['name']}*\n"
            msg += f"  💰 المرتب: {d['salary']} | 🎁 مكافآت: {d['bonuses']}\n"
            msg += f"  💳 سلف: {d['advances']} | ✂️ خصم: {d['deductions']}\n"
            msg += f"  💵 الصافي المتبقي: {d['net']} جنيه\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "🏦 تقرير خزنة":
        total_in, total_out = get_monthly_khazna_report()
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
        names = get_all_clients()
        if not names:
            await update.message.reply_text("❌ مفيش عملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_ameel'
        keyboard = [[name] for name in names]
        await update.message.reply_text("👤 اختار العميل:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "🏭 تقرير مورد":
        names = get_all_suppliers()
        if not names:
            await update.message.reply_text("❌ مفيش موردين", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'taqrir_mwrd'
        keyboard = [[name] for name in names]
        await update.message.reply_text("🏭 اختار المورد:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "📅 تقرير يومي":
        # أيام الأسبوع من السبت للجمعة
        today = date.today()
        days_since_saturday = (today.weekday() - 5) % 7
        week_start = today - timedelta(days=days_since_saturday)
        days_ar = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        keyboard = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_name = days_ar[i]
            keyboard.append([f"{day_name} - {day.strftime('%Y-%m-%d')}"])
        context.user_data['action'] = 'taqrir_yawmi'
        await update.message.reply_text("📅 اختار اليوم:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return DAY_SELECT

    # ===== الإعدادات =====
    elif choice == "➕ إضافة بند":
        await update.message.reply_text("📌 اسم البند الجديد؟", reply_markup=ReplyKeyboardRemove())
        context.user_data['action'] = 'add_band'
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف بند":
        bands = get_all_bands()
        if not bands:
            await update.message.reply_text("❌ مفيش بنود", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        context.user_data['action'] = 'del_band'
        keyboard = [[band] for band in bands]
        await update.message.reply_text("📌 اختار البند:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return NAME_AMOUNT_TYPE

    elif choice == "🗑️ حذف حركة":
        keyboard = [["🏦 الخزنة"], ["👥 العملاء"], ["🏭 الموردين"]]
        await update.message.reply_text("اختار من أي شيت؟", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return SELECT_RECORD

    elif choice == "📊 ملخص":
        msg = get_full_summary()
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💰 رصيد الخزنة":
        balance = get_balance()
        emoji = "📈" if balance >= 0 else "📉"
        await update.message.reply_text(f"{emoji} رصيد الخزنة: {balance} جنيه", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💸 إجمالي المديونيات":
        total, details = get_suppliers_total()
        if not details:
            await update.message.reply_text("✅ مفيش مديونيات", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "💸 *إجمالي المديونيات:*\n\n" + "\n".join(details) + f"\n\n*الإجمالي: {total} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    elif choice == "💵 فلوس العملاء":
        total, details = get_clients_total()
        if not details:
            await update.message.reply_text("📭 مفيش فلوس للعملاء", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        msg = "💰 *فلوس العملاء:*\n\n" + "\n".join(details) + f"\n\n*الإجمالي: {total} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ معالج اختيار اليوم ============

async def handle_day_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    try:
        selected_date = choice.split(" - ")[1]
        records, total_in, total_out = get_daily_khazna_report(selected_date)
        day_name = choice.split(" - ")[0]
        if not records:
            await update.message.reply_text(f"📭 مفيش حركات يوم {day_name}", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        net = total_in - total_out
        emoji = "📈" if net >= 0 else "📉"
        msg = f"📅 *تقرير يوم {day_name} - {selected_date}*\n\n"
        for r in records:
            icon = "💚" if r['النوع'] == 'دخل' else "🔴"
            msg += f"{icon} {r['النوع']}: {r['المبلغ']} جنيه - {r['الوصف']}\n"
        msg += f"\n💚 إجمالي الدخل: {total_in} جنيه"
        msg += f"\n🔴 إجمالي الصرف: {total_out} جنيه"
        msg += f"\n{emoji} *الصافي: {net} جنيه*"
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("❌ حصل خطأ", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ معالج الاسم ============

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
        amount = float(update.message.text)
        action = context.user_data['action']
        name = context.user_data['name']
        if action == 'ameel_deen':
            add_client(name, amount, "دين")
            await update.message.reply_text(f"✅ تم تسجيل دين على {name}: {amount} جنيه")
        elif action == 'ameel_dafa3':
            add_client(name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع من {name}: {amount} جنيه")
        elif action == 'mwrd_dafa3':
            add_supplier(name, amount, "دفع")
            await update.message.reply_text(f"✅ تم تسجيل دفع لـ {name}: {amount} جنيه")
        elif action == 'mwrd_madyoniya':
            add_supplier(name, amount, "مديونية")
            await update.message.reply_text(f"✅ تم تسجيل مديونية لـ {name}: {amount} جنيه")
        elif action == 'masrof_edari':
            add_masrof_edari(name, amount)
            await update.message.reply_text(f"✅ تم تسجيل مصروفات إدارية - {name}: {amount} جنيه")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return NAME_AMOUNT

# ============ معالج المبلغ والوصف ============

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 إيه الوصف؟")
        return DESCRIPTION
    except:
        await update.message.reply_text("❌ لازم تكتب رقم بس:")
        return AMOUNT

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    amount = context.user_data['amount']
    add_transaction("دخل", amount, description)
    await update.message.reply_text(f"✅ تم تسجيل دخول: {amount} جنيه\n📝 {description}")
    return ConversationHandler.END

# ============ المصروفات ============

async def get_masrof_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "إدارية" in choice:
        bands = get_all_bands()
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
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 اكتب نوت:")
        return OKHRA_NOTE
    except:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return OKHRA_AMOUNT

async def get_okhra_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    amount = context.user_data['amount']
    add_masrof_okhra(amount, note)
    await update.message.reply_text(f"✅ تم تسجيل مصروفات أخرى: {amount} جنيه\n📝 {note}")
    return ConversationHandler.END

# ============ الموظفين ============

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
        data = get_employee_balance(name)
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
            await update.message.reply_text(
                f"👷 *{name}*\n\n"
                f"💰 المرتب: {data['salary']} جنيه\n"
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
        add_employee_transaction(name, "مرتب", net)
        await update.message.reply_text(f"✅ تم صرف مرتب {name}: {net} جنيه", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def get_mwzf_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        name = context.user_data['name']
        mwzf_type = context.user_data['mwzf_type']
        add_employee_transaction(name, mwzf_type, amount)
        await update.message.reply_text(f"✅ تم تسجيل {mwzf_type} لـ {name}: {amount} جنيه")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return MWZF_AMOUNT

async def get_mwzf_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        salary = float(update.message.text)
        name = context.user_data['name']
        result = add_employee(name, salary)
        if result:
            await update.message.reply_text(f"✅ تم إضافة موظف: {name}\n💰 المرتب الأسبوعي: {salary} جنيه")
        else:
            await update.message.reply_text(f"⚠️ الموظف {name} موجود بالفعل")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ لازم تكتب رقم:")
        return MWZF_SALARY

# ============ الفانكشن الرئيسية NAME_AMOUNT_TYPE ============

async def get_hesab_or_add_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    name = update.message.text

    if action == 'add_ameel':
        result = add_person(name, "عميل")
        msg = f"✅ تم إضافة عميل: {name}" if result else f"⚠️ العميل {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_ameel':
        result = delete_person(name, "عميل")
        msg = f"✅ تم حذف العميل: {name}" if result else f"⚠️ العميل {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwrd':
        result = add_person(name, "مورد")
        msg = f"✅ تم إضافة مورد: {name}" if result else f"⚠️ المورد {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_mwrd':
        result = delete_person(name, "مورد")
        msg = f"✅ تم حذف المورد: {name}" if result else f"⚠️ المورد {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'add_mwzf':
        context.user_data['name'] = name
        await update.message.reply_text("💰 المرتب الأسبوعي؟")
        return MWZF_SALARY

    elif action == 'del_mwzf':
        result = delete_employee(name)
        msg = f"✅ تم حذف الموظف: {name}" if result else f"⚠️ الموظف {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_ameel':
        b = get_person_balance("الخزنة_العملاء", name)
        if b > 0:
            await update.message.reply_text(f"👤 {name}\n💰 عليه: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"👤 {name}\n✅ ليه عندنا: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"👤 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_mwrd':
        b = get_person_balance("الخزنة_الموردين", name)
        if b > 0:
            await update.message.reply_text(f"🏭 {name}\n💰 ليه عندنا: {b} جنيه", reply_markup=ReplyKeyboardRemove())
        elif b < 0:
            await update.message.reply_text(f"🏭 {name}\n✅ دفعنا له زيادة: {abs(b)} جنيه", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"🏭 {name}\n✅ حسابه صفر", reply_markup=ReplyKeyboardRemove())

    elif action == 'hesab_mwzf':
        data = get_employee_balance(name)
        if not data:
            await update.message.reply_text("❌ مش لاقي بيانات", reply_markup=ReplyKeyboardRemove())
        else:
            msg = (f"👷 *{name}*\n\n"
                   f"💰 المرتب: {data['salary']} جنيه\n"
                   f"🎁 مكافآت: {data['bonuses']} جنيه\n"
                   f"💳 سلف: {data['advances']} جنيه\n"
                   f"✂️ خصومات: {data['deductions']} جنيه\n"
                   f"✅ تم صرف: {data['total_paid']} جنيه\n\n"
                   f"💵 *الصافي المتبقي: {data['net']} جنيه*")
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

    elif action == 'add_band':
        result = add_band(name)
        msg = f"✅ تم إضافة البند: {name}" if result else f"⚠️ البند {name} موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'del_band':
        result = delete_band(name)
        msg = f"✅ تم حذف البند: {name}" if result else f"⚠️ البند {name} مش موجود"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    elif action == 'taqrir_band':
        total, details = get_monthly_band_report(name)
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
        transactions = get_person_transactions(name, person_type)
        if not transactions:
            await update.message.reply_text(f"📭 مفيش حركات لـ {name}", reply_markup=ReplyKeyboardRemove())
        else:
            balance = get_person_balance(person_type, name)
            await update.message.reply_text("⏳ جاري إنشاء التقرير...", reply_markup=ReplyKeyboardRemove())
            try:
                pdf_path = generate_pdf_report(name, person_type, transactions, balance)
                with open(pdf_path, 'rb') as f:
                    await update.message.reply_document(f, filename=f"تقرير_{name}.pdf")
                import os
                os.unlink(pdf_path)
            except Exception as e:
                await update.message.reply_text(f"❌ حصل خطأ: {str(e)}", reply_markup=ReplyKeyboardRemove())

    elif action == 'del_record_confirm':
        return await confirm_delete_record(update, context)

    return ConversationHandler.END

# ============ حذف حركة ============

async def select_sheet_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "الخزنة" in choice and "العملاء" not in choice and "الموردين" not in choice:
        table_name = "khazna"
    elif "العملاء" in choice:
        table_name = "person_transactions"
    elif "الموردين" in choice:
        table_name = "person_transactions"
    else:
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    context.user_data['del_table'] = table_name
    context.user_data['del_person_type'] = "عميل" if "العملاء" in choice else "مورد" if "الموردين" in choice else None
    records = get_last_records(table_name, 5)
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
        choice = int(update.message.text) - 1
        records = context.user_data['del_records']
        table_name = context.user_data['del_table']
        target = records[choice]
        record_id = target['id']
        delete_last_record(table_name, record_id)
        await update.message.reply_text("✅ تم حذف الحركة", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ اختيار غلط", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ============ تشغيل البوت ============

app = ApplicationBuilder().token(TOKEN).build()

entry_points_list = [
    CommandHandler("3mlaa", ameel_menu),
    CommandHandler("mwrdeen", mwrd_menu),
    CommandHandler("mwzfeen", mwzf_menu),
    CommandHandler("dakhl", dakhl_menu),
    CommandHandler("sarf", sarf_menu),
    CommandHandler("taqarir", taqrir_menu),
    CommandHandler("eedadat", eedadat_menu),
]

conv_handler = ConversationHandler(
    entry_points=entry_points_list,
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

app.add_handler(conv_handler)

import time
from telegram.error import Conflict

# Error handler callback
async def error_callback(update, context):
    """Handle errors raised during polling"""
    error = context.error
    if isinstance(error, Conflict):
        print(f"\n⚠️  تنبيه Conflict: {error}")
        print(f"🔴 يوجد نسخة أخرى من البوت تعمل!")
        print("📊 سيتم إغلاق البوت الآن لكي تعيد تشغيله بعملية واحدة")
        import sys
        sys.exit(1)  # Exit gracefully instead of raising
    else:
        print(f"❌ خطأ في البوت: {error}")
        import traceback
        traceback.print_exc()

# Register error handler with the application
app.add_error_handler(error_callback)

def start_bot_with_retry():
    """Start bot - Railway will restart on error"""
    try:
        print("✅ البوت شغال!")
        print("🔄 جاري الاتصال بـ Telegram...")
        print("🔌 في انتظار الرسائل...")
        print(f"🆔 معرف النسخة (Replica): {os.getenv('RAILWAY_REPLICA_ID', 'unknown')}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت من قبل المستخدم")
    except Exception as e:
        print(f"❌ خطأ في البوت: {e}")
        print(f"📍 نوع الخطأ: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Exit with error code so Railway restarts
        exit(1)

if __name__ == "__main__":
    try:
        start_bot_with_retry()
    except KeyboardInterrupt:
        print("\n✋ تم إيقاف البوت")
