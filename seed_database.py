"""
سكريبت لرفع الداتا القديمة من ملفات CSV إلى قاعدة بيانات PostgreSQL على Supabase
شغّل الملف ده مرة واحدة بس من جهازك
"""
import csv
import psycopg2
import psycopg2.extras

# ===== ضع رابط الاتصال بتاع Supabase هنا =====
DATABASE_URL = "postgresql://postgres.egwrylltkkvljceesiza:6vOjz3mBLDfh1QVU@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
# ===============================================

def main():
    print("🔌 جاري الاتصال بقاعدة البيانات...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    c = conn.cursor()
    print("✅ تم الاتصال بنجاح!")

    # ===== 1. إنشاء الجداول =====
    print("\n🔧 إنشاء الجداول...")
    c.execute("""CREATE TABLE IF NOT EXISTS khazna (
        id SERIAL PRIMARY KEY, date TEXT NOT NULL, type TEXT NOT NULL,
        amount REAL NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS persons (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(name, type))""")
    c.execute("""CREATE TABLE IF NOT EXISTS person_transactions (
        id SERIAL PRIMARY KEY, person_name TEXT NOT NULL, person_type TEXT NOT NULL,
        date TEXT NOT NULL, trans_type TEXT NOT NULL, amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, salary REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS employee_transactions (
        id SERIAL PRIMARY KEY, employee_name TEXT NOT NULL, date TEXT NOT NULL,
        trans_type TEXT NOT NULL, amount REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bands (
        id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS masrof_edari (
        id SERIAL PRIMARY KEY, band TEXT NOT NULL, amount REAL NOT NULL,
        date TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS masrof_okhra (
        id SERIAL PRIMARY KEY, amount REAL NOT NULL, note TEXT,
        date TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    print("✅ تم إنشاء الجداول")

    # ===== 2. مسح البيانات القديمة (لو موجودة) =====
    print("\n🗑️ مسح أي بيانات قديمة...")
    for table in ['khazna', 'person_transactions', 'persons', 'employee_transactions', 'employees', 'bands', 'masrof_edari', 'masrof_okhra']:
        c.execute(f"DELETE FROM {table}")
    conn.commit()
    print("✅ تم المسح")

    # ===== 3. إدخال البيانات =====

    # --- persons ---
    print("\n👥 إدخال الأشخاص...")
    count = 0
    with open('persons.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'].strip():
                c.execute("INSERT INTO persons (name, type) VALUES (%s, %s)", (row['name'].strip(), row['type'].strip()))
                count += 1
    print(f"   ✅ {count} شخص")

    # --- employees ---
    print("👷 إدخال الموظفين...")
    count = 0
    with open('employees.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'].strip():
                c.execute("INSERT INTO employees (name, salary) VALUES (%s, %s)", (row['name'].strip(), float(row['salary'])))
                count += 1
    print(f"   ✅ {count} موظف")

    # --- bands ---
    print("📋 إدخال البنود...")
    count = 0
    with open('bands.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'].strip():
                c.execute("INSERT INTO bands (name) VALUES (%s)", (row['name'].strip(),))
                count += 1
    print(f"   ✅ {count} بند")

    # --- khazna ---
    print("💰 إدخال حركات الخزنة...")
    count = 0
    with open('khazna.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date'].strip():
                date_val = row['date'].strip().split(' ')[0]  # أخذ التاريخ فقط بدون الوقت
                # تحويل من M/D/YYYY إلى YYYY-MM-DD
                parts = date_val.split('/')
                if len(parts) == 3:
                    date_formatted = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                else:
                    date_formatted = date_val
                c.execute("INSERT INTO khazna (date, type, amount, description) VALUES (%s, %s, %s, %s)",
                         (date_formatted, row['type'].strip(), float(row['amount']), row['description'].strip()))
                count += 1
    print(f"   ✅ {count} حركة")

    # --- person_transactions ---
    print("📊 إدخال حركات الأشخاص...")
    count = 0
    with open('person_transactions.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['person_name'].strip():
                date_val = row['date'].strip().split(' ')[0]
                parts = date_val.split('/')
                if len(parts) == 3:
                    date_formatted = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                else:
                    date_formatted = date_val
                c.execute("INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (%s, %s, %s, %s, %s)",
                         (row['person_name'].strip(), row['person_type'].strip(), date_formatted, row['trans_type'].strip(), float(row['amount'])))
                count += 1
    print(f"   ✅ {count} حركة")

    # --- employee_transactions ---
    print("👷 إدخال حركات الموظفين...")
    count = 0
    with open('employee_transactions.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['employee_name'].strip():
                date_val = row['date'].strip().split(' ')[0]
                parts = date_val.split('/')
                if len(parts) == 3:
                    date_formatted = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                else:
                    date_formatted = date_val
                c.execute("INSERT INTO employee_transactions (employee_name, date, trans_type, amount) VALUES (%s, %s, %s, %s)",
                         (row['employee_name'].strip(), date_formatted, row['trans_type'].strip(), float(row['amount'])))
                count += 1
    print(f"   ✅ {count} حركة")

    # --- masrof_edari ---
    print("🏢 إدخال المصروفات الإدارية...")
    count = 0
    with open('masrof_edari.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['band'].strip():
                date_val = row['date'].strip().split(' ')[0]
                parts = date_val.split('/')
                if len(parts) == 3:
                    date_formatted = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                else:
                    date_formatted = date_val
                c.execute("INSERT INTO masrof_edari (band, amount, date) VALUES (%s, %s, %s)",
                         (row['band'].strip(), float(row['amount']), date_formatted))
                count += 1
    print(f"   ✅ {count} مصروف")

    # --- masrof_okhra ---
    print("📝 إدخال المصروفات الأخرى...")
    count = 0
    with open('masrof_okhra.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['note'].strip() or row['amount'].strip():
                date_val = row['date'].strip().split(' ')[0]
                parts = date_val.split('/')
                if len(parts) == 3:
                    date_formatted = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                else:
                    date_formatted = date_val
                c.execute("INSERT INTO masrof_okhra (amount, note, date) VALUES (%s, %s, %s)",
                         (float(row['amount']), row['note'].strip(), date_formatted))
                count += 1
    print(f"   ✅ {count} مصروف")

    # ===== 4. حفظ كل شيء =====
    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print("🎉 تم رفع كل البيانات بنجاح!")
    print("=" * 50)

if __name__ == "__main__":
    main()
