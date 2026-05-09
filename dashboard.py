from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for, Response
from database import (
    get_balance, get_clients_total, get_suppliers_total,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_weekly_employees_report, get_daily_khazna_report,
    get_db, authenticate_dashboard_user, get_user_companies, user_has_company,
    add_client, add_supplier, add_employee, add_employee_transaction,
    add_masrof_edari, add_masrof_okhra, add_transaction, get_all_bands,
    add_person, add_band
)
from datetime import date, timedelta
from functools import wraps
import os
import io
import html
import re
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_default_key_123")

# ============ DB Helpers ============

def get_khazna_range(date_from, date_to, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT date, type, amount, description
        FROM khazna
        WHERE date >= %s AND date <= %s AND company_id = %s
        ORDER BY created_at DESC
    """, (date_from, date_to, company_id))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    total_in = sum(r['amount'] for r in rows if r['type'] == 'دخل')
    total_out = sum(r['amount'] for r in rows if r['type'] == 'صرف')
    return rows, total_in, total_out

def get_person_transactions_range(name, person_type, date_from, date_to, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT date, trans_type as type, amount
        FROM person_transactions
        WHERE person_name=%s AND person_type=%s
        AND date >= %s AND date <= %s AND company_id = %s
        ORDER BY created_at DESC
    """, (name, person_type, date_from, date_to, company_id))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_masrof_range(date_from, date_to, company_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT band, SUM(amount) as total
        FROM masrof_edari WHERE date >= %s AND date <= %s AND company_id = %s
        GROUP BY band
    """, (date_from, date_to, company_id))
    bands = {r['band']: r['total'] for r in c.fetchall()}
    c.execute("SELECT SUM(amount) as total FROM masrof_okhra WHERE date >= %s AND date <= %s AND company_id = %s", (date_from, date_to, company_id))
    row = c.fetchone()
    okhra = float(row['total']) if row and row['total'] else 0
    conn.close()
    return bands, okhra

# ============ Auth Decorator ============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

LOGIN_HTML = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>تسجيل الدخول - لوحة التحكم</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    font-family: 'Cairo', sans-serif; 
    background: #0a0e1a; 
    color: #f1f5f9;
    display: flex; 
    justify-content: center; 
    align-items: center; 
    min-height: 100vh;
    background-image: radial-gradient(circle at top right, rgba(59,130,246,0.1), transparent 40%),
                      radial-gradient(circle at bottom left, rgba(139,92,246,0.1), transparent 40%);
  }
  .login-card {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 40px;
    border-radius: 20px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  }
  .login-card h2 {
    text-align: center;
    margin-bottom: 30px;
    font-weight: 900;
    font-size: 24px;
    color: #fff;
  }
  .input-group { margin-bottom: 20px; }
  .input-group label { display: block; margin-bottom: 8px; font-size: 14px; color: #94a3b8; font-weight: bold; }
  .input-group input {
    width: 100%;
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid #1e2d45;
    background: #0f172a;
    color: #fff;
    font-family: 'Cairo', sans-serif;
    outline: none;
    transition: all 0.3s;
  }
  .input-group input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
  .login-btn {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 700;
    font-family: 'Cairo', sans-serif;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    margin-top: 10px;
  }
  .login-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px -10px rgba(59,130,246,0.5);
  }
  .error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    font-size: 14px;
    margin-bottom: 20px;
    border: 1px solid rgba(239, 68, 68, 0.2);
  }
</style>
</head>
<body>
  <div class="login-card">
    <h2>تسجيل الدخول</h2>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
      <div class="input-group">
        <label>كلمة المرور</label>
        <input type="password" name="password" required>
      </div>
      <button type="submit" class="login-btn">دخول</button>
    </form>
  </div>
</body>
</html>'''

SELECT_COMPANY_HTML = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>اختيار الشركة</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Cairo', sans-serif;
    background: #0a0e1a;
    color: #f1f5f9;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
  }
  .card {
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 28px;
    border-radius: 16px;
    width: 100%;
    max-width: 460px;
  }
  h2 { font-size: 22px; margin-bottom: 16px; text-align: center; }
  .sub { font-size: 13px; color: #94a3b8; margin-bottom: 16px; text-align: center; }
  .btn {
    width: 100%;
    padding: 12px;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    background: #0f172a;
    color: #fff;
    cursor: pointer;
    font-family: 'Cairo', sans-serif;
    font-weight: 700;
    margin-bottom: 10px;
  }
  .btn:hover { border-color: #3b82f6; }
</style>
</head>
<body>
  <div class="card">
    <h2>اختيار الشركة</h2>
    <div class="sub">اختار الشركة اللي عايز تفتح الداشبورد عليها</div>
    <form method="POST">
      {% for company in companies %}
      <button class="btn" type="submit" name="company_id" value="{{ company.id }}">{{ company.name }}</button>
      {% endfor %}
    </form>
  </div>
</body>
</html>'''

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>لوحة التحكم المالية - {{ company_name }}</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0e1a; --surface:#111827; --surface2:#1a2235; --border:#1e2d45;
  --accent:#3b82f6; --accent2:#06b6d4; --green:#10b981; --red:#ef4444;
  --yellow:#f59e0b; --purple:#8b5cf6; --orange:#f97316;
  --text:#f1f5f9; --text2:#94a3b8; --text3:#475569;
  --sidebar-w: 220px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Cairo',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}

/* ===== Sidebar ===== */
.sidebar{
  position:fixed;right:0;top:0;width:var(--sidebar-w);height:100vh;
  background:var(--surface);border-left:1px solid var(--border);
  padding:20px 0;z-index:200;display:flex;flex-direction:column;
  transition:transform 0.3s;
  transform:translateX(100%);
}
.sidebar.open{transform:translateX(0);}
.logo{padding:0 20px 20px;border-bottom:1px solid var(--border);margin-bottom:12px;}
.logo h1{font-size:16px;font-weight:900;}
.logo span{font-size:11px;color:var(--text3);}
.nav-group{padding:8px 20px 4px;color:var(--text3);font-size:11px;font-weight:700;}
.nav-group-btn{
  width:100%;background:none;border:none;color:var(--text3);text-align:right;
  font-family:'Cairo',sans-serif;font-size:11px;font-weight:700;cursor:pointer;
  padding:8px 20px 4px;display:flex;justify-content:space-between;align-items:center;
}
.nav-group-btn .arrow{transition:transform 0.2s;}
.nav-dropdown.open .nav-group-btn .arrow{transform:rotate(180deg);}
.nav-children{display:none;}
.nav-dropdown.open .nav-children{display:block;}
.nav-item{
  display:flex;align-items:center;gap:10px;padding:10px 20px;
  cursor:pointer;color:var(--text2);font-size:13px;font-weight:600;
  transition:all 0.2s;border-right:3px solid transparent;
}
.nav-item:hover{background:var(--surface2);color:var(--text);}
.nav-item.active{color:var(--accent);border-right-color:var(--accent);background:rgba(59,130,246,0.08);}
.nav-icon{font-size:16px;width:20px;text-align:center;}
.sidebar-footer{margin-top:auto;padding:16px 20px;border-top:1px solid var(--border);}
.cache-info{font-size:11px;color:var(--text3);}

/* Mobile toggle */
.mobile-toggle{
  display:flex;align-items:center;justify-content:center;
  position:fixed;top:12px;right:12px;z-index:300;
  background:var(--accent);border:none;color:white;
  width:40px;height:40px;border-radius:8px;font-size:18px;cursor:pointer;
}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:150;}

/* ===== Main ===== */
.main{margin-right:0;padding:24px 28px;min-height:100vh;}
.page{display:none;animation:fadeIn 0.3s ease;}
.page.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

/* ===== Toolbar ===== */
.toolbar{
  display:flex;flex-wrap:wrap;gap:10px;align-items:center;
  margin-bottom:20px;
  background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:14px 18px;
}
.toolbar-title{font-size:16px;font-weight:900;margin-left:auto;}
.toolbar-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.date-input{
  background:var(--surface2);border:1px solid var(--border);color:var(--text);
  padding:7px 12px;border-radius:8px;font-family:'Cairo',sans-serif;font-size:12px;
  cursor:pointer;
}
.date-input:focus{outline:none;border-color:var(--accent);}
.btn{
  background:var(--surface2);border:1px solid var(--border);color:var(--text2);
  padding:7px 14px;border-radius:8px;cursor:pointer;
  font-family:'Cairo',sans-serif;font-size:12px;font-weight:600;
  transition:all 0.2s;white-space:nowrap;
}
  .btn:hover{border-color:var(--accent);color:var(--accent);}
  .btn.primary{background:var(--accent);border-color:var(--accent);color:white;}
  .btn.primary:hover{background:#2563eb;}
  .btn.danger{background:var(--red);border-color:var(--red);color:white;text-decoration:none;text-align:center;display:inline-block;}
  .btn.danger:hover{background:#dc2626;}
  .btn.small{padding:7px 10px;font-size:12px;border-radius:8px;}
  .export-actions{display:flex;gap:6px;flex-wrap:wrap;align-items:center;}
  .row-actions{display:flex;gap:6px;flex-wrap:wrap;}
  .btn-group{display:flex;gap:6px;flex-wrap:wrap;}
.quick-btn{
  padding:5px 10px;border-radius:20px;font-size:11px;font-weight:700;
  background:var(--surface2);border:1px solid var(--border);color:var(--text3);
  cursor:pointer;transition:all 0.2s;
}
.quick-btn:hover,.quick-btn.active{background:var(--accent);border-color:var(--accent);color:white;}

/* Filter bar */
.filter-bar{
  display:flex;gap:10px;flex-wrap:wrap;align-items:center;
  margin-bottom:16px;
}
.filter-select{
  background:var(--surface2);border:1px solid var(--border);color:var(--text);
  padding:7px 12px;border-radius:8px;font-family:'Cairo',sans-serif;font-size:12px;
  min-width:150px;
}
.filter-select:focus{outline:none;border-color:var(--accent);}
.filter-label{font-size:12px;color:var(--text3);font-weight:600;}

/* ===== Cards ===== */
.cards-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;}
.card{
  background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:18px;position:relative;overflow:hidden;transition:border-color 0.2s,transform 0.2s;
}
.card:hover{border-color:var(--accent);transform:translateY(-1px);}
.card::before{content:'';position:absolute;top:0;right:0;width:3px;height:100%;}
.card.blue::before{background:var(--accent);}
.card.green::before{background:var(--green);}
.card.red::before{background:var(--red);}
.card.yellow::before{background:var(--yellow);}
.card.purple::before{background:var(--purple);}
.card.cyan::before{background:var(--accent2);}
.card.orange::before{background:var(--orange);}
.card-label{font-size:11px;color:var(--text3);font-weight:700;margin-bottom:6px;letter-spacing:0.03em;}
.card-value{font-size:22px;font-weight:900;margin-bottom:3px;}
.card-value.green{color:var(--green);}
.card-value.red{color:var(--red);}
.card-value.blue{color:var(--accent);}
.card-value.yellow{color:var(--yellow);}
.card-value.purple{color:var(--purple);}
.card-value.orange{color:var(--orange);}
.card-sub{font-size:11px;color:var(--text3);}
.card-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:28px;opacity:0.08;}

/* ===== Sections ===== */
.sections-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.section{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:16px;}
.section-header{
  padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
}
.section-title{font-size:13px;font-weight:700;}
.badge{font-size:11px;padding:3px 8px;border-radius:20px;font-weight:700;}
.badge-blue{background:rgba(59,130,246,0.15);color:var(--accent);}
.badge-green{background:rgba(16,185,129,0.15);color:var(--green);}
.badge-red{background:rgba(239,68,68,0.15);color:var(--red);}
.badge-yellow{background:rgba(245,158,11,0.15);color:var(--yellow);}

/* ===== Table ===== */
.table-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;min-width:400px;}
th{
  padding:9px 18px;text-align:right;font-size:11px;font-weight:700;
  color:var(--text3);text-transform:uppercase;letter-spacing:0.05em;
  background:var(--surface2);border-bottom:1px solid var(--border);white-space:nowrap;
}
td{padding:11px 18px;font-size:13px;border-bottom:1px solid rgba(30,45,69,0.5);}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(59,130,246,0.04);}
.amt-pos{color:var(--green);font-weight:700;}
.amt-neg{color:var(--red);font-weight:700;}
.amt-neu{color:var(--text2);}
.tag{display:inline-block;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:700;}
.tag-debt{background:rgba(239,68,68,0.15);color:var(--red);}
.tag-credit{background:rgba(16,185,129,0.15);color:var(--green);}
.tag-zero{background:rgba(148,163,184,0.1);color:var(--text3);}
.tag-in{background:rgba(16,185,129,0.15);color:var(--green);}
.tag-out{background:rgba(239,68,68,0.15);color:var(--red);}

/* ===== Bar chart ===== */
.bar-chart{padding:14px 18px;}
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
.bar-label{font-size:12px;color:var(--text2);width:110px;flex-shrink:0;text-align:right;}
.bar-track{flex:1;height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;}
.bar-fill{height:100%;border-radius:4px;transition:width 0.8s cubic-bezier(0.4,0,0.2,1);}
.bar-fill.green{background:linear-gradient(90deg,var(--green),#34d399);}
.bar-fill.red{background:linear-gradient(90deg,var(--red),#f87171);}
.bar-fill.blue{background:linear-gradient(90deg,var(--accent),var(--accent2));}
.bar-fill.yellow{background:linear-gradient(90deg,var(--yellow),#fcd34d);}
.bar-fill.purple{background:linear-gradient(90deg,var(--purple),#a78bfa);}
.bar-fill.orange{background:linear-gradient(90deg,var(--orange),#fb923c);}
.bar-amount{font-size:12px;color:var(--text2);width:90px;flex-shrink:0;}

/* ===== Day selector ===== */
.day-selector{display:flex;gap:8px;flex-wrap:wrap;padding:14px 18px;border-bottom:1px solid var(--border);}
.day-btn{
  padding:6px 12px;border-radius:20px;background:var(--surface2);
  border:1px solid var(--border);color:var(--text2);
  font-family:'Cairo',sans-serif;font-size:12px;cursor:pointer;transition:all 0.2s;
  text-align:center;line-height:1.4;
}
.day-btn:hover,.day-btn.active{background:var(--accent);border-color:var(--accent);color:white;}
.day-btn small{display:block;font-size:10px;opacity:0.8;}

/* ===== Summary mini ===== */
.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:14px 18px;border-bottom:1px solid var(--border);}
.summary-item{text-align:center;}
.summary-label{font-size:11px;color:var(--text3);margin-bottom:4px;}
.summary-val{font-size:18px;font-weight:900;}

/* ===== Loading / Empty ===== */
.loading{text-align:center;padding:36px;color:var(--text3);font-size:13px;}
.spinner{
  display:inline-block;width:16px;height:16px;
  border:2px solid var(--border);border-top-color:var(--accent);
  border-radius:50%;animation:spin 0.8s linear infinite;
  margin-left:8px;vertical-align:middle;
}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{text-align:center;padding:32px;color:var(--text3);font-size:13px;}
.skeleton{background:linear-gradient(90deg,var(--surface2) 25%,var(--border) 50%,var(--surface2) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:6px;height:16px;margin:6px 0;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* ===== Modals ===== */
.modal-overlay {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8);
  z-index:999; justify-content:center; align-items:center;
  backdrop-filter: blur(4px);
}
.modal-overlay.active { display:flex; animation: fadeIn 0.2s; }
.modal-content {
  background:var(--surface); border:1px solid var(--border); border-radius:16px;
  width:100%; max-width:400px; padding:24px; position:relative;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  transform: translateY(20px);
  animation: slideUp 0.3s forwards;
}
@keyframes slideUp { to { transform: translateY(0); } }
@media(max-width:768px) {
  .modal-overlay { align-items:flex-end; }
  .modal-content { 
    border-radius: 20px 20px 0 0; 
    max-width:100%; 
    padding:24px 20px 40px;
    transform: translateY(100%);
  }
}
.modal-close {
  position:absolute; top:16px; left:16px; background:none; border:none;
  color:var(--text3); font-size:24px; cursor:pointer;
}
.modal-title { font-size:18px; font-weight:900; margin-bottom:20px; color:var(--text); }
.form-group { margin-bottom:16px; }
.form-group label { display:block; font-size:13px; color:var(--text2); margin-bottom:6px; font-weight:700; }
.form-input, .form-select {
  width:100%; padding:12px 14px; background:var(--surface2); border:1px solid var(--border);
  border-radius:10px; color:var(--text); font-family:'Cairo',sans-serif;
  font-size:14px; outline:none; transition:0.2s;
}
.form-input:focus, .form-select:focus { border-color:var(--accent); box-shadow:0 0 0 2px rgba(59,130,246,0.2); }
.modal-btn {
  width:100%; padding:14px; background:var(--accent); color:white; border:none;
  border-radius:10px; font-family:'Cairo',sans-serif; font-size:15px; font-weight:700;
  cursor:pointer; margin-top:8px; transition:0.2s;
}
.modal-btn:hover { background:#2563eb; transform:translateY(-2px); }
.modal-btn:active { transform:translateY(0); }

/* ===== Scrollbar ===== */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--surface);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}

/* ===== Responsive ===== */
@media(max-width:1200px){.cards-grid{grid-template-columns:repeat(3,1fr);}}
@media(max-width:900px){
  .cards-grid{grid-template-columns:repeat(2,1fr);}
  .sections-row{grid-template-columns:1fr;}
}
@media(max-width:768px){
  .sidebar{width:260px;}
  .overlay.show{display:block;}
  .main{margin-right:0;padding:16px;padding-top:60px;}
  .cards-grid{grid-template-columns:repeat(2,1fr);gap:10px;}
  .card{padding:14px;}
  .card-value{font-size:18px;}
  .toolbar{padding:10px 14px;}
  th,td{padding:8px 12px;}
}
@media(max-width:480px){
  .cards-grid{grid-template-columns:1fr 1fr;}
  .card-icon{display:none;}
}
</style>
</head>
<body>

<button class="mobile-toggle" onclick="toggleSidebar()">☰</button>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>

<aside class="sidebar" id="sidebar">
  <div class="logo">
    <h1>💼 {{ company_name }}</h1>
    <span id="last-update">لوحة التحكم</span>
  </div>
  <nav>
    <div class="nav-dropdown open" id="nav-reports">
      <button class="nav-group-btn" onclick="toggleNavGroup('nav-reports')">التقارير <span class="arrow">⌄</span></button>
      <div class="nav-children">
        <div class="nav-item active" onclick="showPage('overview',this)"><span class="nav-icon">📊</span>نظرة عامة</div>
        <div class="nav-item" onclick="showPage('clients',this)"><span class="nav-icon">👥</span>تقرير العملاء</div>
        <div class="nav-item" onclick="showPage('suppliers',this)"><span class="nav-icon">🏭</span>تقرير الموردين</div>
        <div class="nav-item" onclick="showPage('expenses',this)"><span class="nav-icon">📋</span>تقرير المصروفات</div>
        <div class="nav-item" onclick="showPage('daily',this)"><span class="nav-icon">📅</span>تقرير يومي</div>
      </div>
    </div>
    <div class="nav-dropdown open" id="nav-ops">
      <button class="nav-group-btn" onclick="toggleNavGroup('nav-ops')">الإدخال والتشغيل <span class="arrow">⌄</span></button>
      <div class="nav-children">
        <div class="nav-item" onclick="showPage('transactions',this)"><span class="nav-icon">🔄</span>الموردين والعملاء</div>
        <div class="nav-item" onclick="showPage('cash-expenses',this)"><span class="nav-icon">🏦</span>الخزنة والمصروفات</div>
        <div class="nav-item" onclick="showPage('employees',this)"><span class="nav-icon">👷</span>الموظفين</div>
      </div>
    </div>
  </nav>
  <div class="sidebar-footer">
    <a href="/select-company" class="btn" style="width:100%; margin-bottom:8px; text-align:center; display:inline-block; text-decoration:none;">تغيير الشركة</a>
    <a href="/logout" class="btn danger" style="width:100%; margin-top:8px;">تسجيل خروج</a>
  </div>
</aside>

<main class="main">

<!-- ===== نظرة عامة ===== -->
<div class="page active" id="page-overview">
  <div class="toolbar">
    <div>
      <div class="toolbar-title" style="margin-left:10px;">📊 نظرة عامة</div>
      <div class="toolbar-sub" id="overview-period"></div>
    </div>
    <div class="btn-group">
      <span class="quick-btn active" onclick="setQuick('overview',7,this)">7 أيام</span>
      <span class="quick-btn" onclick="setQuick('overview',30,this)">30 يوم</span>
      <span class="quick-btn" onclick="setQuick('overview',90,this)">3 أشهر</span>
    </div>
    <input type="date" class="date-input" id="ov-from">
    <input type="date" class="date-input" id="ov-to">
    <button class="btn primary" onclick="loadOverview()">بحث</button>
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('overview','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('overview','excel')">Excel</button>
    </div>
  </div>
  <div class="cards-grid" id="overview-cards"><div class="loading"><span class="spinner"></span> جاري التحميل</div></div>
  <div class="sections-row">
    <div class="section">
      <div class="section-header"><span class="section-title">📈 دخل وصرف</span><span class="badge badge-blue" id="ov-month"></span></div>
      <div class="bar-chart" id="ov-chart"><div class="loading"><span class="spinner"></span></div></div>
    </div>
    <div class="section">
      <div class="section-header"><span class="section-title">⚡ آخر الحركات</span><span class="badge badge-green" id="ov-txcount"></span></div>
      <div class="table-wrap" id="ov-recent"><div class="loading"><span class="spinner"></span></div></div>
    </div>
  </div>
</div>

<!-- ===== العملاء ===== -->
<div class="page" id="page-clients">
  <div class="toolbar">
    <div><div class="toolbar-title">👥 العملاء</div></div>
    <div class="btn-group">
      <span class="quick-btn active" onclick="setQuick('clients',30,this)">30 يوم</span>
      <span class="quick-btn" onclick="setQuick('clients',90,this)">3 أشهر</span>
      <span class="quick-btn" onclick="setQuick('clients',365,this)">سنة</span>
      <span class="quick-btn" onclick="setQuick('clients',3650,this)">الكل</span>
    </div>
    <input type="date" class="date-input" id="cl-from">
    <input type="date" class="date-input" id="cl-to">
    <button class="btn primary" onclick="loadClients()">بحث</button>
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('clients','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('clients','excel')">Excel</button>
    </div>
  </div>
  <div class="filter-bar">
    <span class="filter-label">فلتر:</span>
    <select class="filter-select" id="client-filter" onchange="filterClientsTable()">
      <option value="all">كل العملاء</option>
      <option value="debt">عليهم فلوس</option>
      <option value="credit">ليهم فلوس</option>
      <option value="zero">صفر</option>
    </select>
    <input type="text" class="date-input" id="client-search" placeholder="🔍 بحث باسم..." oninput="filterClientsTable()" style="min-width:160px;">
  </div>
  <div class="section">
    <div class="section-header">
      <span class="section-title">قائمة العملاء</span>
      <span class="badge badge-blue" id="clients-badge"></span>
    </div>
    <div class="table-wrap" id="clients-table"><div class="loading"><span class="spinner"></span></div></div>
  </div>
</div>

<!-- ===== الموردين ===== -->
<div class="page" id="page-suppliers">
  <div class="toolbar">
    <div><div class="toolbar-title">🏭 الموردين</div></div>
    <div class="btn-group">
      <span class="quick-btn active" onclick="setQuick('suppliers',30,this)">30 يوم</span>
      <span class="quick-btn" onclick="setQuick('suppliers',90,this)">3 أشهر</span>
      <span class="quick-btn" onclick="setQuick('suppliers',365,this)">سنة</span>
      <span class="quick-btn" onclick="setQuick('suppliers',3650,this)">الكل</span>
    </div>
    <input type="date" class="date-input" id="sp-from">
    <input type="date" class="date-input" id="sp-to">
    <button class="btn primary" onclick="loadSuppliers()">بحث</button>
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('suppliers','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('suppliers','excel')">Excel</button>
    </div>
  </div>
  <div class="filter-bar">
    <span class="filter-label">فلتر:</span>
    <select class="filter-select" id="supplier-filter" onchange="filterSuppliersTable()">
      <option value="all">كل الموردين</option>
      <option value="debt">ليهم علينا</option>
      <option value="zero">صفر</option>
    </select>
    <input type="text" class="date-input" id="supplier-search" placeholder="🔍 بحث باسم..." oninput="filterSuppliersTable()" style="min-width:160px;">
  </div>
  <div class="section">
    <div class="section-header">
      <span class="section-title">قائمة الموردين</span>
      <span class="badge badge-red" id="suppliers-badge"></span>
    </div>
    <div class="table-wrap" id="suppliers-table"><div class="loading"><span class="spinner"></span></div></div>
  </div>
</div>

<!-- ===== الموظفين ===== -->
<div class="page" id="page-employees">
  <div class="toolbar">
    <div><div class="toolbar-title">👷 الموظفين</div><button class="btn primary" style="margin-right:auto" onclick="openModal('modal-emp')">➕ موظف</button><button class="btn" style="background:var(--green);color:white;border:none;margin-right:8px;" onclick="openModal('modal-emp-tx')">💵 معاملة</button></div>
    <input type="text" class="date-input" id="emp-search" placeholder="🔍 بحث باسم..." oninput="filterEmpTable()" style="min-width:160px;">
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('employees','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('employees','excel')">Excel</button>
    </div>
  </div>
  <div class="section">
    <div class="section-header"><span class="section-title">تقرير المرتبات الأسبوعي</span><span class="badge badge-yellow" id="emp-badge"></span></div>
    <div class="table-wrap" id="emp-table"><div class="loading"><span class="spinner"></span></div></div>
  </div>
</div>

<!-- ===== المصروفات ===== -->
<div class="page" id="page-expenses">
  <div class="toolbar">
    <div><div class="toolbar-title">📋 المصروفات</div></div>
    <div class="btn-group">
      <span class="quick-btn active" onclick="setQuick('expenses',30,this)">30 يوم</span>
      <span class="quick-btn" onclick="setQuick('expenses',90,this)">3 أشهر</span>
      <span class="quick-btn" onclick="setQuick('expenses',365,this)">سنة</span>
    </div>
    <input type="date" class="date-input" id="ex-from">
    <input type="date" class="date-input" id="ex-to">
    <button class="btn primary" onclick="loadExpenses()">بحث</button>
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('expenses','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('expenses','excel')">Excel</button>
    </div>
  </div>
  <div class="sections-row">
    <div class="section">
      <div class="section-header"><span class="section-title">📌 البنود الإدارية</span></div>
      <div class="bar-chart" id="ex-bands"><div class="loading"><span class="spinner"></span></div></div>
    </div>
    <div class="section">
      <div class="section-header"><span class="section-title">📊 ملخص</span></div>
      <div id="ex-summary"><div class="loading"><span class="spinner"></span></div></div>
    </div>
  </div>
</div>

<!-- ===== التقرير اليومي ===== -->
<div class="page" id="page-daily">
  <div class="toolbar">
    <div><div class="toolbar-title">📅 التقرير اليومي</div></div>
    <input type="date" class="date-input" id="daily-custom" onchange="loadDailyCustom()">
    <div class="export-actions">
      <button class="btn small" onclick="openReportExport('daily','pdf')">PDF</button>
      <button class="btn small" onclick="openReportExport('daily','excel')">Excel</button>
    </div>
  </div>
  <div class="section">
    <div class="day-selector" id="day-selector"></div>
    <div id="daily-content"><div class="empty">اختار يوم</div></div>
  </div>
</div>

<!-- ===== الترانزكشن ===== -->
<div class="page" id="page-transactions">
  <div class="toolbar">
    <div><div class="toolbar-title">🔄 الموردين والعملاء</div><div class="toolbar-sub">إضافة أسماء جديدة وتسجيل الحركات من مكان واحد</div></div>
  </div>
  <div class="sections-row">
    <div class="section">
      <div class="section-header"><span class="section-title">إضافة عميل / مورد</span></div>
      <div style="padding:16px;">
        <div class="form-group">
          <label>نوع الإضافة</label>
          <select class="form-select" id="tx-add-type">
            <option value="client">عميل</option>
            <option value="supplier">مورد</option>
          </select>
        </div>
        <div class="form-group"><label>الاسم</label><input type="text" id="tx-add-name" class="form-input" placeholder="اكتب الاسم"></div>
        <button class="modal-btn" onclick="submitAddPersonForm()">إضافة</button>
      </div>
    </div>
    <div class="section">
      <div class="section-header"><span class="section-title">تسجيل حركة</span></div>
      <div style="padding:16px;">
        <div class="form-group">
          <label>نوع الشخص</label>
          <select class="form-select" id="tx-person-type" onchange="onTxPersonTypeChange()">
            <option value="">اختر</option>
            <option value="client">عميل</option>
            <option value="supplier">مورد</option>
          </select>
        </div>
        <div class="form-group">
          <label>الاسم</label>
          <select class="form-select" id="tx-person-name">
            <option value="">اختر النوع أولا</option>
          </select>
        </div>
        <div class="form-group">
          <label>نوع الترانزكشن</label>
          <select class="form-select" id="tx-action">
            <option value="">اختر النوع أولا</option>
          </select>
        </div>
        <div class="form-group">
          <label>المبلغ</label>
          <input type="number" id="tx-amount" class="form-input" min="0" step="any" placeholder="اكتب المبلغ">
        </div>
        <button class="modal-btn" onclick="submitTransactionForm()">تسجيل الترانزكشن</button>
      </div>
    </div>
  </div>
</div>

<!-- ===== الخزنة والمصروفات ===== -->
<div class="page" id="page-cash-expenses">
  <div class="toolbar">
    <div><div class="toolbar-title">🏦 الخزنة والمصروفات</div><div class="toolbar-sub">تسجيل دخل/صرف وخانات المصروفات في مكان واحد</div></div>
  </div>
  <div class="sections-row">
    <div class="section">
      <div class="section-header"><span class="section-title">حركة خزنة</span></div>
      <div style="padding:16px;">
        <div class="form-group">
          <label>النوع</label>
          <select class="form-select" id="cash-type">
            <option value="دخل">دخل</option>
            <option value="صرف">صرف</option>
          </select>
        </div>
        <div class="form-group"><label>المبلغ</label><input type="number" id="cash-amount" class="form-input" min="0" step="any"></div>
        <div class="form-group"><label>الوصف</label><input type="text" id="cash-desc" class="form-input"></div>
        <button class="modal-btn" onclick="submitCashForm()">تسجيل حركة خزنة</button>
      </div>
    </div>
    <div class="section">
      <div class="section-header"><span class="section-title">المصروفات الإدارية</span></div>
      <div style="padding:16px;">
        <div class="form-group"><label>بند إداري</label><select id="edari-band-select" class="form-select"><option value="">اختر البند</option></select></div>
        <div class="form-group"><label>مبلغ إداري</label><input type="number" id="edari-amount" class="form-input" min="0" step="any"></div>
        <button class="modal-btn" style="margin-bottom:12px;" onclick="submitEdariForm()">تسجيل مصروف إداري</button>
        <div class="form-group"><label>إضافة بند جديد</label><input type="text" id="new-band-name" class="form-input" placeholder="اسم البند الجديد"></div>
        <button class="modal-btn" style="background:var(--purple)" onclick="submitAddBandForm()">إضافة بند</button>
      </div>
    </div>
  </div>
  <div class="section" style="margin-top:12px;">
    <div class="section-header"><span class="section-title">المصروفات الأخرى</span></div>
    <div style="padding:16px;">
        <div class="form-group"><label>مبلغ مصروف آخر</label><input type="number" id="okhra-amount" class="form-input" min="0" step="any"></div>
        <div class="form-group"><label>بيان المصروف الآخر</label><input type="text" id="okhra-note" class="form-input"></div>
        <button class="modal-btn" onclick="submitOkhraForm()">تسجيل مصروف آخر</button>
    </div>
  </div>
</div>


<!-- Modals -->
<div class="modal-overlay" id="modal-khazna-in" onclick="if(event.target==this) closeModal('modal-khazna-in')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-khazna-in')">&times;</button>
    <div class="modal-title">💰 إيداع في الخزنة (دخل)</div>
    <form onsubmit="submitForm(event, '/api/add_khazna', {trans_type:'دخل', amount:this.amount.value, description:this.desc.value})">
      <div class="form-group"><label>المبلغ</label><input type="number" name="amount" class="form-input" required step="any" min="0"></div>
      <div class="form-group"><label>البيان / الوصف</label><input type="text" name="desc" class="form-input" required></div>
      <button type="submit" class="modal-btn" style="background:var(--green)">تسجيل الإيداع</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-khazna-out" onclick="if(event.target==this) closeModal('modal-khazna-out')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-khazna-out')">&times;</button>
    <div class="modal-title">💸 سحب من الخزنة (صرف)</div>
    <form onsubmit="submitForm(event, '/api/add_khazna', {trans_type:'صرف', amount:this.amount.value, description:this.desc.value})">
      <div class="form-group"><label>المبلغ</label><input type="number" name="amount" class="form-input" required step="any" min="0"></div>
      <div class="form-group"><label>البيان / الوصف</label><input type="text" name="desc" class="form-input" required></div>
      <button type="submit" class="modal-btn" style="background:var(--red)">تسجيل السحب</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-client" onclick="if(event.target==this) closeModal('modal-client')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-client')">&times;</button>
    <div class="modal-title">👥 حركة عميل</div>
    <form onsubmit="submitForm(event, '/api/add_client', {name:this.cname.value, amount:this.amount.value||0, trans_type:this.type.value})">
      <div class="form-group"><label>اسم العميل</label><select name="cname" id="client-name-select" class="form-select" required><option value="">اختر العميل</option></select></div>
      <div class="form-group"><label>المبلغ (اختياري)</label><input type="number" name="amount" class="form-input" step="any" min="0"></div>
      <div class="form-group">
        <label>نوع الحركة</label>
        <select name="type" class="form-select">
          <option value="دين">دين (العميل عليه فلوس ليك)</option>
          <option value="دفع">دفع (العميل دفع فلوس ليك)</option>
        </select>
      </div>
      <button type="submit" class="modal-btn">حفظ</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-supplier" onclick="if(event.target==this) closeModal('modal-supplier')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-supplier')">&times;</button>
    <div class="modal-title">🏭 حركة مورد</div>
    <form onsubmit="submitForm(event, '/api/add_supplier', {name:this.sname.value, amount:this.amount.value||0, trans_type:this.type.value})">
      <div class="form-group"><label>اسم المورد</label><select name="sname" id="supplier-name-select" class="form-select" required><option value="">اختر المورد</option></select></div>
      <div class="form-group"><label>المبلغ (اختياري)</label><input type="number" name="amount" class="form-input" step="any" min="0"></div>
      <div class="form-group">
        <label>نوع الحركة</label>
        <select name="type" class="form-select">
          <option value="دين">دين (المورد ليه فلوس عندك)</option>
          <option value="دفع">دفع (دفعت فلوس للمورد)</option>
        </select>
      </div>
      <button type="submit" class="modal-btn">حفظ</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-emp" onclick="if(event.target==this) closeModal('modal-emp')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-emp')">&times;</button>
    <div class="modal-title">➕ إضافة موظف جديد</div>
    <form onsubmit="submitForm(event, '/api/add_employee', {name:this.ename.value, salary:this.salary.value})">
      <div class="form-group"><label>اسم الموظف</label><input type="text" name="ename" class="form-input" required></div>
      <div class="form-group"><label>الراتب الأسبوعي</label><input type="number" name="salary" class="form-input" required step="any" min="0"></div>
      <button type="submit" class="modal-btn">تسجيل המوظف</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-emp-tx" onclick="if(event.target==this) closeModal('modal-emp-tx')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-emp-tx')">&times;</button>
    <div class="modal-title">💵 تسجيل معاملة موظف</div>
    <form onsubmit="submitEmployeeTxForm(event)">
      <div class="form-group"><label>اسم الموظف</label><select name="ename" id="emp-tx-name" class="form-select" required onchange="onEmployeeTxTypeChange()"><option value="">اختر الموظف</option></select></div>
      <div class="form-group"><label>المبلغ</label><input type="number" id="emp-tx-amount" name="amount" class="form-input" required step="any" min="0"></div>
      <div class="form-group">
        <label>نوع الحركة</label>
        <select name="type" id="emp-tx-type" class="form-select" onchange="onEmployeeTxTypeChange()">
          <option value="مرتب">صرف مرتب (تلقائي)</option>
          <option value="سلفة">سلفة</option>
          <option value="خصم">خصم</option>
          <option value="مكافأة">مكافأة</option>
        </select>
      </div>
      <div class="form-group"><label>ملاحظات (اختياري)</label><input type="text" name="note" class="form-input"></div>
      <button type="submit" class="modal-btn">تنفيذ</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-exp-edari" onclick="if(event.target==this) closeModal('modal-exp-edari')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-exp-edari')">&times;</button>
    <div class="modal-title">📌 تسجيل مصروف إداري</div>
    <form onsubmit="submitForm(event, '/api/add_expense_edari', {band:this.band.value, amount:this.amount.value})">
      <div class="form-group"><label>بند المصروف</label><select name="band" id="edari-band-modal-select" class="form-select" required><option value="">اختر البند</option></select></div>
      <div class="form-group"><label>المبلغ</label><input type="number" name="amount" class="form-input" required step="any" min="0"></div>
      <button type="submit" class="modal-btn">تسجيل</button>
    </form>
  </div>
</div>

<div class="modal-overlay" id="modal-exp-okhra" onclick="if(event.target==this) closeModal('modal-exp-okhra')">
  <div class="modal-content">
    <button class="modal-close" onclick="closeModal('modal-exp-okhra')">&times;</button>
    <div class="modal-title">➕ تسجيل مصروف آخر</div>
    <form onsubmit="submitForm(event, '/api/add_expense_okhra', {amount:this.amount.value, note:this.note.value})">
      <div class="form-group"><label>المبلغ</label><input type="number" name="amount" class="form-input" required step="any" min="0"></div>
      <div class="form-group"><label>البيان</label><input type="text" name="note" class="form-input" required></div>
      <button type="submit" class="modal-btn">تسجيل</button>
    </form>
  </div>
</div>

</main>


<script>
// ===== Modals Logic =====
async function openModal(id) {
  document.getElementById(id).classList.add('active');
  if (id === 'modal-client') await populateClientSelector();
  else if (id === 'modal-supplier') await populateSupplierSelector();
  else if (id === 'modal-emp-tx') await populateEmployeeSelector();
  else if (id === 'modal-exp-edari') await populateBandSelector();
}
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
async function submitForm(e, endpoint, data) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const oldText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner" style="margin:0"></span>';
  btn.disabled = true;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const result = await res.json();
    if (result.success) {
      closeModal(e.target.closest('.modal-overlay').id);
      e.target.reset();
      const activePage = document.querySelector('.page.active').id.replace('page-','');
      showPage(activePage);
      // Optional: show a toast notification
    } else {
      alert('❌ حدث خطأ: ' + (result.error || 'غير معروف'));
    }
  } catch (err) {
    alert('❌ فشل الاتصال بالخادم');
  }
  btn.innerHTML = oldText;
  btn.disabled = false;
}
function updateSelectOptions(id, list, placeholder='اختر') {
  const select = document.getElementById(id);
  if(!select) return;
  select.innerHTML = `<option value="">${placeholder}</option>` + list.map(item => `<option value="${item}">${item}</option>`).join('');
}

// ===== Globals =====
let clientsData = [], suppliersData = [], empData = [];
const fmt = n => Number(n).toLocaleString('ar-EG',{maximumFractionDigits:1}) + ' ج';
const today = () => new Date().toISOString().split('T')[0];
const daysAgo = d => { const dt = new Date(); dt.setDate(dt.getDate()-d); return dt.toISOString().split('T')[0]; };
const jsArg = s => String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r?\n/g, ' ');
const COLORS = ['blue','green','yellow','purple','orange','red','cyan'];

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}
function toggleNavGroup(id){
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}

function showPage(name, el) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  if(el) el.classList.add('active');
  // Close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
  if(name==='overview') loadOverview();
  else if(name==='clients') loadClients();
  else if(name==='suppliers') loadSuppliers();
  else if(name==='employees') loadEmployees();
  else if(name==='expenses') loadExpenses();
  else if(name==='daily') initDaily();
  else if(name==='transactions') initTransactionsPage();
}

function setQuick(page, days, el) {
  el.closest('.btn-group').querySelectorAll('.quick-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  const from = daysAgo(days), to = today();
  if(page==='overview'){ document.getElementById('ov-from').value=from; document.getElementById('ov-to').value=to; loadOverview(); }
  else if(page==='clients'){ document.getElementById('cl-from').value=from; document.getElementById('cl-to').value=to; loadClients(); }
  else if(page==='suppliers'){ document.getElementById('sp-from').value=from; document.getElementById('sp-to').value=to; loadSuppliers(); }
  else if(page==='expenses'){ document.getElementById('ex-from').value=from; document.getElementById('ex-to').value=to; loadExpenses(); }
}

async function api(url) {
  const res = await fetch('/api/'+url);
  if (res.status === 401) {
    window.location.href = '/login';
    return {};
  }
  return res.json();
}

async function postApi(endpoint, data) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  if (res.status === 401) {
    window.location.href = '/login';
    return {success:false, error:'Unauthorized'};
  }
  return res.json();
}

function reportDates(report) {
  if (report === 'overview') return [document.getElementById('ov-from').value, document.getElementById('ov-to').value];
  if (report === 'clients') return [document.getElementById('cl-from').value, document.getElementById('cl-to').value];
  if (report === 'suppliers') return [document.getElementById('sp-from').value, document.getElementById('sp-to').value];
  if (report === 'expenses') return [document.getElementById('ex-from').value, document.getElementById('ex-to').value];
  if (report === 'employees') return [daysAgo(7), today()];
  if (report === 'daily') {
    const d = document.getElementById('daily-custom').value || today();
    return [d, d];
  }
  return [daysAgo(30), today()];
}

function openReportExport(report, fmt) {
  const [from, to] = reportDates(report);
  window.open(`/export/report/${report}/${fmt}?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`, '_blank');
}

function openPersonExport(kind, name, fmt) {
  const from = kind === 'client' ? document.getElementById('cl-from').value : document.getElementById('sp-from').value;
  const to = kind === 'client' ? document.getElementById('cl-to').value : document.getElementById('sp-to').value;
  window.open(`/export/person/${kind}/${fmt}?name=${encodeURIComponent(name)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`, '_blank');
}

// ===== Transactions Page =====
function getTxActions(personType) {
  if (personType === 'client') {
    return [
      {value: 'دين', label: 'دين على العميل'},
      {value: 'دفع', label: 'استلام فلوس (دفع)'},
      {value: 'خصم', label: 'خصم من الرصيد'}
    ];
  }
  if (personType === 'supplier') {
    return [
      {value: 'مديونية', label: 'مديونية للمورد'},
      {value: 'دفع', label: 'دفع للمورد'}
    ];
  }
  return [];
}

async function onTxPersonTypeChange() {
  const personType = document.getElementById('tx-person-type').value;
  const personSelect = document.getElementById('tx-person-name');
  const actionSelect = document.getElementById('tx-action');
  personSelect.innerHTML = '<option value="">جاري التحميل...</option>';
  actionSelect.innerHTML = '<option value="">اختر الحركة</option>';

  const actions = getTxActions(personType);
  actions.forEach(a => {
    actionSelect.innerHTML += `<option value="${a.value}">${a.label}</option>`;
  });

  if (!personType) {
    personSelect.innerHTML = '<option value="">اختر النوع أولا</option>';
    return;
  }
  const data = await api(personType === 'client' ? 'clients' : 'suppliers');
  if (!Array.isArray(data)) {
    personSelect.innerHTML = '<option value="">فشل التحميل</option>';
    return;
  }
  if (!data.length) {
    personSelect.innerHTML = '<option value="">لا يوجد أسماء</option>';
    return;
  }
  personSelect.innerHTML = '<option value="">اختر الاسم</option>';
  data.forEach(item => {
    personSelect.innerHTML += `<option value="${item.name}">${item.name}</option>`;
  });
}

function initTransactionsPage() {
  if (!clientsData.length) loadClients();
  if (!suppliersData.length) loadSuppliers();
  const personType = document.getElementById('tx-person-type').value;
  if (personType) onTxPersonTypeChange();
}

async function submitTransactionForm() {
  const personType = document.getElementById('tx-person-type').value;
  const name = document.getElementById('tx-person-name').value;
  const transType = document.getElementById('tx-action').value;
  const amount = parseFloat(document.getElementById('tx-amount').value || '0');
  if (!personType || !name || !transType || !(amount > 0)) {
    alert('❌ اكمل كل البيانات بشكل صحيح');
    return;
  }

  const endpoint = personType === 'client' ? '/api/add_client' : '/api/add_supplier';
  const result = await postApi(endpoint, {name, amount, trans_type: transType});
  if (result.success) {
    alert('✅ تم تسجيل الترانزكشن');
    document.getElementById('tx-amount').value = '';
  } else {
    alert('❌ حدث خطأ: ' + (result.error || 'غير معروف'));
  }
}

async function submitAddPersonForm() {
  const type = document.getElementById('tx-add-type').value;
  const name = document.getElementById('tx-add-name').value.trim();
  if (!name) {
    alert('❌ اكتب الاسم');
    return;
  }
  const endpoint = type === 'client' ? '/api/add_person/client' : '/api/add_person/supplier';
  const result = await postApi(endpoint, {name});
  if (result.success) {
    alert('✅ تمت الإضافة');
    document.getElementById('tx-add-name').value = '';
    if (type === 'client') await loadClients();
    else await loadSuppliers();
  } else {
    alert('❌ حدث خطأ: ' + (result.error || 'غير معروف'));
  }
}

// ===== Cash & Expenses Page =====
async function submitCashForm() {
  const trans_type = document.getElementById('cash-type').value;
  const amount = parseFloat(document.getElementById('cash-amount').value || '0');
  const description = document.getElementById('cash-desc').value.trim();
  if (!(amount > 0) || !description) {
    alert('❌ اكتب المبلغ والوصف');
    return;
  }
  const result = await postApi('/api/add_khazna', {trans_type, amount, description});
  if (result.success) {
    alert('✅ تم تسجيل حركة الخزنة');
    document.getElementById('cash-amount').value = '';
    document.getElementById('cash-desc').value = '';
  } else {
    alert('❌ حدث خطأ');
  }
}

async function submitEdariForm() {
  const band = document.getElementById('edari-band-select').value;
  const amount = parseFloat(document.getElementById('edari-amount').value || '0');
  if (!band || !(amount > 0)) {
    alert('❌ اكتب البند والمبلغ');
    return;
  }
  const result = await postApi('/api/add_expense_edari', {band, amount});
  if (result.success) {
    alert('✅ تم تسجيل المصروف الإداري');
    document.getElementById('edari-band-select').value = '';
    document.getElementById('edari-amount').value = '';
  } else {
    alert('❌ حدث خطأ');
  }
}

async function submitOkhraForm() {
  const amount = parseFloat(document.getElementById('okhra-amount').value || '0');
  const note = document.getElementById('okhra-note').value.trim();
  if (!(amount > 0) || !note) {
    alert('❌ اكتب المبلغ والبيان');
    return;
  }
  const result = await postApi('/api/add_expense_okhra', {amount, note});
  if (result.success) {
    alert('✅ تم تسجيل مصروف آخر');
    document.getElementById('okhra-amount').value = '';
    document.getElementById('okhra-note').value = '';
  } else {
    alert('❌ حدث خطأ');
  }
}

async function submitAddBandForm() {
  const name = document.getElementById('new-band-name').value.trim();
  if (!name) {
    alert('❌ اكتب اسم البند');
    return;
  }
  const result = await postApi('/api/add_band', {name});
  if (result.success) {
    alert('✅ تم إضافة البند');
    document.getElementById('new-band-name').value = '';
    await populateBandSelector();
  } else {
    alert('❌ حدث خطأ: ' + (result.error || 'غير معروف'));
  }
}

async function populateClientSelector() {
  if (!clientsData.length) await loadClients();
  updateSelectOptions('client-name-select', clientsData.map(c => c.name), 'اختر العميل');
}

async function populateSupplierSelector() {
  if (!suppliersData.length) await loadSuppliers();
  updateSelectOptions('supplier-name-select', suppliersData.map(s => s.name), 'اختر المورد');
}

async function populateEmployeeSelector() {
  if (!empData.length) await loadEmployees();
  updateSelectOptions('emp-tx-name', empData.map(e => e.name), 'اختر الموظف');
  onEmployeeTxTypeChange();
}

async function populateBandSelector() {
  const bands = await api('bands');
  if (!Array.isArray(bands)) return;
  updateSelectOptions('edari-band-select', bands, bands.length ? 'اختر البند' : 'لا توجد بنود');
  updateSelectOptions('edari-band-modal-select', bands, bands.length ? 'اختر البند' : 'لا توجد بنود');
}

function onEmployeeTxTypeChange() {
  const type = document.getElementById('emp-tx-type')?.value;
  const name = document.getElementById('emp-tx-name')?.value;
  const amountInput = document.getElementById('emp-tx-amount');
  if (!amountInput) return;

  if (type === 'مرتب') {
    const emp = empData.find(e => e.name === name);
    const net = emp && emp.data ? Number(emp.data.net || 0) : 0;
    amountInput.value = net > 0 ? net : 0;
    amountInput.readOnly = true;
  } else {
    amountInput.readOnly = false;
    if (Number(amountInput.value) <= 0) amountInput.value = '';
  }
}

async function submitEmployeeTxForm(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const oldText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner" style="margin:0"></span>';
  btn.disabled = true;
  try {
    const name = document.getElementById('emp-tx-name').value;
    const trans_type = document.getElementById('emp-tx-type').value;
    const amount = parseFloat(document.getElementById('emp-tx-amount').value || '0');
    const note = form.note.value || '';
    if (!name || !(amount > 0)) {
      alert('❌ اختار الموظف واكتب مبلغ صحيح');
      return;
    }
    const result = await postApi('/api/add_employee_tx', {name, trans_type, amount, note});
    if (result.success) {
      closeModal('modal-emp-tx');
      form.reset();
      const activePage = document.querySelector('.page.active').id.replace('page-','');
      showPage(activePage);
    } else {
      alert('❌ حدث خطأ: ' + (result.error || 'غير معروف'));
    }
  } catch (err) {
    alert('❌ فشل الاتصال بالخادم');
  } finally {
    btn.innerHTML = oldText;
    btn.disabled = false;
  }
}

// ===== Overview =====
async function loadOverview() {
  const from = document.getElementById('ov-from').value || daysAgo(7);
  const to = document.getElementById('ov-to').value || today();
  document.getElementById('ov-from').value = from;
  document.getElementById('ov-to').value = to;
  document.getElementById('overview-period').textContent = `من ${from} إلى ${to}`;
  document.getElementById('ov-month').textContent = `${from} → ${to}`;
  document.getElementById('overview-cards').innerHTML = skeletonCards(8);

  const [ov, daily] = await Promise.all([
    api(`overview?from=${from}&to=${to}`),
    api(`daily/${today()}`)
  ]);
  
  if(!ov.balance && ov.balance !== 0) return; // Unauth

  const bc = ov.balance >= 0 ? 'green':'red';
  const nc = ov.net >= 0 ? 'green':'red';
  document.getElementById('overview-cards').innerHTML = `
    <div class="card ${bc}"><div class="card-label">رصيد الخزنة الكلي</div><div class="card-value ${bc}">${fmt(ov.balance)}</div><div class="card-sub">الرصيد الإجمالي</div><span class="card-icon">🏦</span></div>
    <div class="card blue"><div class="card-label">دخل الفترة</div><div class="card-value blue">${fmt(ov.period_in)}</div><div class="card-sub">${from} → ${to}</div><span class="card-icon">📈</span></div>
    <div class="card red"><div class="card-label">صرف الفترة</div><div class="card-value red">${fmt(ov.period_out)}</div><div class="card-sub">إجمالي المصروفات</div><span class="card-icon">📉</span></div>
    <div class="card ${nc}"><div class="card-label">صافي الفترة</div><div class="card-value ${nc}">${fmt(ov.net)}</div><div class="card-sub">${ov.net>=0?'ربح':'خسارة'}</div><span class="card-icon">💹</span></div>
    <div class="card yellow"><div class="card-label">مديونيات الموردين</div><div class="card-value yellow">${fmt(ov.suppliers_debt)}</div><div class="card-sub">إجمالي ما علينا</div><span class="card-icon">🏭</span></div>
    <div class="card green"><div class="card-label">فلوس العملاء</div><div class="card-value green">${fmt(ov.clients_credit)}</div><div class="card-sub">إجمالي ما لنا</div><span class="card-icon">👥</span></div>
    <div class="card purple"><div class="card-label">مرتبات مستحقة</div><div class="card-value purple">${fmt(ov.salary_due)}</div><div class="card-sub">إجمالي الموظفين</div><span class="card-icon">👷</span></div>
    <div class="card cyan"><div class="card-label">حركات اليوم</div><div class="card-value blue">${daily.records ? daily.records.length : 0}</div><div class="card-sub">إجمالي ${fmt(daily.total_in || 0)} دخل</div><span class="card-icon">⚡</span></div>
  `;

  const maxV = Math.max(ov.period_in, ov.period_out, 1);
  document.getElementById('ov-chart').innerHTML = `
    <div class="bar-row"><span class="bar-label">الدخل</span><div class="bar-track"><div class="bar-fill green" style="width:${(ov.period_in/maxV)*100}%"></div></div><span class="bar-amount">${fmt(ov.period_in)}</span></div>
    <div class="bar-row"><span class="bar-label">الصرف</span><div class="bar-track"><div class="bar-fill red" style="width:${(ov.period_out/maxV)*100}%"></div></div><span class="bar-amount">${fmt(ov.period_out)}</span></div>
    <div class="bar-row"><span class="bar-label">الصافي</span><div class="bar-track"><div class="bar-fill ${ov.net>=0?'blue':'red'}" style="width:${Math.min(Math.abs(ov.net)/maxV*100,100)}%"></div></div><span class="bar-amount">${fmt(ov.net)}</span></div>
  `;

  document.getElementById('ov-txcount').textContent = (daily.records ? daily.records.length : 0) + ' حركة';
  if (!daily.records || !daily.records.length) {
    document.getElementById('ov-recent').innerHTML = '<div class="empty">مفيش حركات اليوم</div>';
  } else {
    let h = '<table><thead><tr><th>النوع</th><th>المبلغ</th><th>الوصف</th></tr></thead><tbody>';
    daily.records.slice(0,8).forEach(r => {
      h += `<tr><td><span class="tag ${r.type==='دخل'?'tag-in':'tag-out'}">${r.type}</span></td><td class="${r.type==='دخل'?'amt-pos':'amt-neg'}">${fmt(r.amount)}</td><td>${r.description||'-'}</td></tr>`;
    });
    h += '</tbody></table>';
    document.getElementById('ov-recent').innerHTML = h;
  }
}

// ===== Clients =====
async function loadClients() {
  const from = document.getElementById('cl-from').value || daysAgo(3650);
  const to = document.getElementById('cl-to').value || today();
  document.getElementById('cl-from').value = from;
  document.getElementById('cl-to').value = to;
  document.getElementById('clients-table').innerHTML = '<div class="loading"><span class="spinner"></span></div>';
  const data = await api(`clients?from=${from}&to=${to}`);
  if(!data || data.error) return;
  clientsData = data;
  renderClientsTable(data);
}

function renderClientsTable(data) {
  if (!data.length) { document.getElementById('clients-table').innerHTML = '<div class="empty">مفيش عملاء</div>'; return; }
  let totalDebt = 0;
  let h = '<table><thead><tr><th>العميل</th><th>الحالة</th><th>الرصيد</th><th>تصدير الفترة</th></tr></thead><tbody>';
  data.forEach(c => {
    let cls, txt;
    if(c.balance>0){cls='tag-debt';txt='عليه';totalDebt+=c.balance;}
    else if(c.balance<0){cls='tag-credit';txt='ليه عندنا';}
    else{cls='tag-zero';txt='صفر';}
    const ac = c.balance>0?'amt-neg':c.balance<0?'amt-pos':'amt-neu';
    const nameArg = jsArg(c.name);
    h += `<tr><td><strong>${c.name}</strong></td><td><span class="tag ${cls}">${txt}</span></td><td class="${ac}">${fmt(Math.abs(c.balance))}</td><td><div class="row-actions"><button class="btn small" onclick="openPersonExport('client','${nameArg}','pdf')">PDF</button><button class="btn small" onclick="openPersonExport('client','${nameArg}','excel')">Excel</button></div></td></tr>`;
  });
  h += '</tbody></table>';
  document.getElementById('clients-table').innerHTML = h;
  document.getElementById('clients-badge').textContent = `${data.length} عميل | ديون: ${fmt(totalDebt)}`;
}

function filterClientsTable() {
  const filter = document.getElementById('client-filter').value;
  const search = document.getElementById('client-search').value.toLowerCase();
  let filtered = clientsData.filter(c => {
    if(search && !c.name.toLowerCase().includes(search)) return false;
    if(filter==='debt') return c.balance>0;
    if(filter==='credit') return c.balance<0;
    if(filter==='zero') return c.balance===0;
    return true;
  });
  renderClientsTable(filtered);
}

// ===== Suppliers =====
async function loadSuppliers() {
  const from = document.getElementById('sp-from').value || daysAgo(3650);
  const to = document.getElementById('sp-to').value || today();
  document.getElementById('sp-from').value = from;
  document.getElementById('sp-to').value = to;
  document.getElementById('suppliers-table').innerHTML = '<div class="loading"><span class="spinner"></span></div>';
  const data = await api(`suppliers?from=${from}&to=${to}`);
  if(!data || data.error) return;
  suppliersData = data;
  renderSuppliersTable(data);
}

function renderSuppliersTable(data) {
  if (!data.length) { document.getElementById('suppliers-table').innerHTML = '<div class="empty">مفيش موردين</div>'; return; }
  let total = 0;
  let h = '<table><thead><tr><th>المورد</th><th>الحالة</th><th>الرصيد</th><th>تصدير الفترة</th></tr></thead><tbody>';
  data.forEach(s => {
    let cls, txt;
    if(s.balance>0){cls='tag-debt';txt='ليه علينا';total+=s.balance;}
    else if(s.balance<0){cls='tag-credit';txt='دفعنا زيادة';}
    else{cls='tag-zero';txt='صفر';}
    const ac = s.balance>0?'amt-neg':'amt-neu';
    const nameArg = jsArg(s.name);
    h += `<tr><td><strong>${s.name}</strong></td><td><span class="tag ${cls}">${txt}</span></td><td class="${ac}">${fmt(Math.abs(s.balance))}</td><td><div class="row-actions"><button class="btn small" onclick="openPersonExport('supplier','${nameArg}','pdf')">PDF</button><button class="btn small" onclick="openPersonExport('supplier','${nameArg}','excel')">Excel</button></div></td></tr>`;
  });
  h += '</tbody></table>';
  document.getElementById('suppliers-table').innerHTML = h;
  document.getElementById('suppliers-badge').textContent = `${data.length} مورد | مديونيات: ${fmt(total)}`;
}

function filterSuppliersTable() {
  const filter = document.getElementById('supplier-filter').value;
  const search = document.getElementById('supplier-search').value.toLowerCase();
  let filtered = suppliersData.filter(s => {
    if(search && !s.name.toLowerCase().includes(search)) return false;
    if(filter==='debt') return s.balance>0;
    if(filter==='zero') return s.balance===0;
    return true;
  });
  renderSuppliersTable(filtered);
}

// ===== Employees =====
async function loadEmployees() {
  document.getElementById('emp-table').innerHTML = '<div class="loading"><span class="spinner"></span></div>';
  const data = await api('employees');
  if(!data || data.error) return;
  empData = data;
  renderEmpTable(data);
}

function renderEmpTable(data) {
  if (!data.length) { document.getElementById('emp-table').innerHTML = '<div class="empty">مفيش موظفين</div>'; return; }
  let totalDue = 0;
  let h = '<table><thead><tr><th>الموظف</th><th>المرتب</th><th>أسابيع</th><th>المستحق</th><th>سلف</th><th>خصم</th><th>مكافآت</th><th>تم صرف</th><th>الصافي</th></tr></thead><tbody>';
  data.forEach(e => {
    const d = e.data;
    if(d.net>0) totalDue+=d.net;
    const nc = d.net>0?'amt-neg':d.net<0?'amt-pos':'amt-neu';
    h += `<tr><td><strong>${e.name}</strong></td><td>${fmt(d.salary)}</td><td>${d.weeks}</td><td class="amt-neg">${fmt(d.total_salary_due)}</td><td>${fmt(d.advances)}</td><td>${fmt(d.deductions)}</td><td class="amt-pos">${fmt(d.bonuses)}</td><td>${fmt(d.total_paid)}</td><td class="${nc}"><strong>${fmt(d.net)}</strong></td></tr>`;
  });
  h += '</tbody></table>';
  document.getElementById('emp-table').innerHTML = h;
  document.getElementById('emp-badge').textContent = `${data.length} موظف | مستحق: ${fmt(totalDue)}`;
}

function filterEmpTable() {
  const s = document.getElementById('emp-search').value.toLowerCase();
  renderEmpTable(s ? empData.filter(e=>e.name.toLowerCase().includes(s)) : empData);
}

// ===== Expenses =====
async function loadExpenses() {
  const from = document.getElementById('ex-from').value || daysAgo(30);
  const to = document.getElementById('ex-to').value || today();
  document.getElementById('ex-from').value = from;
  document.getElementById('ex-to').value = to;
  document.getElementById('ex-bands').innerHTML = '<div class="loading"><span class="spinner"></span></div>';
  const data = await api(`expenses?from=${from}&to=${to}`);
  if(!data || data.error) return;
  const maxV = Math.max(...Object.values(data.bands||{}), data.okhra||0, 1);
  let chart = '';
  Object.entries(data.bands||{}).forEach(([band,amt],i)=>{
    chart += `<div class="bar-row"><span class="bar-label">${band}</span><div class="bar-track"><div class="bar-fill ${COLORS[i%COLORS.length]}" style="width:${(amt/maxV)*100}%"></div></div><span class="bar-amount">${fmt(amt)}</span></div>`;
  });
  if(data.okhra>0) chart += `<div class="bar-row"><span class="bar-label">أخرى</span><div class="bar-track"><div class="bar-fill red" style="width:${(data.okhra/maxV)*100}%"></div></div><span class="bar-amount">${fmt(data.okhra)}</span></div>`;
  document.getElementById('ex-bands').innerHTML = chart || '<div class="empty">مفيش مصروفات</div>';
  const total = (data.total_bands||0) + (data.okhra||0);
  document.getElementById('ex-summary').innerHTML = `
    <table>
      <tr><td>مصروفات إدارية</td><td class="amt-neg">${fmt(data.total_bands||0)}</td></tr>
      <tr><td>مصروفات أخرى</td><td class="amt-neg">${fmt(data.okhra||0)}</td></tr>
      <tr><td><strong>الإجمالي</strong></td><td class="amt-neg"><strong>${fmt(total)}</strong></td></tr>
    </table>
  `;
}

// ===== Daily =====
function initDaily() {
  const t = new Date(), dow = t.getDay();
  const dfsn = (dow+1)%7;
  const sat = new Date(t); sat.setDate(t.getDate()-dfsn);
  const days = ['السبت','الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة'];
  let h = '';
  for(let i=0;i<7;i++){
    const d=new Date(sat); d.setDate(sat.getDate()+i);
    const ds=d.toISOString().split('T')[0];
    const isT=ds===today();
    h+=`<button class="day-btn ${isT?'active':''}" onclick="loadDailyReport('${ds}',this)">${days[i]}<small>${d.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})}</small></button>`;
  }
  document.getElementById('day-selector').innerHTML=h;
  document.getElementById('daily-custom').value=today();
  loadDailyReport(today(),null);
}

function loadDailyCustom(){
  const d=document.getElementById('daily-custom').value;
  if(d) loadDailyReport(d,null);
}

async function loadDailyReport(dateStr, btn) {
  if(btn){document.querySelectorAll('.day-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}
  document.getElementById('daily-content').innerHTML='<div class="loading"><span class="spinner"></span></div>';
  const data=await api('daily/'+dateStr);
  if(!data || data.error) return;
  if(!data.records||!data.records.length){document.getElementById('daily-content').innerHTML='<div class="empty">مفيش حركات</div>';return;}
  let h=`<div class="summary-grid">
    <div class="summary-item"><div class="summary-label">دخل</div><div class="summary-val amt-pos">${fmt(data.total_in)}</div></div>
    <div class="summary-item"><div class="summary-label">صرف</div><div class="summary-val amt-neg">${fmt(data.total_out)}</div></div>
    <div class="summary-item"><div class="summary-label">صافي</div><div class="summary-val ${data.net>=0?'amt-pos':'amt-neg'}">${fmt(data.net)}</div></div>
  </div><div class="table-wrap"><table><thead><tr><th>النوع</th><th>المبلغ</th><th>الوصف</th></tr></thead><tbody>`;
  data.records.forEach(r=>{
    h+=`<tr><td><span class="tag ${r.type==='دخل'?'tag-in':'tag-out'}">${r.type}</span></td><td class="${r.type==='دخل'?'amt-pos':'amt-neg'}">${fmt(r.amount)}</td><td>${r.description||'-'}</td></tr>`;
  });
  h+='</tbody></table></div>';
  document.getElementById('daily-content').innerHTML=h;
}

function skeletonCards(n) {
  return Array(n).fill('<div class="card blue"><div class="skeleton" style="width:60%;height:11px"></div><div class="skeleton" style="width:80%;height:22px;margin-top:8px"></div><div class="skeleton" style="width:40%;height:11px;margin-top:6px"></div></div>').join('');
}

// ===== Init =====
document.getElementById('ov-from').value = daysAgo(7);
document.getElementById('ov-to').value = today();
document.getElementById('last-update').textContent = new Date().toLocaleTimeString('ar-EG');
loadOverview();
</script>
</body>
</html>'''

# ============ API ============

def _get_date_range(default_days=30):
    date_from = request.args.get('from', str(date.today() - timedelta(days=default_days)))
    date_to = request.args.get('to', str(date.today()))
    return date_from, date_to

def _money(value):
    return f"{float(value or 0):,.2f}"

def _safe_filename(value):
    cleaned = re.sub(r'[\\/:*?"<>|]+', '-', str(value)).strip()
    return cleaned or 'report'

def _person_type_from_kind(kind):
    if kind == 'client':
        return 'عميل', 'عميل'
    if kind == 'supplier':
        return 'مورد', 'مورد'
    return None, None

def _transaction_totals(rows):
    dues = sum(float(r['amount'] or 0) for r in rows if r['type'] in ('دين', 'مديونية'))
    payments = sum(float(r['amount'] or 0) for r in rows if r['type'] in ('دفع', 'خصم'))
    return dues, payments, dues - payments

def _excel_response(title, subtitle, headers, rows, filename):
    html_rows = ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(cell))}</td>' for cell in row) + '</tr>'
        for row in rows
    )
    html_doc = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><style>
body{{font-family:Tahoma,Arial,sans-serif;direction:rtl}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #999;padding:7px;text-align:center}}
th{{background:#d9eaf7;font-weight:bold}}
.title{{font-size:18px;font-weight:bold;margin-bottom:6px}}
.sub{{margin-bottom:12px;color:#444}}
</style></head>
<body>
<div class="title">{html.escape(title)}</div>
<div class="sub">{html.escape(subtitle)}</div>
<table><thead><tr>{''.join(f'<th>{html.escape(str(h))}</th>' for h in headers)}</tr></thead><tbody>{html_rows}</tbody></table>
</body></html>"""
    safe = _safe_filename(filename)
    encoded_name = quote(safe)
    return Response(
        '\ufeff' + html_doc,
        mimetype='application/vnd.ms-excel; charset=utf-8',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_name}.xls"}
    )

def _pdf_response(title, subtitle, headers, rows, filename):
    try:
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return jsonify({'error': 'ReportLab غير متاح'}), 500

    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Amiri-Regular.ttf")
    font_name = 'Helvetica'
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Amiri', font_path))
            font_name = 'Amiri'
        except Exception:
            font_name = 'Helvetica'

    def ar(value):
        text = str(value)
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ArabicTitle', parent=styles['Title'], fontName=font_name, alignment=1, fontSize=16)
    sub_style = ParagraphStyle('ArabicSub', parent=styles['Normal'], fontName=font_name, alignment=1, fontSize=11)
    elements = [Paragraph(ar(title), title_style), Paragraph(ar(subtitle), sub_style), Spacer(1, 12)]

    data = [[ar(h) for h in headers]]
    data.extend([[ar(cell) for cell in row] for row in rows])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fb')]),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    safe = _safe_filename(filename)
    encoded_name = quote(safe)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f"inline; filename*=UTF-8''{encoded_name}.pdf"}
    )

def _export_response(fmt, title, subtitle, headers, rows, filename):
    if fmt == 'excel':
        return _excel_response(title, subtitle, headers, rows, filename)
    if fmt == 'pdf':
        return _pdf_response(title, subtitle, headers, rows, filename)
    return jsonify({'error': 'صيغة غير مدعومة'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '').strip()

        user = authenticate_dashboard_user(password)
        if user:
            companies = get_user_companies(user['id'])
            if not companies:
                error = "هذا المستخدم غير مربوط بأي شركة"
                return render_template_string(LOGIN_HTML, error=error)

            session.clear()
            session['user_id'] = user['id']
            session['username'] = user.get('username', '')
            if len(companies) == 1:
                session['company_id'] = companies[0]['id']
                session['company_name'] = companies[0]['name']
                return redirect(url_for('index'))
            return redirect(url_for('select_company'))
        else:
            error = "كلمة المرور غير صحيحة"

    return render_template_string(LOGIN_HTML, error=error)

@app.route('/select-company', methods=['GET', 'POST'])
def select_company():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    companies = get_user_companies(user_id)
    if not companies:
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            company_id = int(request.form.get('company_id', '0'))
        except ValueError:
            company_id = 0

        if company_id and user_has_company(user_id, company_id):
            chosen = next((c for c in companies if c['id'] == company_id), None)
            if chosen:
                session['company_id'] = chosen['id']
                session['company_name'] = chosen['name']
                return redirect(url_for('index'))

    if len(companies) == 1:
        session['company_id'] = companies[0]['id']
        session['company_name'] = companies[0]['name']
        return redirect(url_for('index'))

    return render_template_string(SELECT_COMPANY_HTML, companies=companies)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template_string(DASHBOARD_HTML, company_name=session.get('company_name', 'الشركة'))

@app.route('/api/overview')
@login_required
def api_overview():
    company_id = session['company_id']
    date_from, date_to = _get_date_range(7)

    try:
        balance = get_balance(company_id)
        rows, period_in, period_out = get_khazna_range(date_from, date_to, company_id)
        net = period_in - period_out

        suppliers_debt = sum(
            max(get_person_balance("مورد", n, company_id), 0)
            for n in get_all_suppliers(company_id)
        )
        clients_credit = sum(
            max(get_person_balance("عميل", n, company_id), 0)
            for n in get_all_clients(company_id)
        )
        salary_due = sum(
            max(e['data']['net'], 0)
            for e in get_weekly_employees_report(company_id)
        )

        result = {
            'balance': balance,
            'period_in': period_in,
            'period_out': period_out,
            'net': net,
            'suppliers_debt': suppliers_debt,
            'clients_credit': clients_credit,
            'salary_due': salary_due,
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_khazna', methods=['POST'])
@login_required
def api_add_khazna():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        trans_type = data.get('trans_type')
        amount = float(data.get('amount', 0))
        description = data.get('description', '').strip()
        if trans_type not in ('دخل', 'صرف') or amount <= 0 or not description:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        add_transaction(trans_type, amount, description, company_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_client', methods=['POST'])
@login_required
def api_add_client():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        trans_type = data.get('trans_type')
        amount = float(data.get('amount', 0))
        if not name or trans_type not in ('دين', 'دفع', 'خصم') or amount <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        add_client(name, amount, trans_type, company_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_supplier', methods=['POST'])
@login_required
def api_add_supplier():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        trans_type = data.get('trans_type')
        amount = float(data.get('amount', 0))
        if not name or trans_type not in ('مديونية', 'دين', 'دفع') or amount <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        if trans_type == 'دين':
            trans_type = 'مديونية'
        add_supplier(name, amount, trans_type, company_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_employee', methods=['POST'])
@login_required
def api_add_employee():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        salary = float(data.get('salary', 0))
        if not name or salary <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        ok = add_employee(name, salary, company_id)
        if not ok:
            return jsonify({'success': False, 'error': 'الموظف موجود بالفعل'}), 400
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_employee_tx', methods=['POST'])
@login_required
def api_add_employee_tx():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        trans_type = data.get('trans_type')
        amount = float(data.get('amount', 0))
        note = data.get('note', '').strip()
        if not name or trans_type not in ('مرتب', 'سلفة', 'خصم', 'مكافأة') or amount <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        add_employee_transaction(name, trans_type, amount, company_id, note)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_expense_edari', methods=['POST'])
@login_required
def api_add_expense_edari():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        band = data.get('band', '').strip()
        amount = float(data.get('amount', 0))
        if not band or amount <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        add_masrof_edari(band, amount, company_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_expense_okhra', methods=['POST'])
@login_required
def api_add_expense_okhra():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get('amount', 0))
        note = data.get('note', '').strip()
        if amount <= 0 or not note:
            return jsonify({'success': False, 'error': 'بيانات غير صحيحة'}), 400
        add_masrof_okhra(amount, note, company_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_person/<person_kind>', methods=['POST'])
@login_required
def api_add_person(person_kind):
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'الاسم مطلوب'}), 400
        person_type = 'عميل' if person_kind == 'client' else 'مورد' if person_kind == 'supplier' else None
        if not person_type:
            return jsonify({'success': False, 'error': 'نوع غير صحيح'}), 400
        ok = add_person(name, person_type, company_id)
        if not ok:
            return jsonify({'success': False, 'error': 'الاسم موجود بالفعل'}), 400
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_band', methods=['POST'])
@login_required
def api_add_band():
    company_id = session['company_id']
    data = request.get_json(silent=True) or {}
    try:
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'اسم البند مطلوب'}), 400
        ok = add_band(name, company_id)
        if not ok:
            return jsonify({'success': False, 'error': 'البند موجود بالفعل'}), 400
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bands')
@login_required
def api_bands():
    company_id = session['company_id']
    try:
        return jsonify(get_all_bands(company_id))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients')
@login_required
def api_clients():
    company_id = session['company_id']
    try:
        result = [{'name': n, 'balance': get_person_balance("عميل", n, company_id)} for n in get_all_clients(company_id)]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers')
@login_required
def api_suppliers():
    company_id = session['company_id']
    try:
        result = [{'name': n, 'balance': get_person_balance("مورد", n, company_id)} for n in get_all_suppliers(company_id)]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees')
@login_required
def api_employees():
    company_id = session['company_id']
    try:
        result = get_weekly_employees_report(company_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/expenses')
@login_required
def api_expenses():
    company_id = session['company_id']
    date_from, date_to = _get_date_range(30)
    try:
        bands, okhra = get_masrof_range(date_from, date_to, company_id)
        result = {'bands': bands, 'okhra': okhra, 'total_bands': sum(bands.values())}
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily/<selected_date>')
@login_required
def api_daily(selected_date):
    company_id = session['company_id']
    try:
        records, total_in, total_out = get_daily_khazna_report(selected_date, company_id)
        result = {'records': records, 'total_in': total_in, 'total_out': total_out, 'net': total_in - total_out}
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/report/<report_kind>/<fmt>')
@login_required
def export_report(report_kind, fmt):
    company_id = session['company_id']
    date_from, date_to = _get_date_range(30)
    company_name = session.get('company_name', 'الشركة')
    subtitle = f"{company_name} | من {date_from} إلى {date_to}"

    try:
        if report_kind == 'overview':
            balance = get_balance(company_id)
            _, period_in, period_out = get_khazna_range(date_from, date_to, company_id)
            suppliers_debt = sum(max(get_person_balance("مورد", n, company_id), 0) for n in get_all_suppliers(company_id))
            clients_credit = sum(max(get_person_balance("عميل", n, company_id), 0) for n in get_all_clients(company_id))
            salary_due = sum(max(e['data']['net'], 0) for e in get_weekly_employees_report(company_id))
            rows = [
                ['رصيد الخزنة الكلي', _money(balance)],
                ['دخل الفترة', _money(period_in)],
                ['صرف الفترة', _money(period_out)],
                ['صافي الفترة', _money(period_in - period_out)],
                ['مديونيات الموردين', _money(suppliers_debt)],
                ['فلوس العملاء', _money(clients_credit)],
                ['مرتبات مستحقة', _money(salary_due)],
            ]
            return _export_response(fmt, 'تقرير النظرة العامة', subtitle, ['البند', 'القيمة'], rows, 'overview-report')

        if report_kind == 'clients':
            rows = []
            for name in get_all_clients(company_id):
                transactions = get_person_transactions_range(name, 'عميل', date_from, date_to, company_id)
                dues, payments, net = _transaction_totals(transactions)
                rows.append([name, _money(dues), _money(payments), _money(net), _money(get_person_balance('عميل', name, company_id))])
            return _export_response(fmt, 'تقرير العملاء', subtitle, ['العميل', 'ديون الفترة', 'مدفوعات/خصومات الفترة', 'صافي الفترة', 'الرصيد الحالي'], rows, 'clients-report')

        if report_kind == 'suppliers':
            rows = []
            for name in get_all_suppliers(company_id):
                transactions = get_person_transactions_range(name, 'مورد', date_from, date_to, company_id)
                dues, payments, net = _transaction_totals(transactions)
                rows.append([name, _money(dues), _money(payments), _money(net), _money(get_person_balance('مورد', name, company_id))])
            return _export_response(fmt, 'تقرير الموردين', subtitle, ['المورد', 'مديونيات الفترة', 'مدفوعات الفترة', 'صافي الفترة', 'الرصيد الحالي'], rows, 'suppliers-report')

        if report_kind == 'expenses':
            bands, okhra = get_masrof_range(date_from, date_to, company_id)
            rows = [[band, _money(total)] for band, total in bands.items()]
            rows.append(['مصروفات أخرى', _money(okhra)])
            rows.append(['الإجمالي', _money(sum(bands.values()) + okhra)])
            return _export_response(fmt, 'تقرير المصروفات', subtitle, ['البند', 'الإجمالي'], rows, 'expenses-report')

        if report_kind == 'employees':
            rows = []
            for employee in get_weekly_employees_report(company_id):
                data = employee['data']
                rows.append([
                    employee['name'],
                    _money(data.get('salary', 0)),
                    data.get('weeks', 0),
                    _money(data.get('total_salary_due', 0)),
                    _money(data.get('advances', 0)),
                    _money(data.get('deductions', 0)),
                    _money(data.get('bonuses', 0)),
                    _money(data.get('total_paid', 0)),
                    _money(data.get('net', 0)),
                ])
            return _export_response(fmt, 'تقرير المرتبات الأسبوعي', company_name, ['الموظف', 'المرتب', 'أسابيع', 'المستحق', 'سلف', 'خصم', 'مكافآت', 'تم صرفه', 'الصافي'], rows, 'employees-weekly-report')

        if report_kind == 'daily':
            selected_date = date_from
            records, total_in, total_out = get_daily_khazna_report(selected_date, company_id)
            rows = [[r['type'], _money(r['amount']), r.get('description') or '-'] for r in records]
            rows.extend([
                ['إجمالي الدخل', _money(total_in), ''],
                ['إجمالي الصرف', _money(total_out), ''],
                ['الصافي', _money(total_in - total_out), ''],
            ])
            return _export_response(fmt, f'التقرير اليومي {selected_date}', company_name, ['النوع', 'المبلغ', 'الوصف'], rows, f'daily-report-{selected_date}')

        return jsonify({'error': 'تقرير غير معروف'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/person/<person_kind>/<fmt>')
@login_required
def export_person(person_kind, fmt):
    company_id = session['company_id']
    date_from, date_to = _get_date_range(30)
    name = request.args.get('name', '').strip()
    person_type, label = _person_type_from_kind(person_kind)
    if not name or not person_type:
        return jsonify({'error': 'بيانات غير صحيحة'}), 400

    try:
        transactions = get_person_transactions_range(name, person_type, date_from, date_to, company_id)
        dues, payments, net = _transaction_totals(transactions)
        current_balance = get_person_balance(person_type, name, company_id)
        rows = [[t['date'], t['type'], _money(t['amount'])] for t in transactions]
        rows.extend([
            ['الإجمالي المستحق في الفترة', '', _money(dues)],
            ['إجمالي المدفوع/الخصم في الفترة', '', _money(payments)],
            ['صافي حركات الفترة', '', _money(net)],
            ['الرصيد الحالي', '', _money(current_balance)],
        ])
        subtitle = f"{session.get('company_name', 'الشركة')} | من {date_from} إلى {date_to}"
        filename = f"{label}-{name}-{date_from}-{date_to}"
        return _export_response(fmt, f'كشف تفصيلي {label}: {name}', subtitle, ['التاريخ', 'نوع الحركة', 'المبلغ'], rows, filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

