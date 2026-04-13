import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta

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

def get_monthly_khazna_report(sheet):
    try:
        ws = sheet.worksheet("الخزنة")
        records = ws.get_all_records()
        current_month = date.today().strftime("%Y-%m")
        total_in = 0
        total_out = 0
        for row in records:
            if row['التاريخ'][:7] != current_month:
                continue
            amount = float(row['المبلغ'])
            if row['النوع'] == 'دخل':
                total_in += amount
            elif row['النوع'] == 'صرف':
                total_out += amount
        return total_in, total_out
    except:
        return 0, 0

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

def get_clients_total(sheet):
    try:
        names = get_all_clients(sheet)
        total = 0
        details = []
        for name in names:
            b = get_person_balance(sheet, "الخزنة_العملاء", name)
            if b > 0:
                total += b
                details.append(f"  • {name}: {b} جنيه")
        return total, details
    except:
        return 0, []

def get_person_transactions(sheet, name, person_type):
    ws_name = "الخزنة_العملاء" if person_type == "عميل" else "الخزنة_الموردين"
    try:
        ws = sheet.worksheet(ws_name)
        records = ws.get_all_records()
        return [r for r in records if r['الاسم'] == name]
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

def get_suppliers_total(sheet):
    try:
        names = get_all_suppliers(sheet)
        total = 0
        details = []
        for name in names:
            b = get_person_balance(sheet, "الخزنة_الموردين", name)
            if b > 0:
                total += b
                details.append(f"  • {name}: {b} جنيه")
        return total, details
    except:
        return 0, []

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

# ============ إضافة وحذف عميل/مورد ============

def add_person(sheet, name, person_type):
    tab_name = "ليست_العملاء" if person_type == "عميل" else "ليست_الموردين"
    try:
        ws = sheet.worksheet(tab_name)
    except:
        ws = sheet.add_worksheet(title=tab_name, rows=200, cols=1)
        ws.append_row(["الاسم"])
    records = ws.get_all_records()
    if name in [r['الاسم'] for r in records]:
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

# ============ الموظفين ============

def get_all_employees(sheet):
    try:
        ws = sheet.worksheet("ليست_الموظفين")
        records = ws.get_all_records()
        return [(r['الاسم'], float(r['المرتب_الاسبوعي'])) for r in records if r['الاسم']]
    except:
        return []

def get_employee_names(sheet):
    return [e[0] for e in get_all_employees(sheet)]

def add_employee(sheet, name, weekly_salary):
    try:
        ws = sheet.worksheet("ليست_الموظفين")
    except:
        ws = sheet.add_worksheet(title="ليست_الموظفين", rows=200, cols=2)
        ws.append_row(["الاسم", "المرتب_الاسبوعي"])
    records = ws.get_all_records()
    if name in [r['الاسم'] for r in records]:
        return False
    ws.append_row([name, weekly_salary])
    return True

def delete_employee(sheet, name):
    try:
        ws = sheet.worksheet("ليست_الموظفين")
    except:
        return False
    records = ws.get_all_records()
    for i, row in enumerate(records):
        if row['الاسم'] == name:
            ws.delete_rows(i + 2)
            return True
    return False

def add_employee_transaction(sheet, name, type, amount, note=""):
    try:
        ws = sheet.worksheet("خزنة_الموظفين")
    except:
        ws = sheet.add_worksheet(title="خزنة_الموظفين", rows=500, cols=5)
        ws.append_row(["التاريخ", "الاسم", "النوع", "المبلغ", "النوت"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, name, type, amount, note])
    add_transaction(sheet, "صرف", amount, f"{type} موظف: {name}")

def get_employee_balance(sheet, name):
    try:
        today = date.today()
        days_since_saturday = (today.weekday() - 5) % 7
        week_start = today - timedelta(days=days_since_saturday)
        week_start_str = week_start.strftime("%Y-%m-%d")

        ws = sheet.worksheet("خزنة_الموظفين")
        records = ws.get_all_records()
        employees = get_all_employees(sheet)
        salary = next((e[1] for e in employees if e[0] == name), 0)

        total_paid = 0
        advances = 0
        bonuses = 0
        deductions = 0

        for row in records:
            if row['الاسم'] == name:
                row_date = row['التاريخ'][:10]
                if row_date < week_start_str:
                    continue
                amount = float(row['المبلغ'])
                if row['النوع'] == 'مرتب':
                    total_paid += amount
                elif row['النوع'] == 'سلفة':
                    advances += amount
                elif row['النوع'] == 'مكافأة':
                    bonuses += amount
                elif row['النوع'] == 'خصم':
                    deductions += amount

        net = salary + bonuses - advances - deductions - total_paid
        return {
            'salary': salary,
            'bonuses': bonuses,
            'advances': advances,
            'deductions': deductions,
            'total_paid': total_paid,
            'net': net,
            'week_start': week_start_str
        }
    except:
        return None

def get_weekly_employees_report(sheet):
    names = get_employee_names(sheet)
    report = []
    for name in names:
        data = get_employee_balance(sheet, name)
        if data:
            report.append({'name': name, 'data': data})
    return report

# ============ البنود الثابتة ============

def get_all_bands(sheet):
    try:
        ws = sheet.worksheet("ليست_البنود")
        records = ws.get_all_records()
        return [r['البند'] for r in records if r['البند']]
    except:
        return []

def add_band(sheet, name):
    try:
        ws = sheet.worksheet("ليست_البنود")
    except:
        ws = sheet.add_worksheet(title="ليست_البنود", rows=200, cols=1)
        ws.append_row(["البند"])
    records = ws.get_all_records()
    if name in [r['البند'] for r in records]:
        return False
    ws.append_row([name])
    return True

def delete_band(sheet, name):
    try:
        ws = sheet.worksheet("ليست_البنود")
    except:
        return False
    records = ws.get_all_records()
    for i, row in enumerate(records):
        if row['البند'] == name:
            ws.delete_rows(i + 2)
            return True
    return False

# ============ المصروفات ============

def add_masrof_edari(sheet, band, amount):
    try:
        ws = sheet.worksheet("خزنة_المصروفات")
    except:
        ws = sheet.add_worksheet(title="خزنة_المصروفات", rows=500, cols=5)
        ws.append_row(["التاريخ", "النوع", "البند", "المبلغ", "النوت"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, "إدارية", band, amount, ""])
    add_transaction(sheet, "صرف", amount, f"مصروفات إدارية: {band}")

def add_masrof_okhra(sheet, amount, note):
    try:
        ws = sheet.worksheet("خزنة_المصروفات")
    except:
        ws = sheet.add_worksheet(title="خزنة_المصروفات", rows=500, cols=5)
        ws.append_row(["التاريخ", "النوع", "البند", "المبلغ", "النوت"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([now, "أخرى", "", amount, note])
    add_transaction(sheet, "صرف", amount, f"مصروفات أخرى: {note}")

def get_monthly_band_report(sheet, band_name):
    try:
        ws = sheet.worksheet("خزنة_المصروفات")
        records = ws.get_all_records()
        current_month = date.today().strftime("%Y-%m")
        total = 0
        details = []
        for row in records:
            if row['البند'] == band_name and row['التاريخ'][:7] == current_month:
                amount = float(row['المبلغ'])
                total += amount
                details.append({'date': row['التاريخ'], 'amount': amount})
        return total, details
    except:
        return 0, []

def get_monthly_masrof_report(sheet):
    try:
        ws = sheet.worksheet("خزنة_المصروفات")
        records = ws.get_all_records()
        current_month = date.today().strftime("%Y-%m")
        bands = {}
        okhra_total = 0
        for row in records:
            if row['التاريخ'][:7] != current_month:
                continue
            amount = float(row['المبلغ'])
            if row['النوع'] == 'إدارية':
                band = row['البند']
                bands[band] = bands.get(band, 0) + amount
            elif row['النوع'] == 'أخرى':
                okhra_total += amount
        return bands, okhra_total
    except:
        return {}, 0

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

# ============ PDF ============

def generate_pdf_report(name, person_type, transactions, balance):
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    import tempfile

    def ar(text):
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14)
    normal_style = ParagraphStyle('normal', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    elements.append(Paragraph(ar(f"تقرير حركات {person_type}: {name}"), title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(ar(f"تاريخ التقرير: {date.today().strftime('%Y-%m-%d')}"), normal_style))
    elements.append(Spacer(1, 12))

    data = [[ar("التاريخ"), ar("النوع"), ar("المبلغ")]]
    for t in transactions:
        data.append([ar(t['التاريخ']), ar(t['النوع']), ar(str(t['المبلغ']))])

    status = ar("عليه") if balance > 0 else ar("ليه عندنا") if balance < 0 else ar("صفر")
    data.append([ar("الرصيد النهائي"), status, ar(str(abs(balance)))])

    table = Table(data, colWidths=[180, 120, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F2F3F4')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#AED6F1')),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
    ]))
    elements.append(table)
    doc.build(elements)
    return tmp.name