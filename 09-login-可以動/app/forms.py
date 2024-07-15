from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, FileField
from wtforms.validators import DataRequired, EqualTo, Email, ValidationError
from app.models import Student, Loan
from sqlalchemy import and_


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ModifyForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Finish')


class ForgotForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Finish')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class AccountStatusForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(' Success')


class AddStudentForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    firstname = StringField('Firstname')
    lastname = StringField('Lastname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Add Student')

    def validate_username(self, username):
        if Student.query.filter_by(username=username.data).first():
            raise ValidationError('This username is already taken. Please choose another')

    def validate_email(self, email):
        if Student.query.filter_by(email=email.data).first():
            raise ValidationError('This email address is already registered. Please choose another')


class UploadStudentsForm(FlaskForm):
    student_file = FileField('New Students File', validators=[FileAllowed(['csv'])])
    submit = SubmitField('Upload')


class UploadUsersForm(FlaskForm):
    user_file = FileField('New Users File', validators=[FileAllowed(['csv'])])
    submit = SubmitField('Upload')


class UploadPicturesForm(FlaskForm):
    picture_file = FileField('New Users File', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Upload')


class UpdateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update Account')



class BorrowForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    device_id = StringField('Device ID', validators=[DataRequired()])
    submit = SubmitField('Borrow Device')

    def validate_student_id(self, student_id):
        if not student_id.data.isnumeric():
            raise ValidationError('This must be a positive integer')
        student = Student.query.get(student_id.data)
        if not (student):
            raise ValidationError('There is no student with this id in the system')
        if not student.active:
            raise ValidationError('This student has been dactivated and cannot borrow devices')
        if Loan.query.filter(
                (Loan.student_id == student_id.data)
                &
                # (Loan.returndatetime.is_(None))
                (Loan.returndatetime.is_(None))
        ).first():
            raise ValidationError('This student cannot borrow another item until the previous loan has been returned')

    def validate_device_id(self, device_id):
        if not device_id.data.isnumeric():
            raise ValidationError('This must be a positive integer')
        if Loan.query.filter(
                (Loan.device_id == device_id.data)
                &
                (Loan.returndatetime.is_(None))
        ).first():
            raise ValidationError('This device cannot be borrowed as it is currently on loan')



class ToggleActiveForm(FlaskForm):
    submit = SubmitField('Toggle Active')


class DamageForm(FlaskForm):
    submit = SubmitField('Damage Active')



class ListUsersForm(FlaskForm):
    submit = SubmitField('Active')



class SearchStudentForm(FlaskForm):
    lastname = StringField('Lastname', validators=[DataRequired()])
    submit = SubmitField('Search')


class Fine(FlaskForm):
    student_id = StringField("Student_id", validators=[DataRequired()])
    device_id = StringField("Device_id", validators=[DataRequired()])
    submit = SubmitField("Check")