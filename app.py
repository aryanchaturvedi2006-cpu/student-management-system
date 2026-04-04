from flask import Flask, render_template, request, redirect, url_for, Response, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

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
            extra_activities TEXT,
            sports_achievements TEXT,
            courses TEXT
        )
    ''')

    # Add password column dynamically if missing
    cursor.execute("PRAGMA table_info(students)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'password' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN password TEXT DEFAULT 'student123'")

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

    # admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # default admin
    cursor.execute("SELECT * FROM admin WHERE username='admin'")
    if not cursor.fetchone():
        hashed = generate_password_hash('admin123')
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", hashed))

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

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

# ---------------- ADMIN ADMIN ----------------
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
        student_pwd_hash = generate_password_hash('student123')

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
    for s in students_raw:
        courses = json.loads(s[14]) if s[14] else []
        students.append((s, courses))

    # Handle Edit View Toggle Data
    edit_id = request.args.get('edit_id')
    edit_student = None
    edit_courses = []
    if edit_id:
        cursor.execute("SELECT * FROM students WHERE id=?", (edit_id,))
        edit_student = cursor.fetchone()
        if edit_student:
            edit_courses = json.loads(edit_student[14]) if edit_student[14] else []

    conn.close()
    return render_template('index.html', students=students, edit_student=edit_student, edit_courses=edit_courses, search=search, sort=sort)


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
    
    conn.close()
    return render_template('student_portal.html', student=student, courses=courses, fee_record=fee_record, transactions=txs)


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

if __name__ == '__main__':
    app.run(debug=True)