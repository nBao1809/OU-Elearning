import hashlib

from flask import jsonify

from . import db
from models import User
def auth_user(username, password, role=None):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    u = User.query.filter(User.email.__eq__(username),
                          User.password.__eq__(password))

    if role:
        u = u.filter(User.user_role.__eq__(role))

    return u.first()


def get_user_by_id(id):
    return User.query.get(id)

def register_user(name, email, password, role="STUDENT", avatar_url=None):
    if User.query.filter_by(email=email).first():
        return None  # Email đã tồn tại
    hashed_password = str(hashlib.md5(password.encode('utf-8')).hexdigest())
    user = User(
        name=name,
        email=email,
        password=hashed_password,
        role=role,
        avatar_url=avatar_url
    )
    db.session.add(user)
    db.session.commit()
    return user