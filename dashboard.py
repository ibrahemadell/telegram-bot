from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from database import (
    get_balance, get_clients_total, get_suppliers_total,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_weekly_employees_report, get_daily_khazna_report,
    get_db, authenticate_company
)
from datetime import date, timedelta
from functools import wraps
import os

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
        <label>اسم الشركة</label>
        <input type="text" name="company_name" required autocomplete="off">
      </div>
      <div class="input-group">
        <label>كلمة المرور</label>
        <input type="password" name="password" required>
      </div>
      <button type="submit" class="login-btn">دخول</button>
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
}
.logo{padding:0 20px 20px;border-bottom:1px solid var(--border);margin-bottom:12px;}
.logo h1{font-size:16px;font-weight:900;}
.logo span{font-size:11px;color:var(--text3);}
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
  display:none;position:fixed;top:12px;right:12px;z-index:300;
  background:var(--accent);border:none;color:white;
  width:40px;height:40px;border-radius:8px;font-size:18px;cursor:pointer;
}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:150;}

/* ===== Main ===== */
.main{margin-right:var(--sidebar-w);padding:24px 28px;min-height:100vh;}
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
  .sidebar{transform:translateX(100%);width:260px;}
  .sidebar.open{transform:translateX(0);}
  .mobile-toggle{display:flex;align-items:center;justify-content:center;}
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
    <div class="nav-item active" onclick="showPage('overview',this)"><span class="nav-icon">📊</span>نظرة عامة</div>
    <div class="nav-item" onclick="showPage('clients',this)"><span class="nav-icon">👥</span>العملاء</div>
    <div class="nav-item" onclick="showPage('suppliers',this)"><span class="nav-icon">🏭</span>الموردين</div>
    <div class="nav-item" onclick="showPage('employees',this)"><span class="nav-icon">👷</span>الموظفين</div>
    <div class="nav-item" onclick="showPage('expenses',this)"><span class="nav-icon">📋</span>المصروفات</div>
    <div class="nav-item" onclick="showPage('daily',this)"><span class="nav-icon">📅</span>التقرير اليومي</div>
  </nav>
  <div class="sidebar-footer">
    <a href="/logout" class="btn danger" style="width:100%; margin-top:8px;">تسجيل خروج</a>
  </div>
</aside>

<main class="main">

<!-- ===== نظرة عامة ===== -->
<div class="page active" id="page-overview">
  <div class="toolbar">
    <div>
      <div class="toolbar-title">📊 نظرة عامة</div>
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
    <div><div class="toolbar-title">👷 الموظفين</div></div>
    <input type="text" class="date-input" id="emp-search" placeholder="🔍 بحث باسم..." oninput="filterEmpTable()" style="min-width:160px;">
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
  </div>
  <div class="section">
    <div class="day-selector" id="day-selector"></div>
    <div id="daily-content"><div class="empty">اختار يوم</div></div>
  </div>
</div>

</main>

<script>
// ===== Globals =====
let clientsData = [], suppliersData = [], empData = [];
const fmt = n => Number(n).toLocaleString('ar-EG',{maximumFractionDigits:1}) + ' ج';
const today = () => new Date().toISOString().split('T')[0];
const daysAgo = d => { const dt = new Date(); dt.setDate(dt.getDate()-d); return dt.toISOString().split('T')[0]; };
const COLORS = ['blue','green','yellow','purple','orange','red','cyan'];

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
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
  let h = '<table><thead><tr><th>العميل</th><th>الحالة</th><th>الرصيد</th></tr></thead><tbody>';
  data.forEach(c => {
    let cls, txt;
    if(c.balance>0){cls='tag-debt';txt='عليه';totalDebt+=c.balance;}
    else if(c.balance<0){cls='tag-credit';txt='ليه عندنا';}
    else{cls='tag-zero';txt='صفر';}
    const ac = c.balance>0?'amt-neg':c.balance<0?'amt-pos':'amt-neu';
    h += `<tr><td><strong>${c.name}</strong></td><td><span class="tag ${cls}">${txt}</span></td><td class="${ac}">${fmt(Math.abs(c.balance))}</td></tr>`;
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
  let h = '<table><thead><tr><th>المورد</th><th>الحالة</th><th>الرصيد</th></tr></thead><tbody>';
  data.forEach(s => {
    let cls, txt;
    if(s.balance>0){cls='tag-debt';txt='ليه علينا';total+=s.balance;}
    else if(s.balance<0){cls='tag-credit';txt='دفعنا زيادة';}
    else{cls='tag-zero';txt='صفر';}
    const ac = s.balance>0?'amt-neg':'amt-neu';
    h += `<tr><td><strong>${s.name}</strong></td><td><span class="tag ${cls}">${txt}</span></td><td class="${ac}">${fmt(Math.abs(s.balance))}</td></tr>`;
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        password = request.form.get('password', '').strip()
        
        company = authenticate_company(company_name, password)
        if company:
            session['company_id'] = company['id']
            session['company_name'] = company['name']
            return redirect(url_for('index'))
        else:
            error = "اسم الشركة أو كلمة المرور غير صحيحة"
            
    return render_template_string(LOGIN_HTML, error=error)

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

if __name__ == '__main__':
    port = int(os.environ.get('DASHBOARD_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

