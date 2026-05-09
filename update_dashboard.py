import os

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Imports
imports_old = '''from database import (
    get_balance, get_clients_total, get_suppliers_total,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_weekly_employees_report, get_daily_khazna_report,
    get_db, authenticate_company
)'''
imports_new = '''from database import (
    get_balance, get_clients_total, get_suppliers_total,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_weekly_employees_report, get_daily_khazna_report,
    get_db, authenticate_company,
    add_client, add_supplier, add_employee, add_employee_transaction,
    add_masrof_edari, add_masrof_okhra, add_transaction, get_all_bands
)'''
content = content.replace(imports_old, imports_new)

# 2. Add API Endpoints
endpoints = '''
@app.route('/api/add_khazna', methods=['POST'])
@login_required
def api_add_khazna():
    data = request.json
    company_id = session['company_id']
    add_transaction(data['trans_type'], float(data['amount']), data['description'], company_id)
    return jsonify({"success": True})

@app.route('/api/add_client', methods=['POST'])
@login_required
def api_add_client():
    data = request.json
    company_id = session['company_id']
    add_client(data['name'], float(data.get('amount', 0)), data['trans_type'], company_id)
    return jsonify({"success": True})

@app.route('/api/add_supplier', methods=['POST'])
@login_required
def api_add_supplier():
    data = request.json
    company_id = session['company_id']
    add_supplier(data['name'], float(data.get('amount', 0)), data['trans_type'], company_id)
    return jsonify({"success": True})

@app.route('/api/add_employee', methods=['POST'])
@login_required
def api_add_employee():
    data = request.json
    company_id = session['company_id']
    add_employee(data['name'], float(data['salary']), company_id)
    return jsonify({"success": True})

@app.route('/api/add_employee_tx', methods=['POST'])
@login_required
def api_add_employee_tx():
    data = request.json
    company_id = session['company_id']
    add_employee_transaction(data['name'], data['trans_type'], float(data['amount']), company_id, data.get('note', ''))
    return jsonify({"success": True})

@app.route('/api/add_expense_edari', methods=['POST'])
@login_required
def api_add_expense_edari():
    data = request.json
    company_id = session['company_id']
    add_masrof_edari(data['band'], float(data['amount']), company_id)
    return jsonify({"success": True})

@app.route('/api/add_expense_okhra', methods=['POST'])
@login_required
def api_add_expense_okhra():
    data = request.json
    company_id = session['company_id']
    add_masrof_okhra(float(data['amount']), data['note'], company_id)
    return jsonify({"success": True})

@app.route('/dashboard')
'''
content = content.replace("@app.route('/dashboard')", endpoints)


# 3. Add Modals CSS
css_old = '''/* ===== Scrollbar ===== */'''
css_new = '''/* ===== Modals ===== */
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

/* ===== Scrollbar ===== */'''
content = content.replace(css_old, css_new)


# 4. Add Buttons to Toolbars
content = content.replace(
    '<div class="toolbar-title">📊 نظرة عامة</div>',
    '<div class="toolbar-title" style="margin-left:10px;">📊 نظرة عامة</div><div class="btn-group" style="margin-right:auto;"><button class="btn" style="background:var(--green);color:white;border:none;" onclick="openModal(\'modal-khazna-in\')">💰 دخل</button><button class="btn" style="background:var(--red);color:white;border:none;" onclick="openModal(\'modal-khazna-out\')">💸 صرف</button></div>'
)

content = content.replace(
    '<div class="toolbar-title">👥 العملاء</div>',
    '<div class="toolbar-title">👥 العملاء</div><button class="btn primary" style="margin-right:auto" onclick="openModal(\'modal-client\')">➕ تسجيل / إضافة</button>'
)

content = content.replace(
    '<div class="toolbar-title">🏭 الموردين</div>',
    '<div class="toolbar-title">🏭 الموردين</div><button class="btn primary" style="margin-right:auto" onclick="openModal(\'modal-supplier\')">➕ تسجيل / إضافة</button>'
)

content = content.replace(
    '<div class="toolbar-title">👷 الموظفين</div>',
    '<div class="toolbar-title">👷 الموظفين</div><button class="btn primary" style="margin-right:auto" onclick="openModal(\'modal-emp\')">➕ موظف</button><button class="btn" style="background:var(--green);color:white;border:none;margin-right:8px;" onclick="openModal(\'modal-emp-tx\')">💵 معاملة</button>'
)

content = content.replace(
    '<div class="toolbar-title">📋 المصروفات</div>',
    '<div class="toolbar-title">📋 المصروفات</div><button class="btn primary" style="margin-right:auto" onclick="openModal(\'modal-exp-edari\')">➕ إداري</button><button class="btn" style="background:var(--orange);color:white;border:none;margin-right:8px;" onclick="openModal(\'modal-exp-okhra\')">➕ آخر</button>'
)


# 5. Add Modals HTML
modals_html = '''
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
    <div class="modal-title">👥 عميل جديد / حركة</div>
    <form onsubmit="submitForm(event, '/api/add_client', {name:this.cname.value, amount:this.amount.value||0, trans_type:this.type.value})">
      <div class="form-group"><label>اسم العميل</label><input type="text" name="cname" class="form-input" required list="clients-list" autocomplete="off"></div>
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
    <div class="modal-title">🏭 مورد جديد / حركة</div>
    <form onsubmit="submitForm(event, '/api/add_supplier', {name:this.sname.value, amount:this.amount.value||0, trans_type:this.type.value})">
      <div class="form-group"><label>اسم المورد</label><input type="text" name="sname" class="form-input" required list="suppliers-list" autocomplete="off"></div>
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

<datalist id="clients-list"></datalist>
<datalist id="suppliers-list"></datalist>
<datalist id="employees-list"></datalist>
<datalist id="bands-list"></datalist>

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
    <form onsubmit="submitForm(event, '/api/add_employee_tx', {name:this.ename.value, trans_type:this.type.value, amount:this.amount.value, note:this.note.value})">
      <div class="form-group"><label>اسم الموظف</label><input type="text" name="ename" class="form-input" required list="employees-list" autocomplete="off"></div>
      <div class="form-group"><label>المبلغ</label><input type="number" name="amount" class="form-input" required step="any" min="0"></div>
      <div class="form-group">
        <label>نوع الحركة</label>
        <select name="type" class="form-select">
          <option value="صرف راتب">صرف راتب</option>
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
      <div class="form-group"><label>بند المصروف</label><input type="text" name="band" class="form-input" required list="bands-list" autocomplete="off"></div>
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
'''
content = content.replace('</main>', modals_html)

# 6. Add JS Logic
js_old = '''// ===== Globals ====='''
js_new = '''// ===== Modals Logic =====
function openModal(id) { document.getElementById(id).classList.add('active'); }
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
function updateDatalist(id, list) {
  const dl = document.getElementById(id);
  if(!dl) return;
  dl.innerHTML = list.map(item => `<option value="${item}">`).join('');
}

// ===== Globals ====='''
content = content.replace(js_old, js_new)

# 7. Update Datalists on data load
content = content.replace(
    'clientsData = data;\n  renderClientsTable(data);',
    'clientsData = data;\n  renderClientsTable(data);\n  updateDatalist("clients-list", data.map(c=>c.name));'
)
content = content.replace(
    'suppliersData = data;\n  renderSuppliersTable(data);',
    'suppliersData = data;\n  renderSuppliersTable(data);\n  updateDatalist("suppliers-list", data.map(s=>s.name));'
)
content = content.replace(
    'empData = data;\n  renderEmpTable(data);',
    'empData = data;\n  renderEmpTable(data);\n  updateDatalist("employees-list", data.map(e=>e.name));'
)
content = content.replace(
    'renderExpenses(data);\n}',
    'renderExpenses(data);\n  updateDatalist("bands-list", Object.keys(data.bands||{}));\n}'
)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Dashboard updated successfully!")
