import sqlite3
import os
import csv
from datetime import datetime
from database import get_db, init_db

# Initialize database
init_db()

# CSV files to import - place these files in the same directory
CSV_FILES = {
    'persons': 'persons.csv',  # Columns: name,type
    'khazna': 'khazna.csv',    # Columns: date,type,amount,description
    'person_transactions': 'person_transactions.csv',  # Columns: person_name,person_type,date,trans_type,amount
    'employees': 'employees.csv',  # Columns: name,salary
    'employee_transactions': 'employee_transactions.csv',  # Columns: employee_name,date,trans_type,amount
    'bands': 'bands.csv',      # Columns: name
    'masrof_edari': 'masrof_edari.csv',  # Columns: date,band,amount
    'masrof_okhra': 'masrof_okhra.csv',  # Columns: date,amount,note
}

def parse_date(date_str):
    """Parse date from various formats to YYYY-MM-DD"""
    try:
        # Try MM/DD/YYYY HH:MM format
        dt = datetime.strptime(date_str, '%m/%d/%Y %H:%M')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try MM/DD/YYYY format
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            # If already YYYY-MM-DD, return as is
            return date_str

def import_from_csv():
    conn = get_db()
    try:
        for table, filename in CSV_FILES.items():
            if not os.path.exists(filename):
                print(f"⚠️ ملف {filename} غير موجود، تم تخطيه")
                continue

            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Skip header
                data = list(reader)

            if not data:
                print(f"⚠️ ملف {filename} فارغ")
                continue

            imported_count = 0
            for row in data:
                if table == 'persons':
                    conn.execute("INSERT OR IGNORE INTO persons (name, type) VALUES (?, ?)", row)
                elif table == 'khazna':
                    # Convert date
                    row[0] = parse_date(row[0])
                    conn.execute("INSERT INTO khazna (date, type, amount, description) VALUES (?, ?, ?, ?)", row)
                elif table == 'person_transactions':
                    # Convert date
                    row[2] = parse_date(row[2])
                    conn.execute("INSERT INTO person_transactions (person_name, person_type, date, trans_type, amount) VALUES (?, ?, ?, ?, ?)", row)
                elif table == 'employees':
                    conn.execute("INSERT OR IGNORE INTO employees (name, salary) VALUES (?, ?)", row)
                elif table == 'employee_transactions':
                    # Convert date
                    row[1] = parse_date(row[1])
                    conn.execute("INSERT INTO employee_transactions (employee_name, date, trans_type, amount) VALUES (?, ?, ?, ?)", row)
                elif table == 'bands':
                    conn.execute("INSERT OR IGNORE INTO bands (name) VALUES (?)", row)
                elif table == 'masrof_edari':
                    # Convert date
                    row[0] = parse_date(row[0])
                    conn.execute("INSERT INTO masrof_edari (date, band, amount) VALUES (?, ?, ?)", row)
                elif table == 'masrof_okhra':
                    # Convert date
                    row[0] = parse_date(row[0])
                    conn.execute("INSERT INTO masrof_okhra (date, amount, note) VALUES (?, ?, ?)", row)
                imported_count += 1

            print(f"✅ تم استيراد {imported_count} سجل من {filename}")

        conn.commit()
        print("🎉 تم استيراد جميع البيانات بنجاح!")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ في الاستيراد: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import_from_csv()