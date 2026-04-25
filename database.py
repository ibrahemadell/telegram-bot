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

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    print("Connecting to PostgreSQL database...")
    try:
        conn = get_db()
        c = conn.cursor()

        # === جداول جديدة ===
        c.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                dashboard_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_users (
                telegram_id BIGINT PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # === الجداول الموجودة ===
        c.execute("""
            CREATE TABLE IF NOT EXISTS khazna (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS person_transactions (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                person_name TEXT NOT NULL,
                person_type TEXT NOT NULL,
                date TEXT NOT NULL,
                trans_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                name TEXT NOT NULL,
                salary REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS employee_transactions (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                employee_name TEXT NOT NULL,
                date TEXT NOT NULL,
                trans_type TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("ALTER TABLE employee_transactions ADD COLUMN IF NOT EXISTS note TEXT DEFAULT ''")
        c.execute("""
            CREATE TABLE IF NOT EXISTS bands (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS masrof_edari (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                band TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS masrof_okhra (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                amount REAL NOT NULL,
                note TEXT,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # === Migration: اضافة company_id للجداول القديمة ===
        tables = ['khazna', 'persons', 'person_transactions', 'employees',
                  'employee_transactions', 'bands', 'masrof_edari', 'masrof_okhra']
        for t in tables:
            c.execute(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id)")

        # === الشركة الافتراضية ===
        c.execute("INSERT INTO companies (name, dashboard_password) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                  ("الشركة الرئيسية", "admin123"))

        # === ترحيل البيانات للشركة 1 ===
        c.execute("SELECT id FROM companies WHERE name = %s", ("الشركة الرئيسية",))
        default_company = c.fetchone()
        if default_company:
            cid = default_company['id']
            for t in tables:
                c.execute(f"UPDATE {t} SET company_id = %s WHERE company_id IS NULL", (cid,))

        # === تعديل Unique Constraints ===
        c.execute("ALTER TABLE persons DROP CONSTRAINT IF EXISTS persons_name_type_key")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS persons_name_type_company_idx ON persons(name, type, company_id)")

        c.execute("ALTER TABLE employees DROP CONSTRAINT IF EXISTS employees_name_key")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS employees_name_company_idx ON employees(name, company_id)")

        c.execute("ALTER TABLE bands DROP CONSTRAINT IF EXISTS bands_name_key")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS bands_name_company_idx ON bands(name, company_id)")

        conn.commit()
        conn.close()
        print("قاعدة البيانات جاهزة (Multi-Tenant)")
    except Exception as e:
        print(f"Database error: {e}")
        raise

# ============ الشركات والمستخدمين ============

def get_user_company_id(telegram_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT company_id FROM bot_users WHERE telegram_id=%s", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row['company_id'] if row else None

def add_company(name, password):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO companies (name, dashboard_password) VALUES (%s, %s) RETURNING id", (name, password))
        row = c.fetchone()
        conn.commit()
        conn.close()
        return row['id']
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return None

def get_all_companies():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.name, c.dashboard_password,
               COUNT(b.telegram_id) as user_count
        FROM companies c
        LEFT JOIN bot_users b ON c.id = b.company_id
        GROUP BY c.id, c.name, c.dashboard_password
        ORDER BY c.id
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_user_to_company(telegram_id, company_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO bot_users (telegram_id, company_id) VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET company_id = EXCLUDED.company_id
        """, (telegram_id, company_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.rollback()
        conn.close()
        return False

def remove_user_from_company(telegram_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bot_users WHERE telegram_id=%s", (telegram_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def authenticate_company(company_name, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name FROM companies WHERE name=%s AND dashboard_password=%s", (company_name, password))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_company_users(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM bot_users WHERE company_id=%s", (company_id,))
    rows = c.fetchall()
    conn.close()
    return [r['telegram_id'] for r in rows]

# ============ الخزنة ============

def add_transaction(trans_type, amount, description, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
        (str(date.today()), trans_type, amount, description, company_id)
    )
    conn.commit()
    conn.close()

def get_balance(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as balance
        FROM khazna WHERE company_id=%s
    """, (company_id,))
    row = c.fetchone()
    conn.close()
    return float(row['balance']) if row else 0

def get_daily_khazna_report(selected_date, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT date, type, amount, description FROM khazna WHERE date=%s AND company_id=%s ORDER BY created_at",
        (selected_date, company_id)
    )
    records = [dict(r) for r in c.fetchall()]
    total_in = sum(r['amount'] for r in records if r['type'] == 'دخل')
    total_out = sum(r['amount'] for r in records if r['type'] == 'صرف')
    conn.close()
    return records, total_in, total_out

def get_monthly_khazna_report(company_id):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='دخل' THEN amount ELSE 0 END), 0) as total_in,
            COALESCE(SUM(CASE WHEN type='صرف' THEN amount ELSE 0 END), 0) as total_out
        FROM khazna WHERE date LIKE %s AND company_id=%s
    """, (f"{month}%", company_id))
    row = c.fetchone()
    conn.close()
    return (float(row['total_in']), float(row['total_out'])) if row else (0, 0)


# ============ العملاء والموردين ============

def add_person(name, person_type, company_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO persons (name, type, company_id) VALUES (%s, %s, %s)", (name, person_type, company_id))
        conn.commit()
        conn.close()
        return True
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return False

def delete_person(name, person_type, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE name=%s AND type=%s AND company_id=%s", (name, person_type, company_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_all_clients(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM persons WHERE type='عميل' AND company_id=%s ORDER BY name", (company_id,))
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def get_all_suppliers(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM persons WHERE type='مورد' AND company_id=%s ORDER BY name", (company_id,))
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_client(name, amount, trans_type, company_id):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount, company_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, "عميل", today, trans_type, amount, company_id)
    )
    if trans_type == "دفع":
        c.execute("INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
                  (today, "دخل", amount, f"دفعة من عميل: {name}", company_id))
    conn.commit()
    conn.close()

def add_supplier(name, amount, trans_type, company_id):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount, company_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, "مورد", today, trans_type, amount, company_id)
    )
    if trans_type == "دفع":
        c.execute("INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
                  (today, "صرف", amount, f"دفعة لمورد: {name}", company_id))
    conn.commit()
    conn.close()

def get_person_balance(person_type, name, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN trans_type IN ('دين','مديونية') THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN trans_type IN ('دفع','خصم') THEN amount ELSE 0 END), 0) as balance
        FROM person_transactions
        WHERE person_name=%s AND person_type=%s AND company_id=%s
    """, (name, person_type, company_id))
    row = c.fetchone()
    conn.close()
    return float(row['balance']) if row else 0

def get_person_transactions(name, person_type, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT date, trans_type as type, amount FROM person_transactions WHERE person_name=%s AND person_type=%s AND company_id=%s ORDER BY created_at",
        (name, person_type, company_id)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_clients_total(company_id):
    names = get_all_clients(company_id)
    total = 0
    details = []
    for name in names:
        b = get_person_balance("عميل", name, company_id)
        if b > 0:
            total += b
            details.append(f"  • {name}: {b} جنيه")
    return total, details

def get_suppliers_total(company_id):
    names = get_all_suppliers(company_id)
    total = 0
    details = []
    for name in names:
        b = get_person_balance("مورد", name, company_id)
        if b > 0:
            total += b
            details.append(f"  • {name}: {b} جنيه")
    return total, details

# ============ الموظفين ============

def get_all_employees(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, salary FROM employees WHERE company_id=%s ORDER BY name", (company_id,))
    rows = c.fetchall()
    conn.close()
    return [(r['name'], float(r['salary'])) for r in rows]

def get_employee_names(company_id):
    return [e[0] for e in get_all_employees(company_id)]

def add_employee(name, weekly_salary, company_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO employees (name, salary, company_id) VALUES (%s, %s, %s)", (name, weekly_salary, company_id))
        conn.commit()
        conn.close()
        return True
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return False

def delete_employee(name, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE name=%s AND company_id=%s", (name, company_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def add_employee_transaction(name, trans_type, amount, company_id, note=""):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO employee_transactions (employee_name, date, trans_type, amount, note, company_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, today, trans_type, amount, note, company_id)
    )
    if trans_type in ["مرتب", "مكافأة", "سلفة"]:
        c.execute("INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
                  (today, "صرف", amount, f"{trans_type} موظف: {name}", company_id))
    conn.commit()
    conn.close()

def get_employee_balance(name, company_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT salary FROM employees WHERE name=%s AND company_id=%s", (name, company_id))
    emp = c.fetchone()
    if not emp:
        conn.close()
        return None
    salary = float(emp['salary'])

    today = date.today()
    days_since_saturday = (today.weekday() - 5) % 7
    week_start = today - timedelta(days=days_since_saturday)
    week_start_str = week_start.strftime("%Y-%m-%d")

    c.execute(
        "SELECT date, trans_type, amount FROM employee_transactions WHERE employee_name=%s AND company_id=%s ORDER BY created_at",
        (name, company_id)
    )
    all_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if not all_rows:
        weeks_count = 1
        total_salary_due = salary
        total_paid = 0
        bonuses = 0
        advances = 0
        deductions = 0
        net = salary
        return {
            'salary': salary,
            'weeks': weeks_count,
            'total_salary_due': total_salary_due,
            'bonuses': bonuses,
            'advances': advances,
            'deductions': deductions,
            'total_paid': total_paid,
            'net': net,
            'carryover': 0
        }

    first_date = date.fromisoformat(all_rows[0]['date'])
    days_since_sat = (first_date.weekday() - 5) % 7
    first_week_start = first_date - timedelta(days=days_since_sat)

    carryover = 0.0
    current_week = first_week_start
    all_weeks = []
    while current_week <= week_start:
        all_weeks.append(current_week)
        current_week += timedelta(weeks=1)

    weeks_count = len(all_weeks)

    current_week_rows = [r for r in all_rows if r['date'] >= week_start_str]
    prev_rows = [r for r in all_rows if r['date'] < week_start_str]

    running_carryover = 0.0

    for i, wk_start in enumerate(all_weeks[:-1]):
        wk_end = wk_start + timedelta(days=6)
        wk_end_str = wk_end.strftime("%Y-%m-%d")
        wk_start_str_loop = wk_start.strftime("%Y-%m-%d")

        wk_rows = [r for r in all_rows if wk_start_str_loop <= r['date'] <= wk_end_str]

        wk_paid = sum(r['amount'] for r in wk_rows if r['trans_type'] == 'مرتب')
        wk_bonuses = sum(r['amount'] for r in wk_rows if r['trans_type'] == 'مكافأة')
        wk_advances = sum(r['amount'] for r in wk_rows if r['trans_type'] == 'سلفة')
        wk_deductions = sum(r['amount'] for r in wk_rows if r['trans_type'] == 'خصم')

        wk_balance = salary + running_carryover + wk_bonuses - wk_advances - wk_deductions - wk_paid
        running_carryover = wk_balance

    cur_rows = [r for r in all_rows if r['date'] >= week_start_str]
    cur_paid = sum(r['amount'] for r in cur_rows if r['trans_type'] == 'مرتب')
    cur_bonuses = sum(r['amount'] for r in cur_rows if r['trans_type'] == 'مكافأة')
    cur_advances = sum(r['amount'] for r in cur_rows if r['trans_type'] == 'سلفة')
    cur_deductions = sum(r['amount'] for r in cur_rows if r['trans_type'] == 'خصم')

    current_week_due = salary + running_carryover + cur_bonuses - cur_advances - cur_deductions - cur_paid

    total_paid = sum(r['amount'] for r in all_rows if r['trans_type'] == 'مرتب')
    bonuses = sum(r['amount'] for r in all_rows if r['trans_type'] == 'مكافأة')
    advances = sum(r['amount'] for r in all_rows if r['trans_type'] == 'سلفة')
    deductions = sum(r['amount'] for r in all_rows if r['trans_type'] == 'خصم')

    return {
        'salary': salary,
        'weeks': weeks_count,
        'total_salary_due': salary * weeks_count,
        'bonuses': cur_bonuses,
        'advances': cur_advances,
        'deductions': cur_deductions,
        'total_paid': total_paid,
        'cur_paid': cur_paid,
        'net': current_week_due,
        'carryover': running_carryover
    }

def get_weekly_employees_report(company_id):
    names = get_employee_names(company_id)
    report = []
    for name in names:
        data = get_employee_balance(name, company_id)
        if data:
            report.append({'name': name, 'data': data})
    return report

# ============ البنود ============

def get_all_bands(company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM bands WHERE company_id=%s ORDER BY name", (company_id,))
    rows = c.fetchall()
    conn.close()
    return [r['name'] for r in rows]

def add_band(name, company_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO bands (name, company_id) VALUES (%s, %s)", (name, company_id))
        conn.commit()
        conn.close()
        return True
    except (psycopg2.errors.UniqueViolation, psycopg2.IntegrityError):
        conn.rollback()
        conn.close()
        return False

def delete_band(name, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bands WHERE name=%s AND company_id=%s", (name, company_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# ============ المصروفات ============

def add_masrof_edari(band, amount, company_id):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO masrof_edari (band, amount, date, company_id) VALUES (%s, %s, %s, %s)", (band, amount, today, company_id))
    c.execute("INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
              (today, "صرف", amount, f"مصروفات إدارية: {band}", company_id))
    conn.commit()
    conn.close()

def add_masrof_okhra(amount, note, company_id):
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO masrof_okhra (amount, note, date, company_id) VALUES (%s, %s, %s, %s)", (amount, note, today, company_id))
    c.execute("INSERT INTO khazna (date, type, amount, description, company_id) VALUES (%s, %s, %s, %s, %s)",
              (today, "صرف", amount, f"مصروفات أخرى: {note}", company_id))
    conn.commit()
    conn.close()

def get_monthly_band_report(band_name, company_id):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT date, amount FROM masrof_edari WHERE band=%s AND date LIKE %s AND company_id=%s ORDER BY date",
        (band_name, f"{month}%", company_id)
    )
    rows = c.fetchall()
    conn.close()
    total = sum(r['amount'] for r in rows)
    details = [{'date': r['date'], 'amount': r['amount']} for r in rows]
    return total, details

def get_monthly_masrof_report(company_id):
    month = date.today().strftime("%Y-%m")
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT band, SUM(amount) as total FROM masrof_edari WHERE date LIKE %s AND company_id=%s GROUP BY band",
        (f"{month}%", company_id)
    )
    rows_edari = c.fetchall()
    bands = {r['band']: r['total'] for r in rows_edari}
    c.execute("SELECT SUM(amount) as total FROM masrof_okhra WHERE date LIKE %s AND company_id=%s", (f"{month}%", company_id))
    row_okhra = c.fetchone()
    okhra_total = float(row_okhra['total']) if row_okhra and row_okhra['total'] else 0
    conn.close()
    return bands, okhra_total

# ============ الملخص ============

def get_full_summary(company_id):
    balance = get_balance(company_id)
    emoji = "📈" if balance >= 0 else "📉"
    msg = f"📊 *ملخص الحسابات*\n\n"
    msg += f"{emoji} *رصيد الخزنة:* {balance} جنيه\n"
    try:
        names = get_all_clients(company_id)
        if names:
            msg += "\n👥 *العملاء:*\n"
            for name in names:
                b = get_person_balance("عميل", name, company_id)
                if b > 0:
                    msg += f"  • {name}: عليه {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: ليه عندنا {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass
    try:
        names = get_all_suppliers(company_id)
        if names:
            msg += "\n🏭 *الموردين:*\n"
            for name in names:
                b = get_person_balance("مورد", name, company_id)
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

def get_last_records(table_name, company_id, limit=5, person_type=None):
    conn = get_db()
    c = conn.cursor()
    if person_type and table_name == "person_transactions":
        c.execute(
            "SELECT * FROM person_transactions WHERE person_type=%s AND company_id=%s ORDER BY id DESC LIMIT %s",
            (person_type, company_id, limit)
        )
    else:
        c.execute(f"SELECT * FROM {table_name} WHERE company_id=%s ORDER BY id DESC LIMIT %s", (company_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_last_record(table_name, record_id, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"DELETE FROM {table_name} WHERE id=%s AND company_id=%s", (record_id, company_id))
    conn.commit()
    conn.close()

# ============ PDF ============

def generate_pdf_report(name, person_type, transactions, balance):
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab غير متاح")

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
    from reportlab.lib import colors
    import arabic_reshaper
    from bidi.algorithm import get_display

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
