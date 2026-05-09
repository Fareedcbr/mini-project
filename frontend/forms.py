from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Email

class StudentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Register')

class AssignmentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Create Assignment')

class SubmissionForm(FlaskForm):
    student_id = IntegerField('Student ID', validators=[DataRequired()])
    assignment_id = IntegerField('Assignment ID', validators=[DataRequired()])
    file = FileField('Upload File', validators=[DataRequired()])
    submit = SubmitField('Submit Assignment')
