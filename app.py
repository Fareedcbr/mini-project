from importlib.resources import files
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import mysql.connector
import bcrypt

app = Flask(__name__)
app.secret_key = 'fareed'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# MySQL connection setup
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="rool",  # Replace with your password
        database="assignment_db"
    )
    cursor = db.cursor()
    print("Database connection successful!")
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

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        flash('You must be logged in to upload a file.', 'error')
        return redirect(url_for('login'))

    # Check if the user is a student
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'student':
        flash('Only students can upload assignments.', 'error')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file:
        filename = file.filename
        file_path = f"uploads/{filename}"
        file.save(file_path)

        # Save file details to the database
        cursor.execute("INSERT INTO files (user_id, filename, filepath) VALUES (%s, %s, %s)",
                       (session['user_id'], filename, file_path))
        db.commit()

        flash('File uploaded successfully!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
def download_file(filename):
    if 'user_id' not in session:
        flash('You must be logged in to download files.', 'error')
        return redirect(url_for('login'))

    # Fetch the file path from the database
    cursor.execute("SELECT filepath FROM files WHERE filename = %s AND user_id = %s", (filename, session['user_id']))
    result = cursor.fetchone()

    if result and result[0]:  # If a filepath exists in the database
        file_path = result[0]
        try:
            return send_from_directory(directory='.', path=file_path, as_attachment=True)
        except FileNotFoundError:
            flash('File not found.', 'error')
    else:
        flash('File not found in the database.', 'error')

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

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can view assignments.', 'error')
        return redirect(url_for('dashboard'))

    # Fetch assignments from the database
    cursor.execute("SELECT id, title, description, due_date FROM assignment")
    assignments = cursor.fetchall()

    return render_template('assignments.html', assignments=assignments)

@app.route('/assignments/add', methods=['GET', 'POST'])
def add_assignment():
    if 'user_id' not in session:
        flash('You must be logged in to add an assignment.', 'error')
        return redirect(url_for('login'))

    # Check if the user is an instructor
    cursor.execute("SELECT role FROM users WHERE id = %s", (session['user_id'],))
    role = cursor.fetchone()[0]
    if role != 'instructor':
        flash('Only instructors can add assignments.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form['due_date']
        course_id = request.form['course_id']
        cursor.execute("INSERT INTO assignment (title, description, due_date, course_id) VALUES (%s, %s, %s, %s)", (title, description, due_date, course_id))
        db.commit()
        flash('Assignment added successfully!', 'success')
        return redirect(url_for('view_assignments'))

    return render_template('add_assignment.html')

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

    # Fetch all students
    cursor.execute("SELECT users.id, users.username, students.course_id FROM users JOIN students ON users.id = students.user_id")
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

    # Fetch student details
    cursor.execute("""
        SELECT users.username, students.course_id
        FROM users
        JOIN students ON users.id = students.user_id
        WHERE students.id = %s
    """, (student_id,))
    student = cursor.fetchone()

    return render_template('view_student.html', student=student)

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
        cursor.execute("INSERT INTO assignment (title, description, due_date) VALUES (%s, %s, NOW())", (title, description))
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

    # Fetch all users and their data
    cursor.execute("""
        SELECT users.id, users.username, users.email, users.role, 
               COUNT(files.id) AS file_count, 
               COUNT(assignment.id) AS assignment_count
        FROM users
        LEFT JOIN files ON users.id = files.user_id
        LEFT JOIN assignment ON users.id = assignment.course_id
        GROUP BY users.id
    """)
    users_data = cursor.fetchall()

    return render_template('admin_dashboard.html', users_data=users_data)

if __name__ == '__main__':
    app.run(debug=True)
