from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    # UserMixin 是一個由 Flask - Login 提供的輔助類別，目的是為了簡化 Flask
    # 應用中用戶認證處理的工作。這個類別提供了幾個預設的方法，
    # 這些方法對於用戶會話管理（如登入和登出）至關重要，並且在許多用戶認證的流程中通常會用到。
    # 當你的用戶模型繼承了 UserMixin類，你的模型就會自動擁有以下幾個方法：
    # is_authenticated: 這個方法如果用戶已經被驗證，則返回
    # True，通常用於確定當前用戶是否已經登入。
    # is_active: 如果這個賬戶目前是活躍的，則返回
    # True，用來處理賬戶例如是否被封禁。
    # is_anonymous: 如果當前用戶是匿名的，則返回
    # True，通常用於檢查當前用戶是否是已登錄的用戶。
    # get_id: 返回用戶的唯一識別符，這是用於支持用戶會話的重要方法。這個識別符必須是一個能轉換成 str 類型的數據。
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True, index=True)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # image_file = db.Column(db.String(120), nullable=False, default='default.jpg')
    active = db.Column(db.Boolean, nullable=False, default=True)
    image_file = db.Column(db.String(120), nullable=False, default='default.jpg')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)
        # salt_length 就是在 我們的 password , ex : ABC123 , 再增加 長度為 32 的隨機的字串 串在我們的 password
        # 然後再透過 generate_password_hash 合併成一個 新的 hash values ，這樣可以提高安全性

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Since we named our primary key "user_id", instead of "id", we have to override the
    # get_id() from the UserMixin to return the id, and it has to be returned as a string
    def get_id(self):
        return str(self.user_id)

    def __repr__(self):
        return f"user(id='{self.user_id}', '{self.username}', '{self.email}')"

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
#這個 id 主鍵是唯一的，用來標識每一行（即每一筆記錄）的身份。
# 如果在你的資料庫中，表格使用student_id作為主鍵，那麼在進行查詢和操作時，應當以student_id來標識和存取個別學生的資料。
# 會變成底下這樣
# @login.user_loader
# def load_user(student_id):
#     return User.query.get(int(student_id))


class Student(db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True, index=True)
    firstname = db.Column(db.String(32))
    lastname = db.Column(db.String(32), nullable=False, index=True)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    loans = db.relationship('Loan', backref='student', lazy='dynamic')

    def __repr__(self):
        return f"student(id='{self.student_id}', '{self.username}', '{self.lastname}', '{self.firstname}' , '{self.email}', active='{self.active}')"


class Loan(db.Model):
    __tablename__ = 'loans'
    loan_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    device_id = db.Column(db.Integer, nullable=False)
    borrowdatetime = db.Column(db.DateTime, nullable=False)
    returndatetime = db.Column(db.DateTime, nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    damage = db.Column(db.Boolean, nullable=False , default=False)
    def __repr__(self):
        return f"loan(loan_id='{self.loan_id}', device_id='{self.device_id}', borrowdatetime='{self.borrowdatetime}' , returndatetime='{self.returndatetime}', '{self.student}')"


