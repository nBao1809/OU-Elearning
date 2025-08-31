from flasgger import Swagger
from flask import Flask
from urllib.parse import quote
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary
from flask_mail import Mail

app = Flask(__name__)
app.secret_key = 'KJHJF^(&*&&*OHH&*%&*TYUGJHG&(T&IUHKB'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ouedudb?charset=utf8mb4" % quote(
    '1234')
app.config['FLASK_ADMIN_SWATCH'] = 'cosmo'

db = SQLAlchemy(app=app)
login = LoginManager(app=app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'thkhangkunz2@gmail.com'
app.config['MAIL_PASSWORD'] = 'thwj hedg eoby tlzq'  # dùng App Password, không phải mật khẩu Gmail
app.config['MAIL_DEFAULT_SENDER'] = ('EduOnline', 'youremail@gmail.com')

mail = Mail(app)
cloudinary.config(
    cloud_name='dblzpkokm',
    api_key='629135199449497',
    api_secret='YanTDoC3S-bHO-i4I9S8G2hBevs',
    secure=True
)

from EduApp import admin
from EduApp import routes
