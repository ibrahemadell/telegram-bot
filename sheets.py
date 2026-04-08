import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def connect_sheets():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("حسابات البوت")
    return sheet

def add_transaction(sheet, type, amount, description):
    ws = sheet.worksheet("الخزنة")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, type, amount, description])
    update_summary(sheet)

def add_client(sheet, name, amount, type):
    ws = sheet.worksheet("الخزنة_العملاء")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount])
    update_clients_summary(sheet)

def add_supplier(sheet, name, amount, type):
    ws = sheet.worksheet("الخزنة_الموردين")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount])
    update_suppliers_summary(sheet)

def get_balance(sheet):
    ws = sheet.worksheet("الخزنة")
    records = ws.get_all_records()
    balance = 0
    for row in records:
        if row['النوع'] == 'دخل':
            balance += float(row['المبلغ'])
        elif row['النوع'] == 'صرف':
            balance -= float(row['المبلغ'])
    return balance

def get_person_balance(sheet, worksheet_name, name):
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    balance = 0
    for row in records:
        if row['الاسم'] == name:
            if row['النوع'] in ['دين', 'مديونية']:
                balance += float(row['المبلغ'])
            elif row['النوع'] == 'دفع':
                balance -= float(row['المبلغ'])
    return balance

def update_clients_summary(sheet):
    """تحديث تاب ملخص العملاء"""
    try:
        ws = sheet.worksheet("العملاء")
    except:
        ws = sheet.add_worksheet(title="العملاء", rows=200, cols=3)

    ws.clear()
    ws.append_row(["الاسم", "الحالة", "المبلغ"])

    try:
        records = sheet.worksheet("الخزنة_العملاء").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
        for name in names:
            b = get_person_balance(sheet, "الخزنة_العملاء", name)
            status = "عليه" if b > 0 else "ليه عندنا" if b < 0 else "صفر"
            ws.append_row([name, status, abs(b)])
    except:
        pass

def update_suppliers_summary(sheet):
    """تحديث تاب ملخص الموردين"""
    try:
        ws = sheet.worksheet("الموردين")
    except:
        ws = sheet.add_worksheet(title="الموردين", rows=200, cols=3)

    ws.clear()
    ws.append_row(["الاسم", "الحالة", "المبلغ"])

    try:
        records = sheet.worksheet("الخزنة_الموردين").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
        for name in names:
            b = get_person_balance(sheet, "الخزنة_الموردين", name)
            status = "عليه" if b > 0 else "ليه عندنا" if b < 0 else "صفر"
            ws.append_row([name, status, abs(b)])
    except:
        pass

def update_summary(sheet):
    """تحديث تاب الملخص الكلي"""
    try:
        ws = sheet.worksheet("ملخص")
    except:
        ws = sheet.add_worksheet(title="ملخص", rows=50, cols=3)

    ws.clear()
    ws.append_row(["البند", "الحالة", "المبلغ"])

    balance = get_balance(sheet)
    status = "موجب" if balance >= 0 else "سالب"
    ws.append_row(["رصيد الخزنة", status, balance])

def get_full_summary(sheet):
    """جلب الملخص الكامل لإرساله على تيليجرام"""
    balance = get_balance(sheet)
    emoji = "📈" if balance >= 0 else "📉"
    msg = f"📊 *ملخص الحسابات*\n\n"
    msg += f"{emoji} *رصيد الخزنة:* {balance} جنيه\n"

    # العملاء
    try:
        records = sheet.worksheet("الخزنة_العملاء").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
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

    # الموردين
    try:
        records = sheet.worksheet("الخزنة_الموردين").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
        if names:
            msg += "\n🏭 *الموردين:*\n"
            for name in names:
                b = get_person_balance(sheet, "الخزنة_الموردين", name)
                if b > 0:
                    msg += f"  • {name}: عليه {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: ليه عندنا {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass

    return msg
def add_person(sheet, name, person_type):
    """إضافة عميل أو مورد جديد"""
    worksheet_name = "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين"
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    names = [r['الاسم'] for r in records]
    if name in names:
        return False  # موجود بالفعل
    # مش محتاج نضيف صف، بس نحدث الملخص
    if person_type == "عميل":
        update_clients_summary(sheet)
    else:
        update_suppliers_summary(sheet)
    return True

def delete_person(sheet, name, person_type):
    """حذف كل سجلات عميل أو مورد"""
    worksheet_name = "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين"
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    names = [r['الاسم'] for r in records]
    
    if name not in names:
        return False  # مش موجود
    
    # حذف كل الصفوف اللي فيها الاسم ده
    rows_to_delete = []
    for i, row in enumerate(records):
        if row['الاسم'] == name:
            rows_to_delete.append(i + 2)  # +2 عشان الهيدر والـ index
    
    # نحذف من تحت لفوق عشان الأرقام محتشش
    for row_index in reversed(rows_to_delete):
        ws.delete_rows(row_index)
    
    if person_type == "عميل":
        update_clients_summary(sheet)
    else:
        update_suppliers_summary(sheet)
    
    return True