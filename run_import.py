#!/usr/bin/env python3
"""
Script to import data from Google Sheets to SQLite database
Usage: python run_import.py
"""

import os
import sys

def main():
    print("🔄 بدء عملية استيراد البيانات من Google Sheets")
    print("=" * 60)

    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("❌ ملف credentials.json غير موجود!")
        print("📋 يرجى التأكد من وجود ملف credentials.json في نفس المجلد")
        sys.exit(1)

    # Check environment variables
    token = os.environ.get('TOKEN')
    if not token:
        print("⚠️ تحذير: متغير TOKEN غير موجود")
        print("📝 سيتم استيراد البيانات فقط (لن يعمل البوت بدون TOKEN)")

    # Run the import
    try:
        import import_data
        import_data.main()
        print("\n✅ تم الانتهاء من الاستيراد بنجاح!")
    except ImportError as e:
        print(f"❌ خطأ في استيراد المكتبات: {e}")
        print("📦 تأكد من تثبيت المتطلبات: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ خطأ أثناء الاستيراد: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()