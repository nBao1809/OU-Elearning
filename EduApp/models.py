import hashlib
from datetime import datetime, timedelta, timezone
from EduApp import db
from flask_login import UserMixin
from enum import Enum

class UserRoleEnum(Enum):
    ADMIN = "ADMIN"
    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    avatar_url = db.Column(db.String(255),
                           default='https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg')
    role = db.Column(db.Enum(UserRoleEnum), default=UserRoleEnum.STUDENT, nullable=False)
    create_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True, nullable=False)

    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    reviews = db.relationship('Review', backref='reviewer', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)



class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Quan hệ với Course
    courses = db.relationship('Course', backref='category', lazy=True)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thumbnail_id = db.Column(db.String(255))
    level = db.Column(db.String(50))
    is_published = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=False)
    max_enrollment = db.Column(db.Integer)
    create_at = db.Column(db.DateTime, default=datetime.utcnow)


    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    modules = db.relationship('Module', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    reviews = db.relationship('Review', backref='course', lazy=True)
    comments = db.relationship('Comment', backref='course', lazy=True)


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    progress_percent = db.Column(db.Float, default=0.0)

    progress = db.relationship('Progress', backref='enrollment', lazy=True)


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    ordering = db.Column(db.Integer)

    lessons = db.relationship('Lesson', backref='module', lazy=True)


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    ordering = db.Column(db.Integer)
    content_type = db.Column(db.String(50))
    video_url = db.Column(db.String(255))
    file_url = db.Column(db.String(255))
    text_content = db.Column(db.Text)

    progress = db.relationship('Progress', backref='lesson', lazy=True)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollment.id'), nullable=False)
    complete_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(50))
    transaction_code = db.Column(db.String(100))
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('Enrollment', backref='payment', lazy=True)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.utcnow)
    update_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)
