"""
Vercel Serverless Entry Point
==============================
- /          : Dashboard
- /api/*     : API endpoints
- /webhook   : Telegram Webhook receiver
- /set_webhook : لضبط الـ webhook (استدعه مرة واحدة بعد النشر)
"""

import sys
import os

# أضف المجلد الأب للـ path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import threading
from datetime import date, timedelta

from flask import Flask, request, jsonify, render_template_string
from telegram import Update
from telegram.ext import PicklePersistence
from telegram.ext import ApplicationBuilder

from database import (
    init_db, get_balance,
    get_all_clients, get_all_suppliers, get_person_balance,
    get_weekly_employees_report, get_daily_khazna_report,
    get_db
)

# استورد handlers البوت من app.py
from app import conv_handler, error_callback

TOKEN = os.environ.get("TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

if not TOKEN:
    raise ValueError("TOKEN environment variable is required")

# تهيئة قاعدة البيانات
init_db()

# ============ Flask App ============
app = Flask(__name__)

# ============ Simple Cache ============
_cache = {}
_cache_ttl = {}
CACHE_SECONDS = 60

def cache_get(key):
    if key in _cache and time.time() - _cache_ttl.get(key, 0) < CACHE_SECONDS:
        return _cache[key]
    return None

def cache_set(key, value):
    _cache[key] = value
    _cache_ttl[key] = time.time()

def cache_clear():
    _cache.clear()
    _cache_ttl.clear()

# ============ DB Helpers ============
def daysAgo(n):
    return str(date.today() - timedelta(days=n))

def _get_date_range(default_days=30):
    date_from = request.args.get('from', daysAgo(default_days))
    date_to = request.args.get('to', str(date.today()))
    return date_from, date_to

def get_khazna_range(date_from, date_to):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT date, type, amount, description
        FROM khazna
        WHERE date >= %s AND date <= %s
        ORDER BY created_at DESC
    """, (date_from, date_to))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    total_in = sum(r['amount'] for r in rows if r['type'] == 'دخل')
    total_out = sum(r['amount'] for r in rows if r['type'] == 'صرف')
    return rows, total_in, total_out

def get_masrof_range(date_from, date_to):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT band, SUM(amount) as total
        FROM masrof_edari WHERE date >= %s AND date <= %s
        GROUP BY band
    """, (date_from, date_to))
    bands = {r['band']: float(r['total']) for r in c.fetchall()}
    c.execute("SELECT SUM(amount) as total FROM masrof_okhra WHERE date >= %s AND date <= %s", (date_from, date_to))
    row = c.fetchone()
    okhra = float(row['total']) if row and row['total'] else 0
    conn.close()
    return bands, okhra

# ============ Async Helper ============
def run_async(coro):
    """تشغيل async coroutine من بيئة sync بأمان في Vercel threads"""
    result_holder = [None]
    exception_holder = [None]

    def runner():
        try:
            result_holder[0] = asyncio.run(coro)
        except Exception as e:
            exception_holder[0] = e

    t = threading.Thread(target=runner)
    t.start()
    t.join()

    if exception_holder[0]:
        raise exception_holder[0]
    return result_holder[0]

# ============ Telegram App Builder ============
# مسار persistence للحفاظ على user_data بين الـ requests
PERSISTENCE_PATH = "/tmp/tg_persistence"

def get_telegram_app():
    """إنشاء telegram application جديد مع الـ handlers وحفظ الـ state"""
    persistence = PicklePersistence(filepath=PERSISTENCE_PATH)
    tg_app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    tg_app.add_handler(conv_handler)
    tg_app.add_error_handler(error_callback)
    return tg_app

# ============ Webhook Routes ============
@app.route('/webhook', methods=['POST'])
def webhook():
    """استقبال التحديثات من Telegram"""
    if WEBHOOK_SECRET:
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if secret != WEBHOOK_SECRET:
            return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json(force=True)

        async def process_update():
            tg_app = get_telegram_app()
            async with tg_app:
                update = Update.de_json(data, tg_app.bot)
                await tg_app.process_update(update)

        run_async(process_update())
        return jsonify({'ok': True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/set_webhook')
def set_webhook():
    """
    اضغط على هذا الرابط مرة واحدة بعد النشر لضبط الـ webhook.
    مثال: https://YOUR-APP.vercel.app/set_webhook?url=YOUR-APP.vercel.app
    """
    vercel_url = request.args.get('url') or os.environ.get('VERCEL_URL', '')
    if not vercel_url:
        return jsonify({
            'ok': False,
            'error': 'أضف ?url=your-app.vercel.app للرابط',
            'example': f'{request.host_url}set_webhook?url={request.host}'
        }), 400

    vercel_url = vercel_url.replace('https://', '').replace('http://', '').rstrip('/')
    webhook_url = f"https://{vercel_url}/webhook"

    try:
        async def do_set():
            tg_app = get_telegram_app()
            async with tg_app:
                result = await tg_app.bot.set_webhook(
                    url=webhook_url,
                    secret_token=WEBHOOK_SECRET if WEBHOOK_SECRET else None,
                    allowed_updates=list(Update.ALL_TYPES)
                )
                info = await tg_app.bot.get_webhook_info()
                return result, info

        result, info = run_async(do_set())
        return jsonify({
            'ok': result,
            'webhook_url': webhook_url,
            'current_webhook': info.url,
            'pending_updates': info.pending_update_count,
            'message': '✅ تم ضبط الـ webhook بنجاح!' if result else '❌ فشل الضبط'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/webhook_info')
def webhook_info():
    try:
        async def get_info():
            tg_app = get_telegram_app()
            async with tg_app:
                return await tg_app.bot.get_webhook_info()

        info = run_async(get_info())
        return jsonify({
            'url': info.url,
            'pending_update_count': info.pending_update_count,
            'last_error_message': info.last_error_message,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ Dashboard HTML ============
DASHBOARD_HTML = open(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard_template.html'),
    encoding='utf-8'
).read() if os.path.exists(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard_template.html')
) else None

# fallback: استورد من dashboard.py كـ string
if DASHBOARD_HTML is None:
    # استيراد آمن للـ HTML فقط
    import importlib.util
    _dashboard_spec = importlib.util.spec_from_file_location(
        "dashboard_module",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard.py')
    )
    _dashboard_mod = importlib.util.module_from_spec(_dashboard_spec)
    _dashboard_spec.loader.exec_module(_dashboard_mod)
    DASHBOARD_HTML = _dashboard_mod.DASHBOARD_HTML

# ============ Dashboard Routes ============
@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/cache/clear')
def clear_cache_route():
    cache_clear()
    return jsonify({'ok': True})

@app.route('/api/overview')
def api_overview():
    date_from, date_to = _get_date_range(7)
    cache_key = f'overview_{date_from}_{date_to}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    try:
        balance = get_balance()
        _, period_in, period_out = get_khazna_range(date_from, date_to)
        net = period_in - period_out
        suppliers_debt = sum(max(get_person_balance("مورد", n), 0) for n in get_all_suppliers())
        clients_credit = sum(max(get_person_balance("عميل", n), 0) for n in get_all_clients())
        salary_due = sum(max(e['data']['net'], 0) for e in get_weekly_employees_report())
        result = {
            'balance': balance, 'period_in': period_in, 'period_out': period_out,
            'net': net, 'suppliers_debt': suppliers_debt,
            'clients_credit': clients_credit, 'salary_due': salary_due,
        }
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients')
def api_clients():
    date_from, date_to = _get_date_range(3650)
    cache_key = f'clients_{date_from}_{date_to}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    try:
        result = [{'name': n, 'balance': get_person_balance("عميل", n)} for n in get_all_clients()]
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers')
def api_suppliers():
    date_from, date_to = _get_date_range(3650)
    cache_key = f'suppliers_{date_from}_{date_to}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    try:
        result = [{'name': n, 'balance': get_person_balance("مورد", n)} for n in get_all_suppliers()]
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees')
def api_employees():
    cached = cache_get('employees')
    if cached:
        return jsonify(cached)
    try:
        result = get_weekly_employees_report()
        cache_set('employees', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/expenses')
def api_expenses():
    date_from, date_to = _get_date_range(30)
    cache_key = f'expenses_{date_from}_{date_to}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    try:
        bands, okhra = get_masrof_range(date_from, date_to)
        result = {'bands': bands, 'okhra': okhra, 'total_bands': sum(bands.values())}
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily/<selected_date>')
def api_daily(selected_date):
    cache_key = f'daily_{selected_date}'
    if selected_date != str(date.today()):
        cached = cache_get(cache_key)
        if cached:
            return jsonify(cached)
    try:
        records, total_in, total_out = get_daily_khazna_report(selected_date)
        result = {
            'records': records, 'total_in': total_in,
            'total_out': total_out, 'net': total_in - total_out
        }
        if selected_date != str(date.today()):
            cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ Vercel Entry Point ============
# Vercel بيبحث عن متغير `app` من نوع WSGI application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
