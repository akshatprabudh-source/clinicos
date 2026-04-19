from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import sqlite3, hashlib, os, json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
DB = 'clinic.db'

# ── DB helpers ──────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff',
                name TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                gender TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT NOT NULL,
                aadhaar TEXT UNIQUE NOT NULL,
                address TEXT,
                next_visit TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                stock INTEGER NOT NULL DEFAULT 0,
                dose_per_day INTEGER NOT NULL DEFAULT 2,
                units_per_pack INTEGER NOT NULL DEFAULT 10,
                reorder_level INTEGER NOT NULL DEFAULT 5,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                next_visit TEXT NOT NULL,
                notes TEXT,
                created_by TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS prescription_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prescription_id INTEGER NOT NULL,
                medicine_id INTEGER NOT NULL,
                medicine_name TEXT NOT NULL,
                days INTEGER NOT NULL,
                dose_per_day INTEGER NOT NULL,
                units_used INTEGER NOT NULL
            );
        ''')
        # Default admin account
        pw = hashlib.sha256('admin123'.encode()).hexdigest()
        try:
            db.execute("INSERT INTO users (username,password,role,name) VALUES (?,?,?,?)",
                       ('admin', pw, 'admin', 'Administrator'))
            db.commit()
        except:
            pass

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ── Auth ─────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            if request.is_json: return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        return f(*args, **kwargs)
    return decorated

# ── Pages ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login_page'))
    return render_template('app.html', user=session['user'], role=session['role'])

@app.route('/login')
def login_page():
    if 'user' in session: return redirect('/')
    return render_template('login.html')

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "ClinicOS",
        "short_name": "ClinicOS",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0f4c81",
        "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"}]
    })

# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username=? AND password=?',
                      (data['username'], hash_pw(data['password']))).fetchone()
    if not user: return jsonify({'error': 'Invalid credentials'}), 401
    session['user'] = user['username']
    session['role'] = user['role']
    session['name'] = user['name']
    return jsonify({'role': user['role'], 'name': user['name']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

# ── Users API (admin only) ────────────────────────────────────────────────────
@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    db = get_db()
    users = db.execute('SELECT id,username,role,name,created_at FROM users').fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.json
    db = get_db()
    try:
        db.execute('INSERT INTO users (username,password,role,name) VALUES (?,?,?,?)',
                   (data['username'], hash_pw(data['password']), data['role'], data['name']))
        db.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(uid):
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (uid,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username=? AND password=?',
                      (session['user'], hash_pw(data['current']))).fetchone()
    if not user: return jsonify({'error': 'Current password incorrect'}), 400
    db.execute('UPDATE users SET password=? WHERE username=?',
               (hash_pw(data['new']), session['user']))
    db.commit()
    return jsonify({'ok': True})

# ── Patients API ──────────────────────────────────────────────────────────────
def next_patient_id(db):
    row = db.execute('SELECT COUNT(*) as c FROM patients').fetchone()
    return str(row['c'] + 1).zfill(4)

@app.route('/api/patients', methods=['GET'])
@login_required
def get_patients():
    db = get_db()
    q = request.args.get('q','').lower()
    if q:
        rows = db.execute("""SELECT * FROM patients WHERE
            lower(name) LIKE ? OR patient_id LIKE ? OR phone LIKE ?
            ORDER BY id DESC""", (f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()
    else:
        rows = db.execute('SELECT * FROM patients ORDER BY id DESC').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/patients', methods=['POST'])
@login_required
def create_patient():
    data = request.json
    db = get_db()
    pid = next_patient_id(db)
    try:
        db.execute('''INSERT INTO patients (patient_id,name,father_name,gender,age,phone,aadhaar,address)
                      VALUES (?,?,?,?,?,?,?,?)''',
                   (pid, data['name'], data['father_name'], data['gender'],
                    data['age'], data['phone'], data['aadhaar'], data.get('address','')))
        db.commit()
        return jsonify({'ok': True, 'patient_id': pid})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/patients/<pid>', methods=['GET'])
@login_required
def get_patient(pid):
    db = get_db()
    p = db.execute('SELECT * FROM patients WHERE patient_id=?', (pid,)).fetchone()
    if not p: return jsonify({'error': 'Not found'}), 404
    rxs = db.execute('''SELECT p.*, GROUP_CONCAT(i.medicine_name || ' (' || i.days || 'd)') as meds
                        FROM prescriptions p
                        LEFT JOIN prescription_items i ON i.prescription_id=p.id
                        WHERE p.patient_id=? GROUP BY p.id ORDER BY p.visit_date DESC''', (pid,)).fetchall()
    return jsonify({'patient': dict(p), 'history': [dict(r) for r in rxs]})

# ── Inventory API ─────────────────────────────────────────────────────────────
@app.route('/api/medicines', methods=['GET'])
@login_required
def get_medicines():
    db = get_db()
    q = request.args.get('q','').lower()
    if q:
        rows = db.execute("SELECT * FROM medicines WHERE lower(name) LIKE ? OR lower(category) LIKE ? ORDER BY name",
                          (f'%{q}%', f'%{q}%')).fetchall()
    else:
        rows = db.execute('SELECT * FROM medicines ORDER BY name').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/medicines', methods=['POST'])
@login_required
def add_medicine():
    data = request.json
    db = get_db()
    existing = db.execute('SELECT * FROM medicines WHERE lower(name)=?', (data['name'].lower(),)).fetchone()
    if existing:
        db.execute('UPDATE medicines SET stock=stock+? WHERE id=?', (data['stock'], existing['id']))
        db.commit()
        return jsonify({'ok': True, 'updated': True})
    db.execute('INSERT INTO medicines (name,category,stock,dose_per_day,units_per_pack,reorder_level) VALUES (?,?,?,?,?,?)',
               (data['name'], data.get('category',''), data['stock'],
                data.get('dose_per_day',2), data.get('units_per_pack',10), data.get('reorder_level',5)))
    db.commit()
    return jsonify({'ok': True, 'updated': False})

@app.route('/api/medicines/<int:mid>/restock', methods=['POST'])
@login_required
def restock(mid):
    data = request.json
    db = get_db()
    db.execute('UPDATE medicines SET stock=stock+? WHERE id=?', (data['qty'], mid))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/medicines/<int:mid>', methods=['DELETE'])
@login_required
@admin_required
def delete_medicine(mid):
    db = get_db()
    db.execute('DELETE FROM medicines WHERE id=?', (mid,))
    db.commit()
    return jsonify({'ok': True})

# ── Prescriptions API ─────────────────────────────────────────────────────────
@app.route('/api/prescriptions', methods=['POST'])
@login_required
def create_prescription():
    data = request.json
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id=?', (data['patient_id'],)).fetchone()
    if not patient: return jsonify({'error': 'Patient not found'}), 404
    max_days = max(item['days'] for item in data['items'])
    visit_date = data.get('visit_date', datetime.today().strftime('%Y-%m-%d'))
    next_visit = (datetime.strptime(visit_date, '%Y-%m-%d') + timedelta(days=max_days)).strftime('%Y-%m-%d')
    cur = db.execute('INSERT INTO prescriptions (patient_id,visit_date,next_visit,notes,created_by) VALUES (?,?,?,?,?)',
                     (data['patient_id'], visit_date, next_visit, data.get('notes',''), session['user']))
    rx_id = cur.lastrowid
    for item in data['items']:
        med = db.execute('SELECT * FROM medicines WHERE id=?', (item['medicine_id'],)).fetchone()
        if not med: continue
        units_used = med['dose_per_day'] * item['days']
        db.execute('INSERT INTO prescription_items (prescription_id,medicine_id,medicine_name,days,dose_per_day,units_used) VALUES (?,?,?,?,?,?)',
                   (rx_id, item['medicine_id'], med['name'], item['days'], med['dose_per_day'], units_used))
        db.execute('UPDATE medicines SET stock=MAX(0,stock-?) WHERE id=?', (units_used, item['medicine_id']))
    db.execute('UPDATE patients SET next_visit=? WHERE patient_id=?', (next_visit, data['patient_id']))
    db.commit()
    return jsonify({'ok': True, 'next_visit': next_visit})

# ── Dashboard API ─────────────────────────────────────────────────────────────
@app.route('/api/dashboard')
@login_required
def dashboard():
    db = get_db()
    today = datetime.today().strftime('%Y-%m-%d')
    total_patients = db.execute('SELECT COUNT(*) as c FROM patients').fetchone()['c']
    today_visits = db.execute('SELECT COUNT(*) as c FROM patients WHERE next_visit=?', (today,)).fetchone()['c']
    overdue = db.execute("SELECT COUNT(*) as c FROM patients WHERE next_visit < ? AND next_visit IS NOT NULL AND next_visit != ''", (today,)).fetchone()['c']
    low_stock = db.execute('SELECT COUNT(*) as c FROM medicines WHERE stock <= reorder_level').fetchone()['c']
    recent_patients = db.execute('SELECT patient_id,name,age,gender,created_at FROM patients ORDER BY id DESC LIMIT 5').fetchall()
    today_list = db.execute('SELECT patient_id,name,phone FROM patients WHERE next_visit=?', (today,)).fetchall()
    low_meds = db.execute('SELECT name,stock,reorder_level FROM medicines WHERE stock <= reorder_level ORDER BY stock').fetchall()
    return jsonify({
        'stats': {'total_patients': total_patients, 'today_visits': today_visits, 'overdue': overdue, 'low_stock': low_stock},
        'recent_patients': [dict(r) for r in recent_patients],
        'today_visits_list': [dict(r) for r in today_list],
        'low_stock_meds': [dict(r) for r in low_meds]
    })

@app.route('/api/upcoming_visits')
@login_required
def upcoming_visits():
    db = get_db()
    today = datetime.today().strftime('%Y-%m-%d')
    rows = db.execute("""SELECT p.patient_id, p.name, p.phone, p.next_visit,
        (SELECT visit_date FROM prescriptions WHERE patient_id=p.patient_id ORDER BY visit_date DESC LIMIT 1) as last_visit
        FROM patients p WHERE p.next_visit IS NOT NULL AND p.next_visit != ''
        ORDER BY p.next_visit""").fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    init_db()
    print("\n✅ ClinicOS is running!")
    print("🌐 Open in browser: http://localhost:5000")
    print("📱 On phone (same WiFi): http://<your-pc-ip>:5000")
    print("⏹  Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
