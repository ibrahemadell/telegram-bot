import sqlite3
import os
from database import get_db, init_db

# Initialize database
init_db()

# Data to import - EDIT THESE LISTS WITH YOUR DATA

# 1. Persons (clients and suppliers)
persons_data = [
    # Format: (name, type) - type is 'عميل' or 'مورد'
    # Example:
    # ("أحمد محمد", "عميل"),
    # ("شركة XYZ", "مورد"),
]

# 2. Khazna (treasury transactions)
khazna_data = [
    # Format: (date, type, amount, description) - type is 'دخل' or 'صرف'
    # Example:
    # ("2024-01-01", "دخل", 1000, "دخل من عميل"),
    # ("2024-01-02", "صرف", 500, "شراء مواد"),
]

# 3. Person transactions (client/supplier payments)
person_transactions_data = [
    # Format: (person_name, person_type, date, trans_type, amount)
    # trans_type: 'مديونية' (debt) or 'دفع' (payment)
    # Example:
    # ("أحمد محمد", "عميل", "2024-01-01", "مديونية", 500),
    # ("أحمد محمد", "عميل", "2024-01-05", "دفع", 200),
]

# 4. Employees
employees_data = [
    # Format: (name, salary)
    # Example:
    # ("محمد علي", 3000),
]

# 5. Employee transactions
employee_transactions_data = [
    # Format: (employee_name, date, trans_type, amount)
    # trans_type: 'مرتب', 'سلفة', etc.
    # Example:
    # ("محمد علي", "2024-01-01", "مرتب", 3000),
]

# 6. Bands (expense categories)
bands_data = [
    # Format: (name,)
    # Example:
    # ("إيجار",),
    # ("كهرباء",),
]

# 7. Masrof Edari (administrative expenses)
masrof_edari_data = [
    # Format: (date, band, amount)
    # Example:
    # ("2024-01-01", "إيجار", 1000),
]

# 8. Masrof Okhra (other expenses)
masrof_okhra_data = [
    # Format: (date, amount, note)
    # Example:
    # ("2024-01-01", 500, "شراء أدوات"),
]

def import_data():
    conn = get_db()
    try:
        # Import persons
        for data in persons_data:
            conn.execute("INSERT OR IGNORE INTO persons (name, type) VALUES (?, ?)", data)
        print(f"✅ تم استيراد {len(persons_data)} شخص")

        # Import khazna
        for data in khazna_data:
            conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)", data)
        print(f"✅ تم استيراد {len(khazna_data)} حركة خزنة")

        # Import person transactions
        for data in person_transactions_data:
            conn.execute("INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (?, ?, ?, ?, ?)", data)
        print(f"✅ تم استيراد {len(person_transactions_data)} حركة أشخاص")

        # Import employees
        for data in employees_data:
            conn.execute("INSERT OR IGNORE INTO employees (name, salary) VALUES (?, ?)", data)
        print(f"✅ تم استيراد {len(employees_data)} موظف")

        # Import employee transactions
        for data in employee_transactions_data:
            conn.execute("INSERT INTO employee_transactions (employee_name, date, trans_type, amount) VALUES (?, ?, ?, ?)", data)
        print(f"✅ تم استيراد {len(employee_transactions_data)} حركة موظفين")

        # Import bands
        for data in bands_data:
            conn.execute("INSERT OR IGNORE INTO bands (name) VALUES (?)", data)
        print(f"✅ تم استيراد {len(bands_data)} بند")

        # Import masrof edari
        for data in masrof_edari_data:
            conn.execute("INSERT INTO masrof_edari (date, band, amount) VALUES (?, ?, ?)", data)
        print(f"✅ تم استيراد {len(masrof_edari_data)} مصروف إداري")

        # Import masrof okhra
        for data in masrof_okhra_data:
            conn.execute("INSERT INTO masrof_okhra (date, amount, note) VALUES (?, ?, ?)", data)
        print(f"✅ تم استيراد {len(masrof_okhra_data)} مصروف آخر")

        conn.commit()
        print("🎉 تم استيراد جميع البيانات بنجاح!")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ في الاستيراد: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import_data()