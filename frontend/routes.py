from flask import Flask, render_template, redirect, url_for, request
from models import db, Student, Assignment, Submission
from forms import StudentForm, AssignmentForm, SubmissionForm

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

@app.route('/students', methods=['GET', 'POST'])
def students():
    form = StudentForm()
    if form.validate_on_submit():
        new_student = Student(name=form.name.data, email=form.email.data)
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('students'))
    students = Student.query.all()
    return render_template('students.html', form=form, students=students)

@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    form = AssignmentForm()
    if form.validate_on_submit():
        new_assignment = Assignment(title=form.title.data, description=form.description.data)
        db.session.add(new_assignment)
        db.session.commit()
        return redirect(url_for('assignments'))
    assignments = Assignment.query.all()
    return render_template('assignments.html', form=form, assignments=assignments)

@app.route('/submissions', methods=['GET', 'POST'])
def submissions():
    form = SubmissionForm()
    if form.validate_on_submit():
        new_submission = Submission(student_id=form.student_id.data, assignment_id=form.assignment_id.data, file_path="uploads/" + form.file.data.filename)
        db.session.add(new_submission)
        db.session.commit()
        return redirect(url_for('submissions'))
    submissions = Submission.query.all()
    return render_template('submissions.html', form=form, submissions=submissions)

if __name__ == '__main__':
    app.run(debug=True)
