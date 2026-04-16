import sqlite3
import os
from datetime import date, datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

# ============ إعداد قاعدة البيانات ============

DB_PATH = os.environ.get("DB_PATH", "/app/data/bot.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # جدول الخزنة
    c.execute("""
        CREATE TABLE IF NOT EXISTS khazna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الأشخاص (عملاء + موردين)
    c.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, type)
        )
    """)

    # جدول حركات الأشخاص
    c.execute("""
        CREATE TABLE IF NOT EXISTS person_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            person_type TEXT NOT NULL,
            date TEXT NOT NULL,
            trans_type TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الموظفين
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            salary REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول حركات الموظفين
    c.execute("""
        CREATE TABLE IF NOT EXISTS employee_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            date TEXT NOT NULL,
            trans_type TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول البنود
    c.execute("""
        CREATE TABLE IF NOT EXISTS bands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول المصروفات الإدارية
    c.execute("""
        CREATE TABLE IF NOT EXISTS masrof_edari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            band TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول المصروفات الأخرى
    c.execute("""
        CREATE TABLE IF NOT EXISTS masrof_okhra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            note TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة")

# ============ دوال الخزنة ============

def add_transaction(sheet, trans_type, amount, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
        (str(date.today()), trans_type, amount, description)
    )
    conn.commit()
    conn.close()

def get_balance(sheet):
    conn = get_db()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as balance
        FROM khazna
    """).fetchone()
    conn.close()
    return row['balance'] if row else 0

def get_daily_khazna_report(sheet, selected_date):
    conn = get_db()
    rows = conn.execute(
        "SELECT date as 'التاريخ', type as 'النوع', amount as 'المبلغ', description as 'الوصف' FROM khazna WHERE date = ?",
        (selected_date,)
    ).fetchall()
    records = [dict(r) for r in rows]
    total_in = sum(r['المبلغ'] for r in records if r['النوع'] == 'دخل')
    total_out = sum(r['المبلغ'] for r in records if r['النوع'] == 'صرف')
    conn.close()
    return records, total_in, total_out

def get_monthly_khazna_report(sheet):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) as total_in,
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as total_out
        FROM khazna WHERE date LIKE ?
    """, (f"{month}%",)).fetchone()
    conn.close()
    return (row['total_in'], row['total_out']) if row else (0, 0)

# ============ دوال الأشخاص (عملاء / موردين) ============

def add_person(sheet, name, person_type):
    conn = get_db()
    try:
        conn.execute("INSERT INTO persons (name, type) VALUES (?, ?)", (name, person_type))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_person(sheet, name, person_type):
    conn = get_db()
    cur = conn.execute("DELETE FROM persons WHERE name=? AND type=?", (name, person_type))
    conn.commit()
    conn.close()
    return cur.rowcount > 0

def get_all_clients(sheet):
    conn = get_db()
    rows = conn.execute("SELECT name FROM persons WHERE type='عميل' ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]

def get_all_suppliers(sheet):
    conn = get_db()
    rows = conn.execute("SELECT name FROM persons WHERE type='مورد' ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_client(sheet, name, amount, trans_type):
    today = str(date.today())
    conn = get_db()
    conn.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (?, ?, ?, ?, ?)",
        (name, "عميل", today, trans_type, amount)
    )
    # تحديث الخزنة
    if trans_type == "دفع":
        conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
                     (today, "دخل", amount, f"دفعة من عميل: {name}"))
    conn.commit()
    conn.close()

def add_supplier(sheet, name, amount, trans_type):
    today = str(date.today())
    conn = get_db()
    conn.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (?, ?, ?, ?, ?)",
        (name, "مورد", today, trans_type, amount)
    )
    # تحديث الخزنة
    if trans_type == "دفع":
        conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
                     (today, "صرف", amount, f"دفع لمورد: {name}"))
    conn.commit()
    conn.close()

def get_person_balance(person_type, name):
    conn = get_db()
    rows = conn.execute(
        "SELECT trans_type, amount FROM person_transactions WHERE person_name=? AND person_type=?",
        (name, person_type)
    ).fetchall()
    conn.close()
    balance = 0
    for r in rows:
        if person_type == "عميل":
            if r['trans_type'] == 'دين':
                balance += r['amount']
            elif r['trans_type'] == 'دفع':
                balance -= r['amount']
        else:  # مورد
            if r['trans_type'] == 'مديونية':
                balance += r['amount']
            elif r['trans_type'] == 'دفع':
                balance -= r['amount']
    return balance

def get_clients_total(sheet):
    names = get_all_clients(sheet)
    details = []
    total = 0
    for name in names:
        b = get_person_balance(sheet, "الخزنة_العملاء", name)
        if b != 0:
            details.append(f"👤 {name}: {b} جنيه")
            total += b
    return total, details

def get_suppliers_total(sheet):
    names = get_all_suppliers(sheet)
    details = []
    total = 0
    for name in names:
        b = get_person_balance(sheet, "الخزنة_الموردين", name)
        if b != 0:
            details.append(f"🏭 {name}: {b} جنيه")
            total += b
    return total, details

def get_person_transactions(sheet, name, person_type):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, trans_type as type, amount FROM person_transactions WHERE person_name=? AND person_type=? ORDER BY date",
        (name, person_type)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ============ دوال الموظفين ============

def add_employee(sheet, name, salary):
    conn = get_db()
    try:
        conn.execute("INSERT INTO employees (name, salary) VALUES (?, ?)", (name, salary))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_employee(sheet, name):
    conn = get_db()
    cur = conn.execute("DELETE FROM employees WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0

def get_all_employees(sheet):
    conn = get_db()
    rows = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee_names(sheet):
    conn = get_db()
    rows = conn.execute("SELECT name FROM employees ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_employee_transaction(sheet, name, trans_type, amount):
    today = str(date.today())
    conn = get_db()
    conn.execute(
        "INSERT INTO employee_transactions (employee_name, date, trans_type, amount) VALUES (?, ?, ?, ?)",
        (name, today, trans_type, amount)
    )
    # تحديث الخزنة لو صرف مرتب أو سلفة
    if trans_type in ["مرتب", "سلفة"]:
        conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
                     (today, "صرف", amount, f"{trans_type} موظف: {name}"))
    conn.commit()
    conn.close()

def get_employee_balance(sheet, name):
    conn = get_db()
    emp = conn.execute("SELECT salary FROM employees WHERE name=?", (name,)).fetchone()
    if not emp:
        conn.close()
        return None

    # حركات الأسبوع الحالي
    today = date.today()
    days_since_saturday = (today.weekday() - 5) % 7
    week_start = str(today - timedelta(days=days_since_saturday))

    rows = conn.execute(
        "SELECT trans_type, amount FROM employee_transactions WHERE employee_name=? AND date >= ?",
        (name, week_start)
    ).fetchall()
    conn.close()

    salary = emp['salary']
    bonuses = sum(r['amount'] for r in rows if r['trans_type'] == 'مكافأة')
    advances = sum(r['amount'] for r in rows if r['trans_type'] == 'سلفة')
    deductions = sum(r['amount'] for r in rows if r['trans_type'] == 'خصم')
    total_paid = sum(r['amount'] for r in rows if r['trans_type'] == 'مرتب')

    net = salary + bonuses - advances - deductions - total_paid
    return {
        'salary': salary,
        'bonuses': bonuses,
        'advances': advances,
        'deductions': deductions,
        'total_paid': total_paid,
        'net': net
    }

def get_weekly_employees_report(sheet):
    names = get_employee_names(sheet)
    report = []
    for name in names:
        data = get_employee_balance(sheet, name)
        if data:
            report.append({'name': name, 'data': data})
    return report

# ============ دوال البنود ============

def get_all_bands(sheet):
    conn = get_db()
    rows = conn.execute("SELECT name FROM bands ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_band(sheet, name):
    conn = get_db()
    try:
        conn.execute("INSERT INTO bands (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_band(sheet, name):
    conn = get_db()
    cur = conn.execute("DELETE FROM bands WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0

# ============ دوال المصروفات ============

def add_masrof_edari(sheet, band, amount):
    today = str(date.today())
    conn = get_db()
    conn.execute(
        "INSERT INTO masrof_edari (band, amount, date) VALUES (?, ?, ?)",
        (band, amount, today)
    )
    conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
                 (today, "صرف", amount, f"مصروفات إدارية: {band}"))
    conn.commit()
    conn.close()

def add_masrof_okhra(sheet, amount, note):
    today = str(date.today())
    conn = get_db()
    conn.execute(
        "INSERT INTO masrof_okhra (amount, note, date) VALUES (?, ?, ?)",
        (amount, note, today)
    )
    conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)",
                 (today, "صرف", amount, f"مصروفات أخرى: {note}"))
    conn.commit()
    conn.close()

def get_monthly_band_report(sheet, band_name):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    rows = conn.execute(
        "SELECT amount FROM masrof_edari WHERE band=? AND date LIKE ?",
        (band_name, f"{month}%")
    ).fetchall()
    conn.close()
    total = sum(r['amount'] for r in rows)
    details = [{'date': f"{month}-{i+1:02d}", 'amount': r['amount']} for i, r in enumerate(rows)]
    return total, details

def get_monthly_masrof_report(sheet):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    # إدارية
    rows_edari = conn.execute(
        "SELECT band, SUM(amount) as total FROM masrof_edari WHERE date LIKE ? GROUP BY band",
        (f"{month}%",)
    ).fetchall()
    bands = {r['band']: r['total'] for r in rows_edari}
    # أخرى
    row_okhra = conn.execute(
        "SELECT SUM(amount) as total FROM masrof_okhra WHERE date LIKE ?",
        (f"{month}%",)
    ).fetchone()
    okhra_total = row_okhra['total'] if row_okhra['total'] else 0
    conn.close()
    return bands, okhra_total

# ============ الملخص ============

def get_full_summary(sheet):
    balance = get_balance(sheet)
    emoji = "📈" if balance >= 0 else "📉"
    msg = f"📊 *ملخص الحسابات*\n\n"
    msg += f"{emoji} *رصيد الخزنة:* {balance} جنيه\n"
    try:
        names = get_all_clients(sheet)
        if names:
            msg += "\n👥 *العملاء:*\n"
            for name in names:
                b = get_person_balance(sheet, "الخزنة_العملاء", name)
                if b > 0:
                    msg += f"  • {name}: عليه {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: ليه عندنا {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass
    try:
        names = get_all_suppliers(sheet)
        if names:
            msg += "\n🏭 *الموردين:*\n"
            for name in names:
                b = get_person_balance(sheet, "الخزنة_الموردين", name)
                if b > 0:
                    msg += f"  • {name}: ليه عندنا {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: دفعنا له زيادة {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass
    return msg

# ============ حذف حركة ============

def get_last_records(table_name, limit=5):
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_last_record(table_name, record_id):
    conn = get_db()
    conn.execute(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

# ============ PDF ============

def generate_pdf_report(name, person_type, transactions, balance):
    import arabic_reshaper
    from bidi.algorithm import get_display

    def ar(text):
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=30)
    elements = []

    title_data = [[ar(f"تاريخ التقرير: {date.today().strftime('%Y-%m-%d')}"),
                   ar(f"تقرير {person_type}: {name}")]]
    title_table = Table(title_data, colWidths=[200, 200])
    title_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 12))

    data = [[ar("المبلغ"), ar("النوع"), ar("التاريخ")]]
    for t in transactions:
        data.append([ar(str(t['amount'])), ar(t['trans_type']), ar(str(t['date']))])

    status = ar("عليه") if balance > 0 else ar("ليه عندنا") if balance < 0 else ar("صفر")
    data.append([ar(str(abs(balance))), status, ar("الرصيد النهائي")])

    table = Table(data, colWidths=[100, 130, 170])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F2F3F4')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#AED6F1')),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
    ]))
    elements.append(table)
    doc.build(elements)
    return tmp.name