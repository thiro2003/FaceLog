import os
from io import BytesIO
from datetime import  datetime 
import csv
from io import StringIO
from flask import send_file
import cv2
import face_recognition
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
import mysql.connector
import numpy as np
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import pytz
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Thiro')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Aiven MySQL Database Configuration
DB_HOST = os.environ.get('DB_HOST', 'mysql-37bfb3f4-rohitsul1112003-1aa2.k.aivencloud.com')
DB_PORT = int(os.environ.get('DB_PORT', 16054))
DB_USER = os.environ.get('DB_USER', 'avnadmin')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'uxzlYXSgDogWzsKdk')
DB_NAME = os.environ.get('DB_NAME', 'FaceLog')


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_disabled=False,
    )




# ---------------- MAIN LANDING PAGE ----------------
@app.route('/')
@app.route('/facelog_home')
def FaceLog_home():
    """Default landing page for the FaceLog application."""
    return render_template("FaceLog_home.html")


# ---------------- ADMIN ROUTES ----------------
@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if 'user' in session:
            return redirect(url_for('admin_dashboard'))
            
    if request.method == 'POST':
            full_name = request.form.get('fullname').strip()
            email = request.form.get('email').strip().lower()
            password = request.form.get('password')
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(
                'SELECT Admin_id, full_name, email, password FROM Admin WHERE email = %s',
                (email,),
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()
    
            if user:
                if (
                    check_password_hash(user['password'], password)
                    and user['full_name'].strip() == full_name
                ):
                    session['user'] = user['full_name']
                    flash('Login Successful ✨👍', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Incorrect full name or password.', 'danger')
            else:
                flash('User Does Not exist, Please Signup ❌🚫', 'danger')
    
    return render_template('Admin/admin_login.html')


@app.route('/admin_registration',methods=['GET','POST'])
def admin_registration():
    if request.method == 'POST':
            full_name = request.form.get('fullname')
            email = request.form.get('email')
            password = request.form.get('password')
            hashed_password = generate_password_hash(password)
    
            conn = get_db_connection()
            cursor = conn.cursor(buffered=True)
            cursor.execute(
                'INSERT INTO Admin (full_name, email, password) VALUES (%s, %s, %s)',
                (full_name, email, hashed_password,),
            )
            conn.commit()
            cursor.close()
            conn.close()
    
            flash('Registration Successful ✨👍', 'success')
            return redirect(url_for('admin_login'))
    return render_template('Admin/admin_registration.html')


@app.route('/admin_home')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('admin_login'))

    admin_name = session['user']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT user_id, username, date_time, attendance
        FROM Attendance
        ORDER BY date_time DESC
    """)

    attendances = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'Admin/admin_home.html',
        admin_name=admin_name,
        attendances=attendances
    )
  
@app.route('/remove_students') 
def remove_students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM Student')

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'Admin/admin_manage_students.html',
        students=students
    )   
# ---------------- CSV EXPORT --------------------------------
@app.route('/export_attendance')
def export_attendance():

    if 'user' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT user_id, username, date_time, attendance
        FROM Attendance
        ORDER BY date_time DESC
    """)

    attendances = cursor.fetchall()

    cursor.close()
    conn.close()

    # Create CSV in memory
    output = StringIO()

    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        'Student ID',
        'Student Name',
        'Date & Time',
        'Attendance'
    ])

    # CSV Data
    for attendance in attendances:
        writer.writerow([
            attendance['user_id'],
            attendance['username'],
            attendance['date_time'],
            'Present' if attendance['attendance'] else 'Absent'
        ])

    # Convert CSV text to bytes
    csv_data = output.getvalue().encode('utf-8')

    # Create binary file
    csv_file = BytesIO(csv_data)
    csv_file.seek(0)

    return send_file(
        csv_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='student_attendance.csv'
    )

@app.route("/export_students_record")
def export_students_record():
    if 'user' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT id, full_name, email, password,image,face_encoding
        FROM Student
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    # Create CSV in memory
    output = StringIO()

    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        'id',
        'full_name',
        'email',
        'password',
        'profile',
        'face_encoding'
    ])

    # CSV Data
    for student in students:
        writer.writerow([
            student['id'],
            student['full_name'],
            student['email'],
            student['password'],
            student['image'],
            student['face_encoding'],
        ])

    # Convert CSV text to bytes
    csv_data = output.getvalue().encode('utf-8')

    # Create binary file
    csv_file = BytesIO(csv_data)
    csv_file.seek(0)

    return send_file(
        csv_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='students_records.csv'
    )
# ---------------- STUDENT & ATTENDANCE ROUTES ----------------
@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'user' in session:
         conn = get_db_connection()
         cursor = conn.cursor(buffered=True)

         cursor.execute(
              'SELECT id FROM Student WHERE full_name = %s',
              (session['user'],)
         )

         user_exists = cursor.fetchone()

         cursor.close()
         conn.close()

         if user_exists:
            return redirect(url_for('student_attendance'))
        
    if request.method == 'POST':
        full_name = request.form.get('fullname').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(
            'SELECT id, full_name, email, password FROM Student WHERE email = %s',
            (email,),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if (
                check_password_hash(user['password'], password)
                and user['full_name'].strip() == full_name
            ):
                session['user'] = user['full_name']
                flash('Login Successful ✨👍', 'success')
                return redirect(url_for('student_attendance'))
            else:
                flash('Incorrect full name or password.', 'danger')
        else:
            flash('User Does Not exist, Please Signup ❌🚫', 'danger')

    return render_template('Student/student_login.html')


@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        full_name = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        image_file = request.files['image']

        img = face_recognition.load_image_file(image_file)
        encodings = face_recognition.face_encodings(img)

        if not encodings:
            flash(
                'No face detected. Please upload a clear face image ❌🚫', 'danger'
            )
            return redirect(url_for('student_register'))

        face_encoding = encodings[0]
        face_encoding_blob = face_encoding.tobytes()
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        cursor.execute(
            'INSERT INTO Student (full_name, email, password, image,'
            ' face_encoding) VALUES (%s, %s, %s, %s, %s)',
            (full_name, email, hashed_password, None, face_encoding_blob),
        )

        conn.commit()
        cursor.close()
        conn.close()

        

        flash('Registration Successful ✨👍', 'success')
        
        return redirect(url_for('admin_dashboard'))

    return render_template('Student/student_registration.html')


@app.route('/student_attendance', methods=['POST', 'GET'])
def student_attendance():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute(
        'SELECT user_id, username, date_time, attendance FROM Attendance WHERE'
        ' username = %s',
        (user,),
    )
    user_attendance = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'Student/student_home.html', user=user, attendances=user_attendance
    )


@app.route('/mark_attendance')
def mark_attendance():
    if 'user' not in session:
        flash('Please login first ❌🚫', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute(
        'SELECT id, full_name, email, password, image, face_encoding FROM Student'
    )
    users = cursor.fetchall()

    known_encodings = []
    known_user_ids = []
    known_usernames = []

    for user in users:
        if user['face_encoding'] is not None:
            enc_bytes = user['face_encoding']
            if isinstance(enc_bytes, bytes):
                face_enc = np.frombuffer(enc_bytes, dtype=np.float64).reshape(-1)
            else:
                face_enc = user['face_encoding']
            known_encodings.append(face_enc)
            known_user_ids.append(user['id'])
            known_usernames.append(user['full_name'])

    if len(known_encodings) == 0:
        cursor.close()
        conn.close()
        flash('No registered faces found. Please register first ❌🚫', 'danger')
        return redirect(url_for('student_register'))

    video = cv2.VideoCapture(0, cv2.CAP_ANY)

    if not video.isOpened():
        cursor.close()
        conn.close()
        flash(
            'Could not open webcam. Check Windows Camera Privacy Settings or close'
            ' other camera apps ❌🚫',
            'danger',
        )
        return redirect(url_for('hostudent_attendanceme'))

    marked = False
    attendance_message = None
    attendance_category = None

    while True:
        ret, frame = video.read()
        if not ret:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations
        )

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                known_encodings, face_encoding, tolerance=0.6
            )
            face_distances = face_recognition.face_distance(
                known_encodings, face_encoding
            )

            if len(face_distances) == 0:
                continue

            best_match_index = np.argmin(face_distances)
            print(f'Best match distance: {face_distances[best_match_index]}')

            if face_distances[best_match_index] < 0.6:
                user_id = known_user_ids[best_match_index]
                username = known_usernames[best_match_index]

                india_timezone = pytz.timezone('Asia/Kolkata')

                today = datetime.now(india_timezone).date()
                
                cursor.execute(
                    'SELECT * FROM Attendance WHERE user_id = %s AND DATE(date_time) ='
                    ' %s',
                    (user_id, today),
                )
                existing = cursor.fetchone()

                if existing:
                    attendance_message = 'Attendance Already Marked For Today ✨👍'
                    attendance_category = 'info'
                else:
                    now_dt = datetime.now(india_timezone)
                    cursor.execute(
                        'INSERT INTO Attendance (user_id, username, date_time,'
                        ' attendance) VALUES (%s, %s, %s, %s)',
                        (user_id, username, now_dt, True),
                    )
                    conn.commit()
                    attendance_message = 'Attendance marked successfully ✨👍'
                    attendance_category = 'success'

                marked = True
                break

        cv2.imshow('Mark Attendance - Press Q to exit', frame)

        if marked or cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()
    cursor.close()
    conn.close()

    if not marked:
        flash('Face not recognized ❌🚫', 'danger')
    else:
        flash(attendance_message, attendance_category)

    return redirect(url_for('student_attendance'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Log out Successful ✨👍', 'success')
    return redirect(url_for('FaceLog_home'))

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute(
        'DELETE FROM Student WHERE id = %s',
        (student_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash('Student deleted successfully.', 'success')

    return redirect(url_for('admin_dashboard'))
    

if __name__ == '__main__':
    app.run(debug=True)