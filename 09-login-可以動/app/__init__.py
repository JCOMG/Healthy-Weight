import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] =  b'WR#&f&+%78er0we=%799eww+#7^90-;s'
login = LoginManager(app)
login.login_view = 'login'
# 假設你開了一家電影院，而這家電影院有一個VIP房間，只有持有VIP卡的客人才能進入。
# 在這裡，VIP房間就像是你的網站上那些需要「登入」後才能訪問的頁面。
# LoginManager就像是電影院的管理系統，負責確認哪些客人有資格進入VIP房間。
# login = LoginManager(app)：這行代碼創建了一個新的LoginManager物件，並且告訴它，我們的電影院（即Flask app應用）需要它來管理我們的VIP入場規則。

# login.login_view = 'login'
# 這行代碼進一步指定，當一位想進入VIP房間的客人還沒有展示他們的VIP卡（即未登入狀態）時，應該被引導到哪裡去獲得VIP卡（即用戶登入頁面的路由）。
# 在這裡，'login'就是那個獲取VIP卡的過程的地方，也就是我們網站上的登入頁面。
# 這裡的 'login' 是指向你定義的 login() 函數的路由。這段代碼中的 @app.route('/login', methods=['GET', 'POST'])


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'data', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
# app.config['MAX_CONTENT_LENGTH'] = 8


from app import views
from app.models import *

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Student=Student, Loan=Loan, datetime=datetime, LoginManager=LoginManager)
