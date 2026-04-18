from flask import Flask, jsonify, render_template_string
from database import (
    get_balance, get_clients_total, get_suppliers_total,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_employee_names, get_employee_balance,
    get_monthly_khazna_report, get_monthly_masrof_report,
    get_daily_khazna_report, get_weekly_employees_report,
    get_db
)
from datetime import date, timedelta
import os

app = Flask(__name__)

# ============ HTML Template ============

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>لوحة التحكم المالية</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #3b82f6;
    --accent2: #06b6d4;
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;
    --purple: #8b5cf6;
    --text: #f1f5f9;
    --text2: #94a3b8;
    --text3: #475569;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Cairo', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* Sidebar */
  .sidebar {
    position: fixed; right:0; top:0;
    width: 240px; height: 100vh;
    background: var(--surface);
    border-left: 1px solid var(--border);
    padding: 24px 0;
    z-index: 100;
    display: flex; flex-direction: column;
  }
  .logo {
    padding: 0 24px 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
  }
  .logo h1 { font-size: 18px; font-weight: 900; color: var(--text); }
  .logo span { font-size: 12px; color: var(--text3); }
  .nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 11px 24px;
    cursor: pointer;
    color: var(--text2);
    font-size: 14px; font-weight: 600;
    transition: all 0.2s;
    border-right: 3px solid transparent;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); }
  .nav-item.active { color: var(--accent); border-right-color: var(--accent); background: rgba(59,130,246,0.08); }
  .nav-icon { font-size: 18px; width: 22px; text-align: center; }

  /* Main */
  .main {
    margin-right: 240px;
    padding: 28px 32px;
    min-height: 100vh;
  }
  .page { display: none; }
  .page.active { display: block; }

  /* Header */
  .page-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 28px;
  }
  .page-title { font-size: 22px; font-weight: 900; }
  .page-sub { font-size: 13px; color: var(--text3); margin-top: 2px; }
  .refresh-btn {
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text2); padding: 8px 16px; border-radius: 8px;
    cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13px;
    transition: all 0.2s;
  }
  .refresh-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* Cards */
  .cards-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 24px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--accent); }
  .card::before {
    content: '';
    position: absolute; top:0; right:0;
    width: 3px; height: 100%;
  }
  .card.blue::before { background: var(--accent); }
  .card.green::before { background: var(--green); }
  .card.red::before { background: var(--red); }
  .card.yellow::before { background: var(--yellow); }
  .card.purple::before { background: var(--purple); }
  .card.cyan::before { background: var(--accent2); }
  .card-label { font-size: 12px; color: var(--text3); font-weight: 600; margin-bottom: 8px; }
  .card-value { font-size: 26px; font-weight: 900; margin-bottom: 4px; }
  .card-value.green { color: var(--green); }
  .card-value.red { color: var(--red); }
  .card-value.blue { color: var(--accent); }
  .card-value.yellow { color: var(--yellow); }
  .card-value.purple { color: var(--purple); }
  .card-sub { font-size: 12px; color: var(--text3); }
  .card-icon {
    position: absolute; left: 16px; top: 50%;
    transform: translateY(-50%);
    font-size: 32px; opacity: 0.1;
  }

  /* Tables */
  .section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 20px;
    overflow: hidden;
  }
  .section-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }
  .section-title { font-size: 14px; font-weight: 700; }
  .section-badge {
    font-size: 11px; padding: 3px 8px;
    border-radius: 20px; font-weight: 700;
  }
  .badge-blue { background: rgba(59,130,246,0.15); color: var(--accent); }
  .badge-green { background: rgba(16,185,129,0.15); color: var(--green); }
  .badge-red { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge-yellow { background: rgba(245,158,11,0.15); color: var(--yellow); }

  table { width: 100%; border-collapse: collapse; }
  th {
    padding: 10px 20px; text-align: right;
    font-size: 11px; font-weight: 700;
    color: var(--text3); text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
  }
  td {
    padding: 12px 20px;
    font-size: 13px;
    border-bottom: 1px solid rgba(30,45,69,0.5);
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(59,130,246,0.04); }

  .amount-positive { color: var(--green); font-weight: 700; }
  .amount-negative { color: var(--red); font-weight: 700; }
  .amount-neutral { color: var(--text2); }

  .status-badge {
    display: inline-block;
    padding: 3px 8px; border-radius: 20px;
    font-size: 11px; font-weight: 700;
  }
  .status-debt { background: rgba(239,68,68,0.15); color: var(--red); }
  .status-credit { background: rgba(16,185,129,0.15); color: var(--green); }
  .status-zero { background: rgba(148,163,184,0.15); color: var(--text3); }

  /* Two column */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .three-col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }

  /* Chart bars */
  .bar-chart { padding: 16px 20px; }
  .bar-row {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 10px;
  }
  .bar-label { font-size: 12px; color: var(--text2); width: 100px; text-align: right; flex-shrink:0; }
  .bar-track {
    flex: 1; height: 8px;
    background: var(--surface2); border-radius: 4px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%; border-radius: 4px;
    transition: width 1s ease;
  }
  .bar-fill.green { background: linear-gradient(90deg, var(--green), #34d399); }
  .bar-fill.red { background: linear-gradient(90deg, var(--red), #f87171); }
  .bar-fill.blue { background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .bar-fill.yellow { background: linear-gradient(90deg, var(--yellow), #fcd34d); }
  .bar-fill.purple { background: linear-gradient(90deg, var(--purple), #a78bfa); }
  .bar-amount { font-size: 12px; color: var(--text2); width: 90px; flex-shrink:0; }

  /* Loading */
  .loading {
    text-align: center; padding: 40px;
    color: var(--text3); font-size: 14px;
  }
  .loading::after {
    content: ''; display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Day selector */
  .day-selector {
    display: flex; gap: 8px; flex-wrap: wrap;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }
  .day-btn {
    padding: 6px 14px; border-radius: 20px;
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text2); font-family: 'Cairo', sans-serif;
    font-size: 12px; cursor: pointer; transition: all 0.2s;
  }
  .day-btn:hover, .day-btn.active {
    background: var(--accent); border-color: var(--accent);
    color: white;
  }

  /* Empty state */
  .empty {
    text-align: center; padding: 32px;
    color: var(--text3); font-size: 13px;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  @media (max-width: 1200px) { .cards-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 900px) { .two-col, .three-col { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<!-- Sidebar -->
<aside class="sidebar">
  <div class="logo">
    <h1>💼 المالية</h1>
    <span>لوحة التحكم</span>
  </div>
  <nav>
    <div class="nav-item active" onclick="showPage('overview')">
      <span class="nav-icon">📊</span> نظرة عامة
    </div>
    <div class="nav-item" onclick="showPage('clients')">
      <span class="nav-icon">👥</span> العملاء
    </div>
    <div class="nav-item" onclick="showPage('suppliers')">
      <span class="nav-icon">🏭</span> الموردين
    </div>
    <div class="nav-item" onclick="showPage('employees')">
      <span class="nav-icon">👷</span> الموظفين
    </div>
    <div class="nav-item" onclick="showPage('expenses')">
      <span class="nav-icon">📋</span> المصروفات
    </div>
    <div class="nav-item" onclick="showPage('daily')">
      <span class="nav-icon">📅</span> التقرير اليومي
    </div>
  </nav>
</aside>

<!-- Main Content -->
<main class="main">

  <!-- ===== نظرة عامة ===== -->
  <div class="page active" id="page-overview">
    <div class="page-header">
      <div>
        <div class="page-title">نظرة عامة</div>
        <div class="page-sub" id="today-date"></div>
      </div>
      <button class="refresh-btn" onclick="loadAll()">🔄 تحديث</button>
    </div>

    <div class="cards-grid" id="overview-cards">
      <div class="loading">جاري التحميل</div>
    </div>

    <div class="two-col">
      <div class="section">
        <div class="section-header">
          <span class="section-title">📈 دخل وصرف الشهر</span>
          <span class="section-badge badge-blue" id="month-label"></span>
        </div>
        <div class="bar-chart" id="monthly-chart">
          <div class="loading">جاري التحميل</div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <span class="section-title">⚡ آخر حركات اليوم</span>
          <span class="section-badge badge-green" id="today-count"></span>
        </div>
        <div id="today-transactions">
          <div class="loading">جاري التحميل</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== العملاء ===== -->
  <div class="page" id="page-clients">
    <div class="page-header">
      <div>
        <div class="page-title">العملاء</div>
        <div class="page-sub">أرصدة وحركات العملاء</div>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <span class="section-title">👥 كل العملاء</span>
        <span class="section-badge badge-blue" id="clients-total-badge"></span>
      </div>
      <div id="clients-table"><div class="loading">جاري التحميل</div></div>
    </div>
  </div>

  <!-- ===== الموردين ===== -->
  <div class="page" id="page-suppliers">
    <div class="page-header">
      <div>
        <div class="page-title">الموردين</div>
        <div class="page-sub">المديونيات والمدفوعات</div>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <span class="section-title">🏭 كل الموردين</span>
        <span class="section-badge badge-red" id="suppliers-total-badge"></span>
      </div>
      <div id="suppliers-table"><div class="loading">جاري التحميل</div></div>
    </div>
  </div>

  <!-- ===== الموظفين ===== -->
  <div class="page" id="page-employees">
    <div class="page-header">
      <div>
        <div class="page-title">الموظفين</div>
        <div class="page-sub">المرتبات والصافي المستحق</div>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <span class="section-title">👷 تقرير الموظفين الأسبوعي</span>
      </div>
      <div id="employees-table"><div class="loading">جاري التحميل</div></div>
    </div>
  </div>

  <!-- ===== المصروفات ===== -->
  <div class="page" id="page-expenses">
    <div class="page-header">
      <div>
        <div class="page-title">المصروفات</div>
        <div class="page-sub">تقرير المصروفات الشهري</div>
      </div>
    </div>
    <div class="two-col">
      <div class="section">
        <div class="section-header">
          <span class="section-title">📌 المصروفات الإدارية</span>
        </div>
        <div class="bar-chart" id="expenses-bands-chart">
          <div class="loading">جاري التحميل</div>
        </div>
      </div>
      <div class="section">
        <div class="section-header">
          <span class="section-title">📊 ملخص المصروفات</span>
        </div>
        <div id="expenses-summary"><div class="loading">جاري التحميل</div></div>
      </div>
    </div>
  </div>

  <!-- ===== التقرير اليومي ===== -->
  <div class="page" id="page-daily">
    <div class="page-header">
      <div>
        <div class="page-title">التقرير اليومي</div>
        <div class="page-sub">حركات الخزنة اليومية</div>
      </div>
    </div>
    <div class="section">
      <div class="day-selector" id="day-selector"></div>
      <div id="daily-content"><div class="empty">اختار يوم لعرض التقرير</div></div>
    </div>
  </div>

</main>

<script>
const DAYS_AR = ['السبت','الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة'];

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  loadPage(name);
}

async function api(endpoint) {
  const res = await fetch('/api/' + endpoint);
  return res.json();
}

function fmt(n) {
  return Number(n).toLocaleString('ar-EG', {maximumFractionDigits:1}) + ' ج';
}

// ===== Overview =====
async function loadOverview() {
  const today = new Date();
  document.getElementById('today-date').textContent =
    today.toLocaleDateString('ar-EG', {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  document.getElementById('month-label').textContent =
    today.toLocaleDateString('ar-EG', {year:'numeric', month:'long'});

  const data = await api('overview');

  // Cards
  const balanceColor = data.balance >= 0 ? 'green' : 'red';
  document.getElementById('overview-cards').innerHTML = `
    <div class="card ${balanceColor}">
      <div class="card-label">رصيد الخزنة</div>
      <div class="card-value ${balanceColor}">${fmt(data.balance)}</div>
      <div class="card-sub">الرصيد الكلي</div>
      <span class="card-icon">🏦</span>
    </div>
    <div class="card blue">
      <div class="card-label">دخل الشهر</div>
      <div class="card-value blue">${fmt(data.month_in)}</div>
      <div class="card-sub">إجمالي الواردات</div>
      <span class="card-icon">📈</span>
    </div>
    <div class="card red">
      <div class="card-label">صرف الشهر</div>
      <div class="card-value red">${fmt(data.month_out)}</div>
      <div class="card-sub">إجمالي المصروفات</div>
      <span class="card-icon">📉</span>
    </div>
    <div class="card yellow">
      <div class="card-label">مديونيات الموردين</div>
      <div class="card-value yellow">${fmt(data.suppliers_debt)}</div>
      <div class="card-sub">إجمالي ما علينا</div>
      <span class="card-icon">🏭</span>
    </div>
    <div class="card green">
      <div class="card-label">فلوس العملاء</div>
      <div class="card-value green">${fmt(data.clients_credit)}</div>
      <div class="card-sub">إجمالي ما لنا</div>
      <span class="card-icon">👥</span>
    </div>
    <div class="card purple">
      <div class="card-label">مرتبات مستحقة</div>
      <div class="card-value purple">${fmt(data.salary_due)}</div>
      <div class="card-sub">إجمالي الموظفين</div>
      <span class="card-icon">👷</span>
    </div>
    <div class="card cyan">
      <div class="card-label">صافي الشهر</div>
      <div class="card-value ${data.month_net >= 0 ? 'green':'red'}">${fmt(data.month_net)}</div>
      <div class="card-sub">${data.month_net >= 0 ? 'ربح' : 'خسارة'}</div>
      <span class="card-icon">💹</span>
    </div>
    <div class="card blue">
      <div class="card-label">حركات اليوم</div>
      <div class="card-value blue">${data.today_count}</div>
      <div class="card-sub">عدد المعاملات</div>
      <span class="card-icon">⚡</span>
    </div>
  `;

  // Monthly chart
  const maxVal = Math.max(data.month_in, data.month_out, 1);
  document.getElementById('monthly-chart').innerHTML = `
    <div class="bar-row">
      <span class="bar-label">الدخل</span>
      <div class="bar-track"><div class="bar-fill green" style="width:${(data.month_in/maxVal)*100}%"></div></div>
      <span class="bar-amount">${fmt(data.month_in)}</span>
    </div>
    <div class="bar-row">
      <span class="bar-label">الصرف</span>
      <div class="bar-track"><div class="bar-fill red" style="width:${(data.month_out/maxVal)*100}%"></div></div>
      <span class="bar-amount">${fmt(data.month_out)}</span>
    </div>
    <div class="bar-row">
      <span class="bar-label">الصافي</span>
      <div class="bar-track"><div class="bar-fill ${data.month_net>=0?'blue':'red'}" style="width:${Math.min(Math.abs(data.month_net)/maxVal*100,100)}%"></div></div>
      <span class="bar-amount">${fmt(data.month_net)}</span>
    </div>
  `;

  // Today transactions
  document.getElementById('today-count').textContent = data.today_count + ' حركة';
  if (data.today_records.length === 0) {
    document.getElementById('today-transactions').innerHTML = '<div class="empty">مفيش حركات النهارده</div>';
  } else {
    let html = '<table><thead><tr><th>النوع</th><th>المبلغ</th><th>الوصف</th></tr></thead><tbody>';
    data.today_records.forEach(r => {
      const cls = r.type === 'دخل' ? 'amount-positive' : 'amount-negative';
      const icon = r.type === 'دخل' ? '💚' : '🔴';
      html += `<tr><td>${icon} ${r.type}</td><td class="${cls}">${fmt(r.amount)}</td><td>${r.description||'-'}</td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('today-transactions').innerHTML = html;
  }
}

// ===== Clients =====
async function loadClients() {
  const data = await api('clients');
  let total_debt = 0;
  if (data.length === 0) {
    document.getElementById('clients-table').innerHTML = '<div class="empty">مفيش عملاء</div>';
    return;
  }
  let html = '<table><thead><tr><th>العميل</th><th>الحالة</th><th>المبلغ</th></tr></thead><tbody>';
  data.forEach(c => {
    let statusClass, statusText;
    if (c.balance > 0) { statusClass='status-debt'; statusText='عليه'; total_debt+=c.balance; }
    else if (c.balance < 0) { statusClass='status-credit'; statusText='ليه عندنا'; }
    else { statusClass='status-zero'; statusText='صفر'; }
    const amtClass = c.balance > 0 ? 'amount-negative' : c.balance < 0 ? 'amount-positive' : 'amount-neutral';
    html += `<tr><td>${c.name}</td><td><span class="status-badge ${statusClass}">${statusText}</span></td><td class="${amtClass}">${fmt(Math.abs(c.balance))}</td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('clients-table').innerHTML = html;
  document.getElementById('clients-total-badge').textContent = `إجمالي الديون: ${fmt(total_debt)}`;
}

// ===== Suppliers =====
async function loadSuppliers() {
  const data = await api('suppliers');
  let total = 0;
  if (data.length === 0) {
    document.getElementById('suppliers-table').innerHTML = '<div class="empty">مفيش موردين</div>';
    return;
  }
  let html = '<table><thead><tr><th>المورد</th><th>الحالة</th><th>المبلغ</th></tr></thead><tbody>';
  data.forEach(s => {
    let statusClass, statusText;
    if (s.balance > 0) { statusClass='status-debt'; statusText='ليه عندنا'; total+=s.balance; }
    else if (s.balance < 0) { statusClass='status-credit'; statusText='دفعنا زيادة'; }
    else { statusClass='status-zero'; statusText='صفر'; }
    const amtClass = s.balance > 0 ? 'amount-negative' : 'amount-neutral';
    html += `<tr><td>${s.name}</td><td><span class="status-badge ${statusClass}">${statusText}</span></td><td class="${amtClass}">${fmt(Math.abs(s.balance))}</td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('suppliers-table').innerHTML = html;
  document.getElementById('suppliers-total-badge').textContent = `إجمالي المديونيات: ${fmt(total)}`;
}

// ===== Employees =====
async function loadEmployees() {
  const data = await api('employees');
  if (data.length === 0) {
    document.getElementById('employees-table').innerHTML = '<div class="empty">مفيش موظفين</div>';
    return;
  }
  let html = '<table><thead><tr><th>الموظف</th><th>المرتب الأسبوعي</th><th>أسابيع</th><th>المستحق</th><th>سلف</th><th>خصم</th><th>مكافآت</th><th>تم صرف</th><th>الصافي</th></tr></thead><tbody>';
  data.forEach(e => {
    const d = e.data;
    const netClass = d.net > 0 ? 'amount-negative' : d.net < 0 ? 'amount-positive' : 'amount-neutral';
    html += `<tr>
      <td><strong>${e.name}</strong></td>
      <td>${fmt(d.salary)}</td>
      <td>${d.weeks}</td>
      <td class="amount-negative">${fmt(d.total_salary_due)}</td>
      <td>${fmt(d.advances)}</td>
      <td>${fmt(d.deductions)}</td>
      <td class="amount-positive">${fmt(d.bonuses)}</td>
      <td>${fmt(d.total_paid)}</td>
      <td class="${netClass}"><strong>${fmt(d.net)}</strong></td>
    </tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('employees-table').innerHTML = html;
}

// ===== Expenses =====
async function loadExpenses() {
  const data = await api('expenses');
  const maxVal = Math.max(...Object.values(data.bands), data.okhra, 1);

  // Bands chart
  let chartHtml = '';
  const colors = ['blue','green','yellow','purple','red','cyan'];
  Object.entries(data.bands).forEach(([band, amount], i) => {
    const color = colors[i % colors.length];
    chartHtml += `<div class="bar-row">
      <span class="bar-label">${band}</span>
      <div class="bar-track"><div class="bar-fill ${color}" style="width:${(amount/maxVal)*100}%"></div></div>
      <span class="bar-amount">${fmt(amount)}</span>
    </div>`;
  });
  if (data.okhra > 0) {
    chartHtml += `<div class="bar-row">
      <span class="bar-label">أخرى</span>
      <div class="bar-track"><div class="bar-fill red" style="width:${(data.okhra/maxVal)*100}%"></div></div>
      <span class="bar-amount">${fmt(data.okhra)}</span>
    </div>`;
  }
  document.getElementById('expenses-bands-chart').innerHTML = chartHtml || '<div class="empty">مفيش مصروفات</div>';

  // Summary
  const total = data.total_bands + data.okhra;
  document.getElementById('expenses-summary').innerHTML = `
    <table>
      <tr><td>مصروفات إدارية</td><td class="amount-negative">${fmt(data.total_bands)}</td></tr>
      <tr><td>مصروفات أخرى</td><td class="amount-negative">${fmt(data.okhra)}</td></tr>
      <tr><td><strong>الإجمالي</strong></td><td class="amount-negative"><strong>${fmt(total)}</strong></td></tr>
    </table>
  `;
}

// ===== Daily =====
function loadDailySelector() {
  const today = new Date();
  const dayOfWeek = today.getDay();
  // السبت = 6
  const daysFromSaturday = (dayOfWeek + 1) % 7;
  const saturday = new Date(today);
  saturday.setDate(today.getDate() - daysFromSaturday);

  let html = '';
  for (let i = 0; i < 7; i++) {
    const d = new Date(saturday);
    d.setDate(saturday.getDate() + i);
    const dateStr = d.toISOString().split('T')[0];
    const dayName = DAYS_AR[i];
    const isToday = dateStr === today.toISOString().split('T')[0];
    html += `<button class="day-btn ${isToday?'active':''}" onclick="loadDailyReport('${dateStr}', this)">${dayName}<br><small>${d.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})}</small></button>`;
  }
  document.getElementById('day-selector').innerHTML = html;

  // Load today by default
  const todayStr = today.toISOString().split('T')[0];
  loadDailyReport(todayStr, null);
}

async function loadDailyReport(dateStr, btn) {
  if (btn) {
    document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  document.getElementById('daily-content').innerHTML = '<div class="loading">جاري التحميل</div>';
  const data = await api('daily/' + dateStr);

  if (data.records.length === 0) {
    document.getElementById('daily-content').innerHTML = '<div class="empty">مفيش حركات في هذا اليوم</div>';
    return;
  }

  let html = `
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:16px 20px;border-bottom:1px solid var(--border)">
      <div style="text-align:center">
        <div style="font-size:11px;color:var(--text3);margin-bottom:4px">إجمالي الدخل</div>
        <div style="font-size:20px;font-weight:900;color:var(--green)">${fmt(data.total_in)}</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:11px;color:var(--text3);margin-bottom:4px">إجمالي الصرف</div>
        <div style="font-size:20px;font-weight:900;color:var(--red)">${fmt(data.total_out)}</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:11px;color:var(--text3);margin-bottom:4px">الصافي</div>
        <div style="font-size:20px;font-weight:900;color:${data.net>=0?'var(--green)':'var(--red)'}">${fmt(data.net)}</div>
      </div>
    </div>
    <table><thead><tr><th>النوع</th><th>المبلغ</th><th>الوصف</th></tr></thead><tbody>
  `;
  data.records.forEach(r => {
    const cls = r.type === 'دخل' ? 'amount-positive' : 'amount-negative';
    const icon = r.type === 'دخل' ? '💚' : '🔴';
    html += `<tr><td>${icon} ${r.type}</td><td class="${cls}">${fmt(r.amount)}</td><td>${r.description||'-'}</td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('daily-content').innerHTML = html;
}

function loadPage(name) {
  if (name === 'overview') loadOverview();
  else if (name === 'clients') loadClients();
  else if (name === 'suppliers') loadSuppliers();
  else if (name === 'employees') loadEmployees();
  else if (name === 'expenses') loadExpenses();
  else if (name === 'daily') loadDailySelector();
}

function loadAll() { loadOverview(); }

// Init
loadOverview();
</script>
</body>
</html>'''

# ============ API Routes ============

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/overview')
def api_overview():
    try:
        balance = get_balance()
        month_in, month_out = get_monthly_khazna_report()
        month_net = month_in - month_out
        _, clients_details = get_clients_total()
        clients_credit = sum(
            get_person_balance("عميل", name.replace("  • ", "").split(":")[0].strip())
            for name in clients_details
        ) if clients_details else 0

        _, suppliers_details = get_suppliers_total()
        suppliers_debt = 0
        for name in get_all_suppliers():
            b = get_person_balance("مورد", name)
            if b > 0:
                suppliers_debt += b

        # Salary due
        salary_due = 0
        for emp in get_weekly_employees_report():
            if emp['data']['net'] > 0:
                salary_due += emp['data']['net']

        # Today
        today_str = str(date.today())
        today_records, today_in, today_out = get_daily_khazna_report(today_str)

        return jsonify({
            'balance': balance,
            'month_in': month_in,
            'month_out': month_out,
            'month_net': month_net,
            'clients_credit': clients_credit,
            'suppliers_debt': suppliers_debt,
            'salary_due': salary_due,
            'today_count': len(today_records),
            'today_records': today_records
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients')
def api_clients():
    try:
        result = []
        for name in get_all_clients():
            b = get_person_balance("عميل", name)
            result.append({'name': name, 'balance': b})
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers')
def api_suppliers():
    try:
        result = []
        for name in get_all_suppliers():
            b = get_person_balance("مورد", name)
            result.append({'name': name, 'balance': b})
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees')
def api_employees():
    try:
        return jsonify(get_weekly_employees_report())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/expenses')
def api_expenses():
    try:
        bands, okhra = get_monthly_masrof_report()
        total_bands = sum(bands.values()) if bands else 0
        return jsonify({
            'bands': bands,
            'okhra': okhra,
            'total_bands': total_bands
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily/<selected_date>')
def api_daily(selected_date):
    try:
        records, total_in, total_out = get_daily_khazna_report(selected_date)
        return jsonify({
            'records': records,
            'total_in': total_in,
            'total_out': total_out,
            'net': total_in - total_out
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('DASHBOARD_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
