from flask import Flask, render_template, request, redirect, url_for, Response, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import os
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

app = Flask(__name__)
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(days=30)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max-limit

# -------- OAUTH CONFIGURATION --------
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            age INTEGER,
            dob TEXT,
            gender TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            semester TEXT,
            gpa REAL,
            attendance TEXT,
            sports_achievements TEXT,
            courses TEXT,
            stars INTEGER DEFAULT 0,
            contest_rank TEXT DEFAULT 'Unranked'
        )
    ''')

    # Add password and profile_pic columns dynamically if missing
    cursor.execute("PRAGMA table_info(students)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'password' not in columns:
        default_student_pwd = os.getenv('DEFAULT_STUDENT_PASSWORD', 'student123')
        cursor.execute(f"ALTER TABLE students ADD COLUMN password TEXT DEFAULT '{default_student_pwd}'")
    if 'profile_pic' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN profile_pic TEXT DEFAULT ''")
    if 'stars' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN stars INTEGER DEFAULT 0")
    if 'contest_rank' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN contest_rank TEXT DEFAULT 'Unranked'")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_name TEXT,
            date TEXT,
            status TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            total_amount REAL DEFAULT 0.0,
            paid_amount REAL DEFAULT 0.0,
            due_date TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL,
            date TEXT,
            method TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NULL,
            uploader_role TEXT,
            title TEXT,
            file_path TEXT,
            file_type TEXT,
            is_pyq INTEGER DEFAULT 0,
            uploaded_at TEXT,
            assignment_task_id INTEGER NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(documents)")
    doc_cols = [info[1] for info in cursor.fetchall()]
    if 'assignment_task_id' not in doc_cols:
        cursor.execute("ALTER TABLE documents ADD COLUMN assignment_task_id INTEGER NULL")
    if 'is_pyq' not in doc_cols:
        cursor.execute("ALTER TABLE documents ADD COLUMN is_pyq INTEGER DEFAULT 0")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignment_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            due_date TEXT,
            created_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            due_date TEXT,
            duration_minutes INTEGER,
            questions_json TEXT,
            is_contest INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(quizzes)")
    quiz_cols = [info[1] for info in cursor.fetchall()]
    if 'is_contest' not in quiz_cols:
        cursor.execute("ALTER TABLE quizzes ADD COLUMN is_contest INTEGER DEFAULT 0")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            student_id INTEGER,
            start_time TEXT,
            submit_time TEXT,
            answers_json TEXT,
            score REAL,
            UNIQUE(quiz_id, student_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            meet_code TEXT,
            host_id TEXT,
            created_at TEXT
        )
    ''')

    # admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # oauth_users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT,
            provider_id TEXT,
            email TEXT,
            name TEXT,
            profile_pic TEXT,
            user_type TEXT,
            created_at TEXT,
            UNIQUE(provider, provider_id)
        )
    ''')

    # default admin
    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
    cursor.execute("SELECT * FROM admin WHERE username=?", (admin_user,))
    if not cursor.fetchone():
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
        hashed = generate_password_hash(admin_pass)
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (admin_user, hashed))

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')

        session.permanent = bool(remember)

        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        
        def verify_pass(stored, provided):
            if stored and (stored.startswith('scrypt:') or stored.startswith('pbkdf2:')):
                return check_password_hash(stored, provided)
            return stored == provided
        
        # Check Admin
        cursor.execute("SELECT id, username, password FROM admin WHERE username=?", (username,))
        admin = cursor.fetchone()
        
        if admin and verify_pass(admin[2], password):
            conn.close()
            session['user'] = admin[1]
            session['role'] = 'admin'
            return redirect(url_for('home'))
            
        # Check Student (username = roll)
        cursor.execute("SELECT id, name, password FROM students WHERE roll=?", (username,))
        student = cursor.fetchone()
        conn.close()
        
        if student and verify_pass(student[2], password):
            session['user'] = student[1] # name
            session['student_id'] = student[0]
            session['role'] = 'student'
            return redirect(url_for('student_dashboard'))
            
        return "Invalid username (or Roll Number) resulting in incorrect password!"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------- OAUTH ROUTES --------
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            picture = user_info.get('picture', '')
            provider_id = user_info.get('sub')
            
            conn = sqlite3.connect('students.db')
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id, user_type FROM oauth_users WHERE provider=? AND provider_id=?", ('google', provider_id))
            oauth_user = cursor.fetchone()
            
            if not oauth_user:
                # Create new OAuth user
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    INSERT INTO oauth_users (provider, provider_id, email, name, profile_pic, user_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('google', provider_id, email, name, picture, 'student', created_at))
                conn.commit()
                user_type = 'student'
                oauth_user_id = cursor.lastrowid
            else:
                oauth_user_id, user_type = oauth_user
            
            # Link to student profile
            if user_type == 'student':
                cursor.execute("SELECT id FROM students WHERE email=?", (email,))
                student_record = cursor.fetchone()
                if student_record:
                    session['student_id'] = student_record[0]
                else:
                    # Create a blank student profile for the new OAuth user
                    student_pwd_hash = generate_password_hash('oauth_login_only')
                    cursor.execute("INSERT INTO students (name, email, roll, password) VALUES (?, ?, ?, ?)", (name, email, f"OAUTH-{str(provider_id)[:6]}", student_pwd_hash))
                    conn.commit()
                    session['student_id'] = cursor.lastrowid
            
            conn.close()
            
            # Set session
            session['user'] = name
            session['email'] = email
            session['oauth_user_id'] = oauth_user_id
            session['role'] = user_type
            session['oauth_provider'] = 'google'
            
            # Redirect based on user type
            if user_type == 'admin':
                return redirect(url_for('home'))
            else:
                return redirect(url_for('student_dashboard'))
    except Exception as e:
        print(f"OAuth error: {e}")
        return redirect(url_for('login'))


# -------- END OAUTH ROUTES --------

def generate_notifications(student_id=None):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, due_date FROM assignment_tasks")
    tasks = cursor.fetchall()
    cursor.execute("SELECT title, due_date FROM quizzes")
    quizzes = cursor.fetchall()
    cursor.execute("SELECT title, meet_code FROM live_classes")
    live_classes = cursor.fetchall()
    conn.close()
    
    alerts = []
    
    for cls in live_classes:
        alerts.append({"type": "urgent", "msg": f"🔴 LIVE NOW: '{cls[0]}' Video Class is active! Join in 'Study Materials'."})
        
    now_date = datetime.now().date()
    tmrw_date = now_date + timedelta(days=1)
    
    def process_items(items, label):
        for item in items:
            title, due_str = item[0], item[1]
            try: due_dt = datetime.fromisoformat(due_str).date()
            except ValueError:
                try: due_dt = datetime.strptime(due_str, "%Y-%m-%dT%H:%M").date()
                except: continue
                
            if due_dt == now_date:
                alerts.append({"type": "urgent", "msg": f"URGENT: {label} '{title}' is due TODAY!"})
            elif due_dt == tmrw_date:
                alerts.append({"type": "warning", "msg": f"Reminder: {label} '{title}' is due TOMORROW."})
                
    process_items(tasks, "Assignment")
    process_items(quizzes, "Live Quiz")
    return alerts

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']
        age = request.form.get('age', None)
        dob = request.form.get('dob', '')
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        semester = request.form.get('semester', '')
        attendance = request.form.get('attendance', '')
        extra_activities = request.form.get('extra_activities', '')
        sports_achievements = request.form.get('sports_achievements', '')

        course_names = request.form.getlist('course_name[]')
        marks_list = request.form.getlist('marks[]')

        courses = []
        marks_float = []

        for cname, m in zip(course_names, marks_list):
            if cname.strip() != '' and m != '':
                try:
                    m_float = float(m)
                    if m_float < 0 or m_float > 100:
                        return "Marks must be between 0 and 100!"
                    courses.append([cname.strip(), m_float])
                    marks_float.append(m_float)
                except:
                    return "Invalid marks!"

        if not name.strip() or not roll.strip():
            return "Name and Roll are required!"

        if attendance:
            try:
                att = float(attendance)
                if att < 0 or att > 100:
                    return "Attendance must be between 0 and 100!"
            except:
                return "Invalid attendance!"

        if marks_float:
            avg = sum(marks_float) / len(marks_float)
            gpa = round((avg / 100) * 10, 2)
        else:
            gpa = 0

        courses_json = json.dumps(courses)
        default_student_pwd = os.getenv('DEFAULT_STUDENT_PASSWORD', 'student123')
        student_pwd_hash = generate_password_hash(default_student_pwd)

        cursor.execute('''
            INSERT INTO students
            (name, roll, age, dob, gender, address, phone, email, semester, gpa, attendance, extra_activities, sports_achievements, courses, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, roll, age, dob, gender, address, phone, email, semester, gpa, attendance, extra_activities, sports_achievements, courses_json, student_pwd_hash))

        conn.commit()

    # SEARCH + SORT
    search = request.args.get('search', '')
    sort = request.args.get('sort', '')

    query = "SELECT * FROM students"
    params = []

    if search:
        query += " WHERE name LIKE ? OR roll LIKE ? OR semester LIKE ?"
        params.extend(['%' + search + '%', '%' + search + '%', '%' + search + '%'])

    if sort == "gpa":
        query += " ORDER BY gpa DESC"
    elif sort == "name":
        query += " ORDER BY name ASC"
    elif sort == "semester":
        query += " ORDER BY semester ASC"

    cursor.execute(query, params)
    students_raw = cursor.fetchall()

    students = []
    total_gpa = 0
    valid_gpa_count = 0
    total_attendance = 0
    valid_attendance_count = 0

    for s in students_raw:
        courses = json.loads(s[14]) if s[14] else []
        students.append((s, courses))
        
        # Calculate GPA Average
        if s[10] is not None and float(s[10]) > 0:
            total_gpa += float(s[10])
            valid_gpa_count += 1
            
        # Calculate Attendance Average
        if s[11] is not None and str(s[11]).strip() != '':
            try:
                total_attendance += float(s[11])
                valid_attendance_count += 1
            except ValueError:
                pass
                
    avg_gpa = round(total_gpa / valid_gpa_count, 1) if valid_gpa_count > 0 else 0.0
    avg_attendance = round(total_attendance / valid_attendance_count, 1) if valid_attendance_count > 0 else 0.0
    total_students = len(students)

    # Handle Edit View Toggle Data
    edit_id = request.args.get('edit_id')
    edit_student = None
    edit_courses = []
    if edit_id:
        cursor.execute("SELECT * FROM students WHERE id=?", (edit_id,))
        edit_student = cursor.fetchone()
        if edit_student:
            edit_courses = json.loads(edit_student[14]) if edit_student[14] else []

    # Fetch all global study materials (excluding PYQs)
    cursor.execute("SELECT * FROM documents WHERE student_id IS NULL AND is_pyq=0 ORDER BY uploaded_at DESC")
    global_docs = cursor.fetchall()
    
    # Fetch all PYQs
    cursor.execute("SELECT * FROM documents WHERE is_pyq=1 ORDER BY uploaded_at DESC")
    pyqs = cursor.fetchall()
    
    # Get all assignment tasks
    cursor.execute("SELECT * FROM assignment_tasks ORDER BY due_date ASC")
    assignment_tasks = cursor.fetchall()
    
    cursor.execute("SELECT * FROM live_classes ORDER BY created_at DESC")
    active_classes = cursor.fetchall()

    conn.close()
    return render_template('index.html', students=students, edit_student=edit_student, edit_courses=edit_courses, search=search, sort=sort, avg_gpa=avg_gpa, avg_attendance=avg_attendance, total_students=total_students, global_docs=global_docs, pyqs=pyqs, assignment_tasks=assignment_tasks, active_classes=active_classes)


# ---------------- STUDENT PORTAL ----------------
@app.route('/student_dashboard')
def student_dashboard():
    if 'user' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
        
    student_id = session['student_id']
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = cursor.fetchone()
    courses = json.loads(student[14]) if student[14] else []
    
    # Get fees 
    cursor.execute("SELECT * FROM fees WHERE student_id=?", (student_id,))
    fee_record = cursor.fetchone()
    
    # Get past transactions
    cursor.execute("SELECT * FROM transactions WHERE student_id=? ORDER BY date DESC", (student_id,))
    txs = cursor.fetchall()
    
    # Get private assignments
    cursor.execute("SELECT * FROM documents WHERE student_id=? AND file_type='Assignment Submission' ORDER BY uploaded_at DESC", (student_id,))
    assignments = cursor.fetchall()
    
    # Fetch all global study materials (excluding PYQs)
    cursor.execute("SELECT * FROM documents WHERE student_id IS NULL AND file_type != 'Assignment Submission' AND is_pyq=0 ORDER BY uploaded_at DESC")
    study_materials = cursor.fetchall()

    # Fetch all PYQs
    cursor.execute("SELECT * FROM documents WHERE is_pyq=1 ORDER BY uploaded_at DESC")
    pyqs = cursor.fetchall()
    
    # Fetch all tasks from teachers
    cursor.execute("SELECT * FROM assignment_tasks ORDER BY due_date ASC")
    all_tasks = cursor.fetchall()
    
    # Fetch quizzes
    cursor.execute('''
        SELECT q.id, q.title, q.due_date, q.duration_minutes, a.start_time, a.submit_time, a.score
        FROM quizzes q
        LEFT JOIN quiz_attempts a ON q.id = a.quiz_id AND a.student_id = ?
        ORDER BY q.due_date ASC
    ''', (student_id,))
    active_quizzes = cursor.fetchall()
    
    # Fetch live classes
    cursor.execute("SELECT * FROM live_classes ORDER BY created_at DESC")
    live_classes = cursor.fetchall()
    
    alerts = generate_notifications(student_id)
    
    # Structure task status
    task_dashboard = []
    from datetime import datetime as dt
    now = dt.now()
    for t in all_tasks:
        try:
            due_dt = dt.fromisoformat(t[3])
        except ValueError:
            due_dt = dt.strptime(t[3], "%Y-%m-%dT%H:%M") # fallback
            
        locked = now > due_dt
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE student_id=? AND assignment_task_id=?", (student_id, t[0]))
        attempts = cursor.fetchone()[0]
        
        task_dashboard.append({
            "id": t[0],
            "title": t[1],
            "desc": t[2],
            "due": t[3].replace("T", " "),
            "locked": locked,
            "attempts": attempts,
            "can_submit": (not locked) and (attempts < 2)
        })
        
    conn.close()
    return render_template('student_portal.html', student=student, courses=courses, fee_record=fee_record, transactions=txs, assignments=assignments, study_materials=study_materials, pyqs=pyqs, task_dashboard=task_dashboard, active_quizzes=active_quizzes, notifications=alerts, live_classes=live_classes)


# ---------------- DELETE AND EDIT ----------------
@app.route('/delete/<int:id>')
def delete(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))

    if request.method == 'GET':
        return redirect(url_for('home', edit_id=id))

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    name = request.form['name']
    roll = request.form['roll']
    age = request.form.get('age', None)
    dob = request.form.get('dob', '')
    gender = request.form.get('gender', '')
    address = request.form.get('address', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    semester = request.form.get('semester', '')
    attendance = request.form.get('attendance', '')
    extra_activities = request.form.get('extra_activities', '')
    sports_achievements = request.form.get('sports_achievements', '')

    course_names = request.form.getlist('course_name[]')
    marks_list = request.form.getlist('marks[]')

    courses = []
    marks_float = []

    for cname, m in zip(course_names, marks_list):
        if cname.strip() != '' and m != '':
            m_float = float(m)
            courses.append([cname.strip(), m_float])
            marks_float.append(m_float)

    avg = sum(marks_float) / len(marks_float) if marks_float else 0
    gpa = round((avg / 100) * 10, 2)
    courses_json = json.dumps(courses)

    cursor.execute('''
        UPDATE students SET 
        name=?, roll=?, age=?, dob=?, gender=?, address=?, phone=?, email=?, 
        semester=?, attendance=?, extra_activities=?, sports_achievements=?, 
        gpa=?, courses=? WHERE id=?
    ''', (name, roll, age, dob, gender, address, phone, email, semester, 
          attendance, extra_activities, sports_achievements, gpa, courses_json, id))
    
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

# ---------------- ATTENDANCE API ----------------
@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    student_id = data.get('student_id')
    course_name = data.get('course_name')
    date = data.get('date')
    status = data.get('status')

    if not all([student_id, course_name, date, status]):
        return jsonify({"error": "Missing data"}), 400

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM attendance WHERE student_id=? AND course_name=? AND date=?", (student_id, course_name, date))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE attendance SET status=? WHERE id=?", (status, existing[0]))
    else:
        cursor.execute("INSERT INTO attendance (student_id, course_name, date, status) VALUES (?, ?, ?, ?)", (student_id, course_name, date, status))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/attendance/<int:student_id>', methods=['GET'])
def get_attendance(student_id):
    # Both Admin and Student can check attendance but student only their own
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    if session.get('role') == 'student' and session.get('student_id') != student_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT course_name, date, status FROM attendance WHERE student_id=? ORDER BY date DESC", (student_id,))
    records = cursor.fetchall()
    
    cursor.execute("SELECT courses FROM students WHERE id=?", (student_id,))
    student_row = cursor.fetchone()
    conn.close()
    
    if not student_row:
        return jsonify({"error": "Student not found"}), 404
        
    courses_json = student_row[0]
    enrolled_courses = json.loads(courses_json) if courses_json else []
    course_names = [c[0] for c in enrolled_courses]
    
    history = [{"course_name": r[0], "date": r[1], "status": r[2]} for r in records]
    
    stats = {}
    for c in course_names:
        stats[c] = {"total": 0, "present": 0, "percentage": 0}
        
    for r in records:
        cname, date, status = r
        if cname in stats:
            stats[cname]["total"] += 1
            if status == "Present":
                stats[cname]["present"] += 1
                
    for c in stats:
        if stats[c]["total"] > 0:
            stats[c]["percentage"] = round((stats[c]["present"] / stats[c]["total"]) * 100, 1)

    return jsonify({"courses": course_names, "history": history, "stats": stats})

# ---------------- FEES API & PAYMENT ----------------
@app.route('/api/fees/assign', methods=['POST'])
def assign_fees():
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    student_id = data.get('student_id')
    amount = float(data.get('amount', 0))
    due_date = data.get('due_date', '')
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM fees WHERE student_id=?", (student_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE fees SET total_amount=?, due_date=? WHERE student_id=?", (amount, due_date, student_id))
    else:
        cursor.execute("INSERT INTO fees (student_id, total_amount, paid_amount, due_date) VALUES (?, ?, 0.0, ?)", (student_id, amount, due_date))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/all_fees', methods=['GET'])
def get_all_fees():
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 401
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT students.id, students.name, students.roll, fees.total_amount, fees.paid_amount, fees.due_date 
        FROM students 
        LEFT JOIN fees ON students.id = fees.student_id
    ''')
    res = cursor.fetchall()
    conn.close()
    
    fees_list = [{"student_id": r[0], "name": r[1], "roll": r[2], "total": r[3] or 0.0, "paid": r[4] or 0.0, "due": r[5] or ''} for r in res]
    return jsonify(fees_list)

@app.route('/api/fees/record_payment', methods=['POST'])
def record_payment():
    if session.get('role') != 'admin': 
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    student_id = data.get('student_id')
    amount_paid = float(data.get('amount_paid', 0))
    method = data.get('method', 'Manual Payment')
    
    if amount_paid <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400
        
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (student_id, amount, date, method) VALUES (?, ?, ?, ?)", (student_id, amount_paid, date_str, method))
    cursor.execute("UPDATE fees SET paid_amount = paid_amount + ? WHERE student_id=?", (amount_paid, student_id))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/checkout', methods=['POST'])
def checkout():
    if session.get('role') != 'student': return redirect(url_for('login'))
    
    student_id = session['student_id']
    amount_to_pay = float(request.form.get('amount', 0))
    if amount_to_pay <= 0: return "Invalid amount"
    
    # We load the mock simulated gateway page
    return render_template('mock_payment.html', amount=amount_to_pay, student_id=student_id)
        
@app.route('/process_payment', methods=['POST'])
def process_payment():
    if session.get('role') != 'student': return redirect(url_for('login'))

    student_id = request.form.get('student_id')
    amount = float(request.form.get('amount', 0))
    card = request.form.get('card_number', '1234')
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (student_id, amount, date, method) VALUES (?, ?, ?, ?)", (student_id, amount, date_str, f"Card ending in {card[-4:]}"))
    cursor.execute("UPDATE fees SET paid_amount = paid_amount + ? WHERE student_id=?", (amount, student_id))
    
    conn.commit()
    conn.close()
    
    return render_template('payment_success.html')

# ---------------- EXPORT ----------------
@app.route('/export')
def export():
    if session.get('role') != 'admin': return redirect(url_for('login'))

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()

    def generate():
        yield "Name,Roll,Semester,GPA,Attendance\n"
        for s in students:
            yield f"{s[1]},{s[2]},{s[9]},{s[10]},{s[11]}\n"

    return Response(generate(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=students.csv"})

# ---------------- FILE UPLOAD HANDLERS ----------------
@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user' not in session: return redirect(url_for('login'))
    if 'photo' not in request.files: return "No photo provided", 400
    
    file = request.files['photo']
    if file.filename == '': return "Empty filename", 400
    
    student_id = session.get('student_id')
    if not student_id: return "Admin cannot upload their own pic here", 403
    
    import time
    filename = f"{student_id}_{int(time.time())}_{secure_filename(file.filename)}"
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profiles'), exist_ok=True)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles', filename)
    file.save(filepath)
    
    db_path = f"uploads/profiles/{filename}"
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET profile_pic=? WHERE id=?", (db_path, student_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('student_dashboard'))
    
@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'user' not in session: return redirect(url_for('login'))
    
    title = request.form.get('title', 'Untitled Document')
    file_type = request.form.get('file_type', 'unknown') 
    is_global = request.form.get('is_global', 'false') == 'true'
    is_pyq = request.form.get('is_pyq', 'false') == 'true'
    task_id = request.form.get('task_id', None)
    
    if 'document' not in request.files: return "No file element found", 400
    file = request.files['document']
    if file.filename == '': return "Empty filename", 400
    
    role = session.get('role')
    student_id = session.get('student_id') if role == 'student' else None
    
    if (is_global or is_pyq) and role != 'admin':
        return "Only authorized admins can upload global study materials or PYQs.", 403
        
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
        
    # --- TIME-LOCK AND ATTEMPT VALIDATION ENGINE ---
    if task_id and role == 'student':
        cursor.execute("SELECT due_date FROM assignment_tasks WHERE id=?", (task_id,))
        task_info = cursor.fetchone()
        if not task_info:
            conn.close()
            return "Task not found", 404
            
        due_date_str = task_info[0]
        from datetime import datetime as dt
        try:
            due_datetime = dt.fromisoformat(due_date_str)
        except ValueError:
            due_datetime = dt.strptime(due_date_str, "%Y-%m-%dT%H:%M")
            
        if dt.now() > due_datetime:
            conn.close()
            return "Deadline has strictly bypassed. System rejected the file drop.", 403
            
        cursor.execute("SELECT COUNT(*) FROM documents WHERE student_id=? AND assignment_task_id=?", (student_id, task_id))
        attempts = cursor.fetchone()[0]
        if attempts >= 2:
            conn.close()
            return "Maximum allowed attempts (2) exhausted. Access locked.", 403
    # -----------------------------------------------

    path_dir = 'pyqs' if is_pyq else ('study_materials' if is_global else 'assignments')
    import time
    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', path_dir), exist_ok=True)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', path_dir, filename)
    file.save(filepath)
    
    db_path = f"uploads/documents/{path_dir}/{filename}"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO documents (student_id, uploader_role, title, file_path, file_type, is_pyq, uploaded_at, assignment_task_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, role, title, db_path, file_type, 1 if is_pyq else 0, date_str, task_id))
    conn.commit()
    conn.close()
    
    if role == 'admin':
        return redirect(url_for('home'))
        
    return redirect(url_for('student_dashboard'))
    
@app.route('/create_assignment_task', methods=['POST'])
def create_assignment_task():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    title = request.form.get('title')
    description = request.form.get('description', '')
    due_date = request.form.get('due_date') # HTML5 datetime-local string
    
    if not title or not due_date: return "Missing fields", 400
    
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO assignment_tasks (title, description, due_date, created_at)
        VALUES (?, ?, ?, ?)
    ''', (title, description, due_date, date_str))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/extend_deadline/<int:task_id>', methods=['POST'])
def extend_deadline(task_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    new_due_date = request.form.get('due_date')
    if not new_due_date: return "Missing deadline", 400
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE assignment_tasks SET due_date=? WHERE id=?", (new_due_date, task_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/create_custom_quiz', methods=['POST'])
def create_custom_quiz():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    title = request.form.get('title', 'Untitled Quiz')
    due_date = request.form.get('due_date')
    duration = int(request.form.get('duration_minutes', 15))
    q_count = int(request.form.get('question_count', 0))
    
    is_contest = 1 if request.form.get('is_contest') == '1' else 0
    
    questions = []
    import json
    for i in range(1, q_count + 1):
        q_text = request.form.get(f'q_{i}_text')
        if not q_text: continue
        q_type = request.form.get(f'q_{i}_type', 'text')
        marks = float(request.form.get(f'q_{i}_marks', 1))
        
        q_obj = {"id": i, "text": q_text, "type": q_type, "marks": marks}
        if q_type == 'mcq':
            q_obj["opts"] = [
                request.form.get(f'q_{i}_A', ''),
                request.form.get(f'q_{i}_B', ''),
                request.form.get(f'q_{i}_C', ''),
                request.form.get(f'q_{i}_D', '')
            ]
            q_obj["ans"] = request.form.get(f'q_{i}_ans', 'a')
        questions.append(q_obj)
        
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO quizzes (title, due_date, duration_minutes, questions_json, is_contest, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, due_date, duration, json.dumps(questions), is_contest, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

# ---------------- QUIZ HANDLERS ----------------
@app.route('/start_quiz/<int:quiz_id>', methods=['POST'])
def start_quiz(quiz_id):
    if session.get('role') != 'student': return redirect(url_for('login'))
    student_id = session['student_id']
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quiz_attempts WHERE quiz_id=? AND student_id=?", (quiz_id, student_id))
    attempt = cursor.fetchone()
    if attempt:
        conn.close()
        return redirect(url_for('take_quiz', quiz_id=quiz_id))
        
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO quiz_attempts (quiz_id, student_id, start_time) VALUES (?, ?, ?)", (quiz_id, student_id, start_time))
    conn.commit()
    conn.close()
    return redirect(url_for('take_quiz', quiz_id=quiz_id))

@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    if session.get('role') != 'student': return redirect(url_for('login'))
    student_id = session['student_id']
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,))
    quiz = cursor.fetchone()
    
    cursor.execute("SELECT start_time, submit_time FROM quiz_attempts WHERE quiz_id=? AND student_id=?", (quiz_id, student_id))
    attempt = cursor.fetchone()
    conn.close()
    
    if not quiz or not attempt: return "Invalid access", 400
    if attempt[1]: return redirect(url_for('student_dashboard')) # Already submitted
    
    start_dt = datetime.strptime(attempt[0], "%Y-%m-%d %H:%M:%S")
    duration = timedelta(minutes=quiz[3])
    expire_dt = start_dt + duration
    time_left_seconds = (expire_dt - datetime.now()).total_seconds()
    
    if time_left_seconds <= -5: # strict 5s backend lock
        # Force arbitrary empty submission since they timed out server-side
        return redirect(url_for('force_submit_quiz', quiz_id=quiz_id))
        
    raw_qs = json.loads(quiz[4])
    return render_template('take_quiz.html', quiz=quiz, questions=raw_qs, time_left=int(time_left_seconds))

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST', 'GET'])
def submit_quiz(quiz_id):
    if session.get('role') != 'student': return redirect(url_for('login'))
    student_id = session['student_id']
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,))
    quiz = cursor.fetchone()
    cursor.execute("SELECT start_time, submit_time FROM quiz_attempts WHERE quiz_id=? AND student_id=?", (quiz_id, student_id))
    attempt = cursor.fetchone()
    
    if not quiz or not attempt or attempt[1]: 
        conn.close()
        return redirect(url_for('student_dashboard'))
        
    start_dt = datetime.strptime(attempt[0], "%Y-%m-%d %H:%M:%S")
    duration = timedelta(minutes=quiz[3])
    expire_dt = start_dt + duration
    
    cheating_flag = request.form.get('cheating_flag') == "true"
    
    # Network grace period 5 seconds
    if datetime.now() > expire_dt + timedelta(seconds=5) or cheating_flag:
        # Even though JS forces, if someone bypassed, we reject answers, score 0
        answers = {"violation_flag": "Exam forcefully terminated due to zero-tolerance cheating violation or latency timeout."}
        score = 0.0
    else:
        # Evaluate provided answers based on dynamic marks
        raw_qs = json.loads(quiz[4])
        answers = {}
        earned = 0.0
        total_possible = 0.0
        
        for q in raw_qs:
            q_id = str(q['id'])
            user_ans = request.form.get('q_' + q_id, '').strip()
            answers[q_id] = user_ans
            q_points = float(q.get('marks', 1))
            total_possible += q_points
            
            if q['type'] == 'mcq' and user_ans.lower() == q.get('ans', '').lower():
                earned += q_points
            # Written answers manually graded later
            
        score = (earned / total_possible) * 100 if total_possible > 0 else 0

    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE quiz_attempts SET submit_time=?, answers_json=?, score=? WHERE quiz_id=? AND student_id=?", 
                   (submit_time, json.dumps(answers), score, quiz_id, student_id))
    conn.commit()
    conn.close()
    return redirect(url_for('student_dashboard'))
    
@app.route('/force_submit_quiz/<int:quiz_id>')
def force_submit_quiz(quiz_id):
    # A dummy endpoint to execute a blank zero-graded fallback if they drastically missed the time
    return submit_quiz(quiz_id)

# ---------------- LIVE CLASS HANDLERS ----------------
@app.route('/create_live_class', methods=['POST'])
def create_live_class():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    title = request.form.get('title', 'Online Class')
    # Generate unique 9 character meet code e.g. "edu-abcd-xyz"
    import random, string
    code = f"edu-{''.join(random.choices(string.ascii_lowercase, k=4))}-{''.join(random.choices(string.ascii_lowercase, k=4))}"
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO live_classes (title, meet_code, host_id, created_at) VALUES (?, ?, ?, ?)", 
                   (title, code, 'admin', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/end_live_class/<int:class_id>')
def end_live_class(class_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM live_classes WHERE id=?", (class_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/join_class/<meet_code>')
def join_class(meet_code):
    if 'user' not in session: return redirect(url_for('login'))
    role = session.get('role')
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM live_classes WHERE meet_code=?", (meet_code,))
    class_info = cursor.fetchone()
    conn.close()
    
    if not class_info: return "Class ended or does not exist. The host may have terminated it.", 404
    
    # Pass user contextual data to UI
    display_name = ''
    if role == 'student':
        # Grab actual student name
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        c.execute("SELECT name FROM students WHERE id=?", (session['student_id'],))
        std = c.fetchone()
        display_name = std[0] if std else 'Guest Student'
        conn.close()
    else:
        display_name = 'Admin (Host)'
        
    return render_template('live_class.html', meet_code=meet_code, title=class_info[0], display_name=display_name, role=role)

@app.route('/delete_document/<int:doc_id>')
def delete_document(doc_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM documents WHERE id=?", (doc_id,))
    doc = cursor.fetchone()
    if doc:
        try:
            os.remove(os.path.join('static', doc[0]))
        except Exception as e:
            pass
        cursor.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/api/leaderboard')
def get_leaderboard():
    from flask import jsonify
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    # Fetch students and their contest performance
    cursor.execute("""
        SELECT s.id, s.name, s.stars, s.contest_rank, 
               (SELECT SUM(score) FROM quiz_attempts qa JOIN quizzes q ON qa.quiz_id = q.id WHERE qa.student_id = s.id AND q.is_contest = 1) as contest_score
        FROM students s
        ORDER BY contest_score DESC, s.stars DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for r in rows:
        leaderboard.append({
            "id": r[0],
            "name": r[1],
            "stars": r[2] or 0,
            "rank": r[3] or 'Unranked',
            "score": r[4] or 0
        })
    return jsonify(leaderboard)

@app.route('/admin/finalize_contest', methods=['POST'])
def finalize_contest():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # Calculate performance for the LATEST contest
    cursor.execute("SELECT id FROM quizzes WHERE is_contest = 1 ORDER BY created_at DESC LIMIT 1")
    latest_contest = cursor.fetchone()
    if not latest_contest:
        conn.close()
        return "No contest found", 404
        
    contest_id = latest_contest[0]
    
    # Get all attempts for this contest
    cursor.execute("""
        SELECT student_id, score, time_taken 
        FROM quiz_attempts 
        WHERE quiz_id = ? 
        ORDER BY score DESC, time_taken ASC
    """, (contest_id,))
    attempts = cursor.fetchall()
    
    total_participants = len(attempts)
    if total_participants == 0:
        conn.close()
        return "No participants to rank. Make sure pupils have submitted their contest entries.", 200
        
    for i, att in enumerate(attempts):
        student_id = att[0]
        rank_label = 'Participation'
        star_reward = 1
        
        if i < max(1, int(0.1 * total_participants)):
            rank_label = 'Platinum'
            star_reward = 5
        elif i < max(2, int(0.3 * total_participants)):
            rank_label = 'Gold'
            star_reward = 3
        elif i < max(3, int(0.6 * total_participants)):
            rank_label = 'Silver'
            star_reward = 2
            
        cursor.execute("UPDATE students SET stars = stars + ?, contest_rank = ? WHERE id = ?", (star_reward, rank_label, student_id))
    
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)