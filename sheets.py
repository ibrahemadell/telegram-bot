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
    if type == "دفع":
        add_transaction(sheet, "دخل", amount, f"دفعة من عميل: {name}")

def add_supplier(sheet, name, amount, type):
    ws = sheet.worksheet("الخزنة_الموردين")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount])
    update_suppliers_summary(sheet)
    if type == "دفع":
        add_transaction(sheet, "صرف", amount, f"دفعة لمورد: {name}")

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
            status = "ليه عندنا" if b > 0 else "دفعنا له زيادة" if b < 0 else "صفر"
            ws.append_row([name, status, abs(b)])
    except:
        pass

def update_summary(sheet):
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
                    msg += f"  • {name}: ليه عندنا {b} جنيه\n"
                elif b < 0:
                    msg += f"  • {name}: دفعنا له زيادة {abs(b)} جنيه\n"
                else:
                    msg += f"  • {name}: صفر\n"
    except:
        pass

    return msg

def add_person(sheet, name, person_type):
    worksheet_name = "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين"
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    names = [r['الاسم'] for r in records]
    if name in names:
        return False
    if person_type == "عميل":
        update_clients_summary(sheet)
    else:
        update_suppliers_summary(sheet)
    return True

def delete_person(sheet, name, person_type):
    worksheet_name = "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين"
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    names = [r['الاسم'] for r in records]
    if name not in names:
        return False
    rows_to_delete = []
    for i, row in enumerate(records):
        if row['الاسم'] == name:
            rows_to_delete.append(i + 2)
    for row_index in reversed(rows_to_delete):
        ws.delete_rows(row_index)
    if person_type == "عميل":
        update_clients_summary(sheet)
    else:
        update_suppliers_summary(sheet)
    return True

def get_last_records(sheet, worksheet_name, limit=5):
    ws = sheet.worksheet(worksheet_name)
    records = ws.get_all_records()
    return records[-limit:] if len(records) >= limit else records

def delete_last_record(sheet, worksheet_name, row_index):
    ws = sheet.worksheet(worksheet_name)
    ws.delete_rows(row_index + 2)

def get_all_clients(sheet):
    try:
        records = sheet.worksheet("الخزنة_العملاء").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
        return sorted(names)
    except:
        return []

def get_all_suppliers(sheet):
    try:
        records = sheet.worksheet("الخزنة_الموردين").get_all_records()
        names = list(set([r['الاسم'] for r in records if r['الاسم']]))
        return sorted(names)
    except:
        return []