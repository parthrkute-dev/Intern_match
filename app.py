from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
app = Flask(__name__)
app.secret_key = 'intern_match_2026_premium'
DB_FILE = 'internship.db'

# --- EMAIL CONFIGURATION ---
EMAIL_SENDER = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password" 

def send_user_response_email(target_email, user_type, user_name):
    """Sends a confirmation email directly to the user's ID."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Intern Match Team <{EMAIL_SENDER}>"
        msg['To'] = target_email
        msg['Subject'] = "Profile Successfully Activated | Intern Match"

        role = "Recruiter" if user_type == 'company' else "Student"
        body = f"Hello {user_name},\n\nYour {role} profile for {target_email} is now active. Our AI is matching you with opportunities!\n\nBest regards,\nIntern Match Team"
        
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Email Error: {e}")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS student_profiles 
            (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, sector TEXT, role TEXT, 
             skills TEXT, stipend TEXT, mode TEXT, hobbies TEXT, address TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS company_profiles 
            (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, sector TEXT, role TEXT, 
             skills TEXT, stipend TEXT, mode TEXT, hobbies TEXT, address TEXT)''')
        conn.commit()

init_db()

@app.route('/')
def home(): return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'password123':
        session['logged_in'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 401

@app.route('/choice')
def choice():
    if not session.get('logged_in'): return redirect('/')
    return render_template('choice.html')

@app.route('/student_login')
def student_login_page(): return render_template('student_login.html')

@app.route('/company_login')
def company_login_page(): return render_template('company_login.html')

@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    session['user_email'] = data['email']
    session['user_type'] = data['type']
    table = "student_profiles" if data['type'] == 'student' else "company_profiles"
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"INSERT OR IGNORE INTO {table} (email) VALUES (?)", (data['email'],))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session: return redirect('/')
    return render_template('index.html' if session['user_type'] == 'student' else 'company.html')

@app.route('/api/save_profile', methods=['POST'])
def save_profile():
    data = request.json
    u_email = session.get('user_email')
    u_type = session.get('user_type')
    table = "student_profiles" if u_type == 'student' else "company_profiles"
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''UPDATE {table} SET name=?, sector=?, role=?, skills=?, stipend=?, mode=?, hobbies=?, address=? WHERE email=?''', 
                       (data['name'], data['sector'], data['role'], data['skills'], data['stipend'], data['mode'], data['hobbies'], data['address'], u_email))
        conn.commit()
    threading.Thread(target=send_user_response_email, args=(u_email, u_type, data['name'])).start()
    return jsonify({"message": "Success"})

@app.route('/api/match')
def match():
    results = []
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        students = cursor.execute("SELECT * FROM student_profiles").fetchall()
        companies = cursor.execute("SELECT * FROM company_profiles").fetchall()
        for s in students:
            if not s[2]: continue
            s_skills = set(k.strip().lower() for k in str(s[5]).split(','))
            for c in companies:
                if not c[2]: continue
                c_skills = set(k.strip().lower() for k in str(c[5]).split(','))
                common = s_skills.intersection(c_skills)
                score = (len(common) / len(c_skills) * 70) if c_skills else 0
                if s[6] == c[6]: score += 15
                if s[7] == c[7]: score += 15
                if score > 0: results.append({"student": s[2], "company": c[2], "score": f"{min(int(score), 100)}%"})
    return jsonify(results)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__': app.run(debug=True)