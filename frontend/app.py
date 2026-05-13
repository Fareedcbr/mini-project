from importlib.resources import files
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import mysql.connector
import bcrypt
import os

print("Current working directory:", os.getcwd())
print("Templates folder absolute path:", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
print("Files in templates folder:", os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')))

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
)
app.secret_key = os.environ.get('SECRET_KEY', 'fareed')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))

# MySQL connection setup
try:
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', 'root')
    db_name = os.environ.get('DB_NAME', 'assignment_db')
    db_port = int(os.environ.get('DB_PORT', '3306'))

    db = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        port=db_port,
        ssl_disabled=True
    )

    cursor = db.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN credits INT DEFAULT 0")
    except mysql.connector.Error:
        pass
    try:
        cursor.execute("ALTER TABLE assignment ADD COLUMN instructor_id INT")
    except mysql.connector.Error:
        pass
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            assignment_id INT NOT NULL,
            score FLOAT,
            comments TEXT,
            UNIQUE KEY student_assignment (student_id, assignment_id)
        )
    """)
    db.commit()
    print("Database connection successful and grades table ensured!")
except mysql.connector.Error as err:
    print(f"Error: {err}")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username') 
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        course_id = request.form.get('course_id') if role == 'student' else None

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Check if the email or username is already registered
        cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email or username is already registered. Please login.', 'error')
            return redirect(url_for('login'))

        # Insert the new user into the users table
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                       (username, email, hashed_password.decode('utf-8'), role))
        db.commit()

        # Get the user ID of the newly created user
        user_id = cursor.lastrowid

        # Insert into students or instructors table based on the role
        if role == 'student':
            cursor.execute("INSERT INTO students (user_id, course_id) VALUES (%s, %s)", (user_id, course_id))
        elif role == 'instructor':
            cursor.execute("INSERT INTO instructors (user_id, department) VALUES (%s, %s)", (user_id, 'General'))
            # Assign the instructor to the selected course
            cursor.execute("INSERT INTO courses (name, instructor_id) VALUES (%s, %s)", ('New Course', user_id))
        db.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    # Fetch all courses for the dropdown
    cursor.execute("SELECT id, name FROM courses")
    courses = cursor.fetchall()

    return render_template('register.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']  # This can be either username or email
        password = request.form['password']

        # Check if the user exists in the users table
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (identifier, identifier))
        user = cursor.fetchone()

        print(f"User fetched from database: {user}")  # Debugging
        print(f"Entered password: {password}")  # Debugging

        if user:
            print(f"Stored hashed password: {user[3]}")  # Debugging
            if bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):  # Assuming the 4th column is the hashed password
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[4]  # Assuming the 5th column is the role
                flash('Login successful!', 'success')
                if user[4] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('dashboard'))
            else:
                print("Password mismatch")  # Debugging
        else:
            print("User not found")  # Debugging

        flash('Invalid username/email or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('You must be logged in to access the dashboard.', 'error')
        return redirect(url_for('login'))

    # Check the user's role
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]

    if role == 'student':
        # Fetch files submitted by the student
        cursor.execute("SELECT id, filename FROM files WHERE user_id = %s", (session['user_id'],))
        files = cursor.fetchall()

        # Fetch assignments for the student's course
        cursor.execute("""
            SELECT assignment.id, assignment.title, assignment.description, assignment.due_date
            FROM assignment
            JOIN students ON assignment.course_id = students.course_id
            WHERE students.user_id = %s
        """, (session['user_id'],))
        assignments = cursor.fetchall()

        return render_template('dashboard.html', files=files, students=None, assignments=assignments)

    elif role == 'instructor':
        # Fetch students and assignments for the instructor
        cursor.execute("""
            SELECT users.username, students.course_id
            FROM users
            JOIN students ON users.id = students.user_id
        """)
        students = cursor.fetchall()

        cursor.execute("SELECT id, title, description, due_date FROM assignment")
        assignments = cursor.fetchall()

        return render_template('dashboard.html', files=None, students=students, assignments=assignments)

    else:
        flash('Invalid role. Please contact the administrator.', 'error')
        return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('You must be logged in to upload a file.', 'error')
        return redirect(url_for('login'))

    # Only students can upload
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'student':
        flash('Only students can upload assignments.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        file = request.files['file']
        assignment_id = request.form.get('assignment_id')
        file_id = request.form.get('file_id')

        if file and assignment_id:
            filename = file.filename
            upload_folder = UPLOAD_FOLDER
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            if file_id:
                cursor.execute(
                    "UPDATE files SET filename = %s, filepath = %s WHERE id = %s AND user_id = %s",
                    (filename, file_path, file_id, session['user_id'])
                )
                flash('File updated successfully!', 'success')
            else:
                cursor.execute(
                    "INSERT INTO files (user_id, filename, filepath, assignment_id) VALUES (%s, %s, %s, %s)",
                    (session['user_id'], filename, file_path, assignment_id)
                )
                # Award credit to the instructor
                cursor.execute("SELECT instructor_id FROM assignment WHERE id = %s", (assignment_id,))
                instructor_id = cursor.fetchone()[0]
                cursor.execute("UPDATE users SET credits = credits + 1 WHERE id = %s", (instructor_id,))
                flash('File uploaded successfully!', 'success')
            db.commit()
        else:
            flash('Please select a file and an assignment.', 'error')

        return redirect(url_for('upload'))

    cursor.execute("""
        SELECT a.id, a.title, a.description, a.due_date,
               f.id AS file_id, f.filename, g.score
        FROM assignment a
        JOIN students s ON a.course_id = s.course_id
        LEFT JOIN files f ON f.assignment_id = a.id AND f.user_id = %s
        LEFT JOIN grades g ON g.assignment_id = a.id AND g.student_id = (
            SELECT id FROM students WHERE user_id = %s
        )
        WHERE s.user_id = %s
        GROUP BY a.id, f.id, f.filename, g.score
    """, (session['user_id'], session['user_id'], session['user_id']))
    assignments = cursor.fetchall()

    cursor.execute("SELECT files.id, files.filename, files.assignment_id, assignment.title FROM files JOIN assignment ON files.assignment_id = assignment.id WHERE files.user_id = %s", (session['user_id'],))
    submitted_files = cursor.fetchall()

    cursor.execute("SELECT grades.id, grades.assignment_id, grades.score, grades.comments, assignment.title FROM grades JOIN assignment ON grades.assignment_id = assignment.id WHERE grades.student_id = (SELECT id FROM students WHERE user_id = %s)", (session['user_id'],))
    grades = cursor.fetchall()

    return render_template('upload.html', assignments=assignments, submitted_files=submitted_files, grades=grades)

@app.route('/upload/<int:file_id>/edit', methods=['GET', 'POST'])
def edit_upload(file_id):
    if 'user_id' not in session:
        flash('You must be logged in to edit a file.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'student':
        flash('Only students can edit uploads.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT id, filename, assignment_id FROM files WHERE id = %s AND user_id = %s", (file_id, session['user_id']))
    file_record = cursor.fetchone()
    if not file_record:
        flash('Upload not found.', 'error')
        return redirect(url_for('upload'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            upload_folder = UPLOAD_FOLDER
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            cursor.execute("UPDATE files SET filename = %s, filepath = %s WHERE id = %s", (filename, file_path, file_id))
            db.commit()
            flash('Upload updated successfully.', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Please select a file.', 'error')

    return render_template('edit_upload.html', file_record=file_record)

@app.route('/download/<filename>')
def download_file(filename):
    if 'user_id' not in session:
        flash('You must be logged in to download files.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT filepath FROM files WHERE filename = %s AND user_id = %s", (filename, session['user_id']))
    result = cursor.fetchone()

    if result and result[0]:
        file_path = result[0]
        try:
            return send_from_directory(directory=os.path.dirname(file_path), path=os.path.basename(file_path), as_attachment=True)
        except FileNotFoundError:
            flash('File not found.', 'error')
    else:
        flash('File not found in the database.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/view_upload/<int:file_id>')
def view_upload(file_id):
    if 'user_id' not in session:
        flash('You must be logged in to view uploads.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT filepath, user_id FROM files WHERE id = %s", (file_id,))
    result = cursor.fetchone()
    if not result:
        flash('File not found.', 'error')
        return redirect(url_for('dashboard'))

    file_path, file_owner = result
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role == 'student' and session['user_id'] != file_owner:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    try:
        return send_from_directory(directory=os.path.dirname(file_path), path=os.path.basename(file_path), as_attachment=False)
    except FileNotFoundError:
        flash('File not found.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/home')
def home():
    return render_template('home.html')  # Create a 'home.html' template in the 'templates' folder

@app.route('/')
def index():
    if 'user_id' in session:
        cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
        role = cursor.fetchone()[0]
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/terms')
def terms():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms of Service</title>
    </head>
    <body>
        <h1>Terms of Service</h1>
        <p>These are the terms of service for the Online Assignment Submission Management System.</p>
        <a href="/">Back to Home</a>
    </body>
    </html>
    '''

@app.route('/privacy')
def privacy():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy</title>
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p>This is the privacy policy for the Online Assignment Submission Management System.</p>
        <a href="/">Back to Home</a>
    </body>
    </html>
    '''

@app.route('/students')
def view_students():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    return render_template('students.html', students=students)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        course_id = request.form['course_id']
        cursor.execute("INSERT INTO students (name, email, password, course_id) VALUES (%s, %s, %s, %s)", (name, email, password, course_id))
        db.commit()
        flash('Student added successfully!', 'success')
        return redirect(url_for('view_students'))
    return render_template('add_student.html')

@app.route('/assignments')
def view_assignments():
    if 'user_id' not in session:
        flash('You must be logged in to view assignments.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]

    if role == 'instructor':
        cursor.execute("SELECT id, title, description, due_date FROM assignment")
        assignments = cursor.fetchall()
    elif role == 'student':
        # Fetch assignments for the student's course
        cursor.execute("""
            SELECT assignment.id, assignment.title, assignment.description, assignment.due_date
            FROM assignment
            JOIN students ON assignment.course_id = students.course_id
            WHERE students.user_id = %s
        """, (session['user_id'],))
        assignments = cursor.fetchall()
    else:
        flash('Only instructors and students can view assignments.', 'error')
        return redirect(url_for('dashboard'))

    return render_template('assignments.html', assignments=assignments, role=role)

@app.route('/assignments/add', methods=['GET', 'POST'])
def add_assignment():
    if 'user_id' not in session:
        flash('You must be logged in to add an assignment.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can add assignments.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT id, name FROM courses WHERE instructor_id = %s", (session['user_id'],))
    courses = cursor.fetchall()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form['due_date']
        course_id = request.form['course_id']
        cursor.execute("INSERT INTO assignment (title, description, due_date, course_id, instructor_id) VALUES (%s, %s, %s, %s, %s)", (title, description, due_date, course_id, session['user_id']))
        db.commit()
        flash('Assignment added successfully!', 'success')
        return redirect(url_for('view_assignments'))

    return render_template('add_assignment.html', courses=courses)

@app.route('/assignments/edit/<int:assignment_id>', methods=['GET', 'POST'])
def edit_assignment(assignment_id):
    if 'user_id' not in session:
        flash('You must be logged in to edit an assignment.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can edit assignments.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT id, title, description, due_date, course_id FROM assignment WHERE id = %s", (assignment_id,))
    assignment = cursor.fetchone()
    if not assignment:
        flash('Assignment not found.', 'error')
        return redirect(url_for('view_assignments'))

    cursor.execute("SELECT id, name FROM courses WHERE instructor_id = %s", (session['user_id'],))
    courses = cursor.fetchall()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form['due_date']
        course_id = request.form['course_id']
        cursor.execute("UPDATE assignment SET title = %s, description = %s, due_date = %s, course_id = %s WHERE id = %s", (title, description, due_date, course_id, assignment_id))
        db.commit()
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('view_assignments'))

    return render_template('edit_assignment.html', assignment=assignment, courses=courses)

@app.route('/assignments/delete/<int:assignment_id>')
def delete_assignment(assignment_id):
    if 'user_id' not in session:
        flash('You must be logged in to delete an assignment.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can delete assignments.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("DELETE FROM assignment WHERE id = %s", (assignment_id,))
    db.commit()
    flash('Assignment deleted successfully.', 'success')
    return redirect(url_for('view_assignments'))

@app.route('/manage_students')
def manage_students():
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT s.id, u.username, u.email,
               COUNT(DISTINCT f.assignment_id) AS submitted_count,
               COALESCE(GROUP_CONCAT(DISTINCT a.title ORDER BY a.title SEPARATOR ', '), 'None') AS submitted_assignments,
               COALESCE(g.avg_score, 'Not graded') AS avg_score
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN files f ON f.user_id = u.id
        LEFT JOIN assignment a ON f.assignment_id = a.id
        LEFT JOIN (
            SELECT student_id, ROUND(AVG(score),1) AS avg_score
            FROM grades
            GROUP BY student_id
        ) g ON g.student_id = s.id
        GROUP BY s.id, u.username, u.email, g.avg_score
    """)
    students = cursor.fetchall()

    return render_template('manage_students.html', students=students)

@app.route('/students/<int:student_id>')
def view_student(student_id: int):
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT users.username, users.email, students.course_id
        FROM students
        JOIN users ON students.user_id = users.id
        WHERE students.id = %s
    """, (student_id,))
    student = cursor.fetchone()

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('manage_students'))

    cursor.execute("""
        SELECT a.id, a.title, a.description, a.due_date, COALESCE(g.score, 'Not graded') AS score
        FROM assignment a
        LEFT JOIN grades g ON g.assignment_id = a.id AND g.student_id = %s
        WHERE a.course_id = %s
    """, (student_id, student[2]))
    student_assignments = cursor.fetchall()

    return render_template('view_student.html', student=student, student_assignments=student_assignments)

@app.route('/students/<int:student_id>/grade', methods=['GET', 'POST'])
def grade_student(student_id: int):
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT users.username, users.email
        FROM students
        JOIN users ON students.user_id = users.id
        WHERE students.id = %s
    """, (student_id,))
    student = cursor.fetchone()
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('manage_students'))

    if request.method == 'POST':
        assignment_id = request.form['assignment_id']
        score = request.form['score']
        comments = request.form.get('comments', '')
        cursor.execute("""
            INSERT INTO grades (student_id, assignment_id, score, comments)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score), comments = VALUES(comments)
        """, (student_id, assignment_id, score, comments))
        db.commit()
        flash('Grade saved successfully.', 'success')
        return redirect(url_for('grade_student', student_id=student_id))

    cursor.execute("""
        SELECT a.id, a.title, a.description, a.due_date, g.score, g.comments, f.id AS file_id
        FROM assignment a
        LEFT JOIN grades g ON g.assignment_id = a.id AND g.student_id = %s
        LEFT JOIN students s ON s.id = %s
        LEFT JOIN files f ON f.assignment_id = a.id AND f.user_id = s.user_id
        WHERE a.course_id = s.course_id
    """, (student_id, student_id))
    assignments = cursor.fetchall()

    cursor.execute("""
        SELECT f.id, f.filename, COALESCE(a.title, 'Unknown Assignment') AS title, f.assignment_id
        FROM files f
        LEFT JOIN assignment a ON f.assignment_id = a.id
        WHERE f.user_id = (
            SELECT user_id FROM students WHERE id = %s
        )
        ORDER BY f.assignment_id
    """, (student_id,))
    student_files = cursor.fetchall()

    return render_template('grade_student.html', student=student, assignments=assignments, student_id=student_id, student_files=student_files)

@app.route('/grades')
def grade_overview():
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT s.id, u.username, u.email, s.course_id, a.title, a.due_date, f.filename, g.score, g.comments
        FROM grades g
        JOIN students s ON g.student_id = s.id
        JOIN users u ON s.user_id = u.id
        JOIN assignment a ON g.assignment_id = a.id
        LEFT JOIN files f ON f.assignment_id = a.id AND f.user_id = u.id
        ORDER BY s.id, a.id
    """)
    grade_rows = cursor.fetchall()

    return render_template('grade_overview.html', grade_rows=grade_rows)

@app.route('/assignment/<int:assignment_id>/submissions')
def view_submissions(assignment_id):
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT title FROM assignment WHERE id = %s", (assignment_id,))
    assignment = cursor.fetchone()
    if not assignment:
        flash('Assignment not found.', 'error')
        return redirect(url_for('view_assignments'))

    cursor.execute("""
        SELECT s.id, u.username, u.email, f.filename, f.id AS file_id, g.score, g.comments
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN files f ON f.assignment_id = %s AND f.user_id = u.id
        LEFT JOIN grades g ON g.assignment_id = %s AND g.student_id = s.id
        WHERE s.course_id = (SELECT course_id FROM assignment WHERE id = %s)
        ORDER BY s.id
    """, (assignment_id, assignment_id, assignment_id))
    submissions = cursor.fetchall()

    return render_template('view_submissions.html', assignment=assignment, submissions=submissions, assignment_id=assignment_id)

@app.route('/students/delete/<int:student_id>')
def delete_student(student_id):
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Delete the student
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    db.commit()

    flash('Student deleted successfully.', 'success')
    return redirect(url_for('manage_students'))

@app.route('/assign_form', methods=['GET', 'POST'])
def assign_form():
    if 'user_id' not in session:
        flash('You must be logged in to submit an assignment.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can submit assignments.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        # Insert the assignment into the database
        cursor.execute("INSERT INTO assignment (title, description, due_date, instructor_id) VALUES (%s, %s, NOW(), %s)", (title, description, session['user_id']))
        db.commit()

        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('view_assignments'))

    return render_template('assign_form.html')

@app.route('/some_route')
def some_route():
    return render_template('dashboard.html', files=files, students=None, assignments=None)  # Correct

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        flash('You must be logged in to access the admin dashboard.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'admin':
        flash('Only admins can access the admin dashboard.', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT id, username, email, role FROM users")
    users_data = cursor.fetchall()

    cursor.execute("""
        SELECT s.id, u.username, u.email, COUNT(DISTINCT f.id) AS uploaded_count,
               ROUND(AVG(g.score), 1) AS avg_grade
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN files f ON f.user_id = u.id
        LEFT JOIN grades g ON g.student_id = s.id
        GROUP BY s.id, u.username, u.email
    """)
    student_stats = cursor.fetchall()

    cursor.execute("""
        UPDATE assignment a
        JOIN courses c ON a.course_id = c.id
        SET a.instructor_id = c.instructor_id
        WHERE a.instructor_id IS NULL AND c.instructor_id IS NOT NULL
    """)
    db.commit()

    cursor.execute("""
        SELECT id, title, course_id
        FROM assignment
        WHERE instructor_id IS NULL
        ORDER BY id
    """)
    incomplete_assignments = cursor.fetchall()

    cursor.execute("""
        SELECT u.id, u.username, u.email, COUNT(DISTINCT a.id) AS assignments_created, u.credits
        FROM users u
        LEFT JOIN assignment a ON a.instructor_id = u.id
        WHERE u.role = 'instructor'
        GROUP BY u.id, u.username, u.email, u.credits
    """)
    instructor_stats = cursor.fetchall()

    return render_template(
        'admin_dashboard.html',
        users_data=users_data,
        student_stats=student_stats,
        instructor_stats=instructor_stats,
        incomplete_assignments=incomplete_assignments,
    )

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
