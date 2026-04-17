import gspread
import sqlite3
import os
from datetime import datetime
from google.oauth2.service_account import Credentials

# Database path
DB_PATH = os.environ.get("DB_PATH", "/app/data/bot.db")

# Google Sheets credentials
CREDENTIALS_PATH = os.environ.get("CREDENTIALS_PATH", "credentials.json")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def connect_to_sheets():
    """Connect to Google Sheets"""
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ ملف الاعتمادات غير موجود: {CREDENTIALS_PATH}")
        return None

    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH)
        gc = gspread.authorize(creds)
        print("✅ تم الاتصال بـ Google Sheets")
        return gc
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Google Sheets: {e}")
        return None

def import_khazna_data(gc, spreadsheet_name="Bot Data"):
    """Import treasury data from Google Sheets"""
    try:
        sh = gc.open(spreadsheet_name)
        worksheet = sh.worksheet("الخزنة")

        # Get all data
        data = worksheet.get_all_values()
        if len(data) <= 1:  # Only header or empty
            print("⚠️ لا توجد بيانات في ورقة الخزنة")
            return

        conn = get_db()
        c = conn.cursor()

        imported_count = 0
        for row in data[1:]:  # Skip header
            if len(row) >= 4:  # date, type, amount, description
                try:
                    # Convert date format if needed
                    date_str = row[0].strip()
                    if date_str:
                        # Try to parse different date formats
                        try:
                            # If it's already in YYYY-MM-DD format
                            datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError:
                            # Try DD/MM/YYYY format
                            try:
                                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                                date_str = date_obj.strftime('%Y-%m-%d')
                            except ValueError:
                                print(f"⚠️ تاريخ غير صحيح: {date_str}, سيتم تجاهله")
                                continue

                        trans_type = row[1].strip()
                        amount_str = row[2].strip().replace(',', '').replace(' ', '')
                        description = row[3].strip() if len(row) > 3 else ""

                        try:
                            amount = float(amount_str)
                        except ValueError:
                            print(f"⚠️ مبلغ غير صحيح: {amount_str}, سيتم تجاهله")
                            continue

                        # Insert into database
                        c.execute("""
                            INSERT INTO khazna (date, type, amount, description)
                            VALUES (?, ?, ?, ?)
                        """, (date_str, trans_type, amount, description))
                        imported_count += 1

                except Exception as e:
                    print(f"❌ خطأ في صف: {row} - {e}")
                    continue

        conn.commit()
        conn.close()
        print(f"✅ تم استيراد {imported_count} سجل من الخزنة")

    except Exception as e:
        print(f"❌ خطأ في استيراد بيانات الخزنة: {e}")

def import_persons_data(gc, spreadsheet_name="Bot Data"):
    """Import persons data from Google Sheets"""
    try:
        sh = gc.open(spreadsheet_name)

        # Import clients
        try:
            worksheet = sh.worksheet("العملاء")
            data = worksheet.get_all_values()
            if len(data) > 1:
                conn = get_db()
                c = conn.cursor()
                imported_count = 0

                for row in data[1:]:  # Skip header
                    if len(row) >= 1 and row[0].strip():
                        name = row[0].strip()
                        try:
                            c.execute("""
                                INSERT OR IGNORE INTO persons (name, type)
                                VALUES (?, 'عميل')
                            """, (name,))
                            if c.rowcount > 0:
                                imported_count += 1
                        except Exception as e:
                            print(f"❌ خطأ في عميل: {name} - {e}")

                conn.commit()
                conn.close()
                print(f"✅ تم استيراد {imported_count} عميل")
        except Exception as e:
            print(f"⚠️ خطأ في استيراد العملاء: {e}")

        # Import suppliers
        try:
            worksheet = sh.worksheet("الموردين")
            data = worksheet.get_all_values()
            if len(data) > 1:
                conn = get_db()
                c = conn.cursor()
                imported_count = 0

                for row in data[1:]:  # Skip header
                    if len(row) >= 1 and row[0].strip():
                        name = row[0].strip()
                        try:
                            c.execute("""
                                INSERT OR IGNORE INTO persons (name, type)
                                VALUES (?, 'مورد')
                            """, (name,))
                            if c.rowcount > 0:
                                imported_count += 1
                        except Exception as e:
                            print(f"❌ خطأ في مورد: {name} - {e}")

                conn.commit()
                conn.close()
                print(f"✅ تم استيراد {imported_count} مورد")
        except Exception as e:
            print(f"⚠️ خطأ في استيراد الموردين: {e}")

    except Exception as e:
        print(f"❌ خطأ في استيراد بيانات الأشخاص: {e}")

def import_employees_data(gc, spreadsheet_name="Bot Data"):
    """Import employees data from Google Sheets"""
    try:
        sh = gc.open(spreadsheet_name)
        worksheet = sh.worksheet("الموظفين")

        data = worksheet.get_all_values()
        if len(data) <= 1:
            print("⚠️ لا توجد بيانات في ورقة الموظفين")
            return

        conn = get_db()
        c = conn.cursor()
        imported_count = 0

        for row in data[1:]:  # Skip header
            if len(row) >= 2:  # name, salary
                try:
                    name = row[0].strip()
                    salary_str = row[1].strip().replace(',', '').replace(' ', '')

                    try:
                        salary = float(salary_str)
                    except ValueError:
                        print(f"⚠️ راتب غير صحيح: {salary_str}, سيتم تجاهله")
                        continue

                    c.execute("""
                        INSERT OR IGNORE INTO employees (name, salary)
                        VALUES (?, ?)
                    """, (name, salary))
                    if c.rowcount > 0:
                        imported_count += 1

                except Exception as e:
                    print(f"❌ خطأ في موظف: {row} - {e}")
                    continue

        conn.commit()
        conn.close()
        print(f"✅ تم استيراد {imported_count} موظف")

    except Exception as e:
        print(f"❌ خطأ في استيراد بيانات الموظفين: {e}")

def main():
    print("🚀 بدء استيراد البيانات من Google Sheets")
    print("=" * 50)

    # Initialize database
    from database import init_db
    init_db()

    # Connect to Google Sheets
    gc = connect_to_sheets()
    if not gc:
        print("❌ فشل الاتصال بـ Google Sheets")
        return

    # Import data
    spreadsheet_name = os.environ.get("SPREADSHEET_NAME", "Bot Data")

    print("\n📊 استيراد بيانات الخزنة...")
    import_khazna_data(gc, spreadsheet_name)

    print("\n👥 استيراد بيانات الأشخاص...")
    import_persons_data(gc, spreadsheet_name)

    print("\n👷 استيراد بيانات الموظفين...")
    import_employees_data(gc, spreadsheet_name)

    print("\n✅ انتهى الاستيراد!")
    print("🎉 يمكنك الآن تشغيل البوت بالبيانات المستوردة")

if __name__ == "__main__":
    main()