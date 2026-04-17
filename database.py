import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime, timedelta

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import tempfile
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ============ إعداد قاعدة البيانات ============

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable is required")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    print(f"🔍 Connecting to PostgreSQL database...")
    try:
        conn = get_db()
        c = conn.cursor()
        print("🔧 Creating tables...")

        # جدول الخزنة
        c.execute("""
            CREATE TABLE IF NOT EXISTS khazna (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ khazna table ready")

        # جدول الأشخاص (عملاء + موردين)
        c.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type)
            )
        """)
        print("✅ persons table ready")

        # جدول حركات الأشخاص
        c.execute("""
            CREATE TABLE IF NOT EXISTS person_transactions (
                id SERIAL PRIMARY KEY,
                person_name TEXT NOT NULL,
                person_type TEXT NOT NULL,
                date TEXT NOT NULL,
                trans_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ person_transactions table ready")

        # جدول الموظفين
        c.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                salary REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ employees table ready")

        # جدول حركات الموظفين
        c.execute("""
            CREATE TABLE IF NOT EXISTS employee_transactions (
                id SERIAL PRIMARY KEY,
                employee_name TEXT NOT NULL,
                date TEXT NOT NULL,
                trans_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ employee_transactions table ready")

        # جدول البنود
        c.execute("""
            CREATE TABLE IF NOT EXISTS bands (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ bands table ready")

        # جدول المصروفات الإدارية
        c.execute("""
            CREATE TABLE IF NOT EXISTS masrof_edari (
                id SERIAL PRIMARY KEY,
                band TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ masrof_edari table ready")

        # جدول المصروفات الأخرى
        c.execute("""
            CREATE TABLE IF NOT EXISTS masrof_okhra (
                id SERIAL PRIMARY KEY,
                amount REAL NOT NULL,
                note TEXT,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ masrof_okhra table ready")

        conn.commit()
        conn.close()
        print("✅ قاعدة البيانات جاهزة")
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise

# ============ دوال الخزنة ============

def add_transaction(trans_type, amount, description):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
        (str(date.today()), trans_type, amount, description)
    )
    conn.commit()
    conn.close()

def get_balance():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as balance
        FROM khazna
    """)
    row = c.fetchone()
    conn.close()
    return row['balance'] if row else 0

def get_daily_khazna_report(selected_date):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT date, type, amount, description FROM khazna WHERE date = %s ORDER BY created_at",
        (selected_date,)
    )
    records = [dict(r) for r in c.fetchall()]
    total_in = sum(r['amount'] for r in records if r['type'] == 'دخل')
    total_out = sum(r['amount'] for r in records if r['type'] == 'صرف')
    conn.close()
    return records, total_in, total_out

def get_monthly_khazna_report():
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) as total_in,
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as total_out
        FROM khazna WHERE date LIKE %s
    """, (f"{month}%",))
    row = c.fetchone()
    conn.close()
    return (row['total_in'], row['total_out']) if row else (0, 0)

# ============ دوال الأشخاص (عملاء / موردين) ============

def add_person(name, person_type):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO persons (name, type) VALUES (%s, %s)", (name, person_type))
        conn.commit()
        conn.close()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        conn.close()
        return False
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return False

def delete_person(name, person_type):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE name=%s AND type=%s", (name, person_type))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_all_clients():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM persons WHERE type='عميل' ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def get_all_suppliers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM persons WHERE type='مورد' ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_client(name, amount, trans_type):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (%s, %s, %s, %s, %s)",
        (name, "عميل", today, trans_type, amount)
    )
    if trans_type == "دفع":
        c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
                  (today, "دخل", amount, f"دفعة من عميل: {name}"))
    conn.commit()
    conn.close()

def add_supplier(name, amount, trans_type):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (%s, %s, %s, %s, %s)",
        (name, "مورد", today, trans_type, amount)
    )
    if trans_type == "دفع":
        c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
                  (today, "صرف", amount, f"دفع لمورد: {name}"))
    conn.commit()
    conn.close()

def get_person_balance(person_type, name):
    if person_type == "الخزنة_العملاء":
        person_type = "عميل"
    elif person_type == "الخزنة_الموردين":
        person_type = "مورد"

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT trans_type, amount FROM person_transactions WHERE person_name=%s AND person_type=%s",
        (name, person_type)
    )
    rows = c.fetchall()
    conn.close()
    balance = 0
    for r in rows:
        if person_type == "عميل":
            if r['trans_type'] == 'دين':
                balance += r['amount']
            elif r['trans_type'] == 'دفع':
                balance -= r['amount']
        elif person_type == "مورد":
            if r['trans_type'] == 'مديونية':
                balance += r['amount']
            elif r['trans_type'] == 'دفع':
                balance -= r['amount']
    return balance

def get_clients_total():
    names = get_all_clients()
    details = []
    total = 0
    for name in names:
        b = get_person_balance("عميل", name)
        if b != 0:
            details.append(f"👤 {name}: {b} جنيه")
            total += b
    return total, details

def get_suppliers_total():
    names = get_all_suppliers()
    details = []
    total = 0
    for name in names:
        b = get_person_balance("مورد", name)
        if b != 0:
            details.append(f"🏭 {name}: {b} جنيه")
            total += b
    return total, details

def get_person_transactions(name, person_type):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT date, trans_type as type, amount FROM person_transactions WHERE person_name=%s AND person_type=%s ORDER BY date",
        (name, person_type)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ============ دوال الموظفين ============

def add_employee(name, salary):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO employees (name, salary) VALUES (%s, %s)", (name, salary))
        conn.commit()
        conn.close()
        return True
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return False

def delete_employee(name):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE name=%s", (name,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_all_employees():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM employees ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee_names():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM employees ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_employee_transaction(name, trans_type, amount):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO employee_transactions (employee_name, date, trans_type, amount) VALUES (%s, %s, %s, %s)",
        (name, today, trans_type, amount)
    )
    if trans_type in ["مرتب", "سلفة"]:
        c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
                  (today, "صرف", amount, f"{trans_type} موظف: {name}"))
    conn.commit()
    conn.close()

def get_employee_balance(name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT salary FROM employees WHERE name=%s", (name,))
    emp = c.fetchone()
    if not emp:
        conn.close()
        return None

    today = date.today()
    days_since_saturday = (today.weekday() - 5) % 7
    week_start = str(today - timedelta(days=days_since_saturday))

    c.execute(
        "SELECT trans_type, amount FROM employee_transactions WHERE employee_name=%s AND date >= %s",
        (name, week_start)
    )
    rows = c.fetchall()
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

def get_weekly_employees_report():
    names = get_employee_names()
    report = []
    for name in names:
        data = get_employee_balance(name)
        if data:
            report.append({'name': name, 'data': data})
    return report

# ============ دوال البنود ============

def get_all_bands():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM bands ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_band(name):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO bands (name) VALUES (%s)", (name,))
        conn.commit()
        conn.close()
        return True
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return False

def delete_band(name):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bands WHERE name=%s", (name,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# ============ دوال المصروفات ============

def add_masrof_edari(band, amount):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO masrof_edari (band, amount, date) VALUES (%s, %s, %s)",
        (band, amount, today)
    )
    c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
              (today, "صرف", amount, f"مصروفات إدارية: {band}"))
    conn.commit()
    conn.close()

def add_masrof_okhra(amount, note):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO masrof_okhra (amount, note, date) VALUES (%s, %s, %s)",
        (amount, note, today)
    )
    c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
              (today, "صرف", amount, f"مصروفات أخرى: {note}"))
    conn.commit()
    conn.close()

def get_monthly_band_report(band_name):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT amount FROM masrof_edari WHERE band=%s AND date LIKE %s",
        (band_name, f"{month}%")
    )
    rows = c.fetchall()
    conn.close()
    total = sum(r['amount'] for r in rows)
    details = [{'date': f"{month}-{i+1:02d}", 'amount': r['amount']} for i, r in enumerate(rows)]
    return total, details

def get_monthly_masrof_report():
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT band, SUM(amount) as total FROM masrof_edari WHERE date LIKE %s GROUP BY band",
        (f"{month}%",)
    )
    rows_edari = c.fetchall()
    bands = {r['band']: r['total'] for r in rows_edari}
    c.execute(
        "SELECT SUM(amount) as total FROM masrof_okhra WHERE date LIKE %s",
        (f"{month}%",)
    )
    row_okhra = c.fetchone()
    okhra_total = row_okhra['total'] if row_okhra and row_okhra['total'] else 0
    conn.close()
    return bands, okhra_total

# ============ الملخص ============

def get_full_summary():
    balance = get_balance()
    emoji = "📈" if balance >= 0 else "📉"
    msg = f"📊 *ملخص الحسابات*\n\n"
    msg += f"{emoji} *رصيد الخزنة:* {balance} جنيه\n"
    try:
        names = get_all_clients()
        if names:
            msg += "\n👥 *العملاء:*\n"
            for name in names:
                b = get_person_balance("عميل", name)
                if b > 0:
                    msg += f"  • {name}: عليه {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: ليه عندنا {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass
    try:
        names = get_all_suppliers()
        if names:
            msg += "\n🏭 *الموردين:*\n"
            for name in names:
                b = get_person_balance("مورد", name)
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

def get_last_records(table_name, limit=5, person_type=None):
    conn = get_db()
    c = conn.cursor()
    if person_type and table_name == "person_transactions":
        c.execute(
            "SELECT * FROM person_transactions WHERE person_type=%s ORDER BY id DESC LIMIT %s",
            (person_type, limit)
        )
    else:
        c.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT %s", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_last_record(table_name, record_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"DELETE FROM {table_name} WHERE id=%s", (record_id,))
    conn.commit()
    conn.close()

# ============ PDF ============

def generate_pdf_report(name, person_type, transactions, balance):
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is not installed. Cannot generate PDF reports.")

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
    from reportlab.lib import colors
    import arabic_reshaper
    from bidi.algorithm import get_display

    # تسجيل الخط العربي
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Amiri-Regular.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Amiri', font_path))
        arabic_font = 'Amiri'
    else:
        arabic_font = 'Helvetica'

    def ar(text):
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except:
            return str(text)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=30)
    elements = []

    title_data = [[ar(f"تاريخ التقرير: {date.today().strftime('%Y-%m-%d')}"),
                   ar(f"تقرير {person_type}: {name}")]]
    title_table = Table(title_data, colWidths=[200, 200])
    title_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), arabic_font),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 12))

    data = [[ar("المبلغ"), ar("النوع"), ar("التاريخ")]]
    for t in transactions:
        data.append([ar(str(t['amount'])), ar(t['type']), ar(str(t['date']))])

    status = ar("عليه") if balance > 0 else ar("ليه عندنا") if balance < 0 else ar("صفر")
    data.append([ar(str(abs(balance))), status, ar("الرصيد النهائي")])

    table = Table(data, colWidths=[100, 130, 170])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), arabic_font),
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