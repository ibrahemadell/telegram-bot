import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def connect_sheets():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("حسابات البوت")
    return sheet

# ============ الخزنة ============

def add_transaction(sheet, type, amount, description):
    ws = sheet.worksheet("الخزنة")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, type, amount, description])

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

# ============ العملاء ============

def add_client(sheet, name, amount, type):
    ws = sheet.worksheet("الخزنة_العملاء")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount])
    if type == "دفع":
        add_transaction(sheet, "دخل", amount, f"دفعة من عميل: {name}")

def get_all_clients(sheet):
    try:
        ws = sheet.worksheet("ليست_العملاء")
        records = ws.get_all_records()
        return sorted([r['الاسم'] for r in records if r['الاسم']])
    except:
        return []

# ============ الموردين ============

def add_supplier(sheet, name, amount, type):
    ws = sheet.worksheet("الخزنة_الموردين")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount])
    if type == "دفع":
        add_transaction(sheet, "صرف", amount, f"دفعة لمورد: {name}")

def get_all_suppliers(sheet):
    try:
        ws = sheet.worksheet("ليست_الموردين")
        records = ws.get_all_records()
        return sorted([r['الاسم'] for r in records if r['الاسم']])
    except:
        return []

# ============ الأرصدة ============

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

# ============ إضافة وحذف ============

def add_person(sheet, name, person_type):
    tab_name = "ليست_العملاء" if person_type == "عميل" else "ليست_الموردين"
    try:
        ws = sheet.worksheet(tab_name)
    except:
        ws = sheet.add_worksheet(title=tab_name, rows=200, cols=1)
        ws.append_row(["الاسم"])

    records = ws.get_all_records()
    existing = [r['الاسم'] for r in records if r['الاسم']]
    if name in existing:
        return False

    ws.append_row([name])
    return True

def delete_person(sheet, name, person_type):
    tab_name = "ليست_العملاء" if person_type == "عميل" else "ليست_الموردين"
    try:
        ws = sheet.worksheet(tab_name)
    except:
        return False

    records = ws.get_all_records()
    for i, row in enumerate(records):
        if row['الاسم'] == name:
            ws.delete_rows(i + 2)
            return True
    return False

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

def get_last_records(sheet, worksheet_name, limit=5):
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    return records[-limit:] if len(records) >= limit else records

def delete_last_record(sheet, worksheet_name, row_index):
    ws = sheet.worksheet(worksheet_name)
    ws.delete_rows(row_index + 2)