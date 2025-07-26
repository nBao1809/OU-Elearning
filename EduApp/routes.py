import hashlib
from datetime import date
from enum import Enum
from flask_login import current_user
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required
from EduApp import app, dao, login, db
import cloudinary
import cloudinary.uploader
from models import User, Course, Review,Comment,Enrollment,Payment
from datetime import datetime


@login.user_loader
def get_user(user_id):
    return dao.get_user_by_id(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        if not email or not password:
            flash("Vui lòng nhập đầy đủ email và mật khẩu.", 'info')
            return render_template('login.html')

        hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()
        user = User.query.filter_by(email=email, password=hashed_password).first()

        if user:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Email hoặc mật khẩu không đúng!', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@app.route('/cart')
def cart():
    course_id = request.args.get('course_id')
    course = Course.query.get(course_id)
    instructor = User.query.get(course.instructor_id) if course and course.instructor_id else None

    if course_id:
        try:
            course_id = int(course_id)
            # Lấy thông tin khóa học từ database
            course = Course.query.get(course_id)
        except (ValueError, TypeError):
            flash('ID khóa học không hợp lệ', 'error')

    return render_template('cart.html', course=course,instructor=instructor)

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True,

        })
    return jsonify({'logged_in': False}), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'STUDENT')

        # Kiểm tra mật khẩu khớp
        if password != confirm_password:
            flash('Mật khẩu không khớp.', 'danger')
            return redirect(url_for('register'))

        avatar_url = None
        avatar_file = request.files.get('avatar_file')

        if avatar_file and avatar_file.filename != '':
            upload_result = cloudinary.uploader.upload(avatar_file)
            avatar_url = upload_result.get('secure_url')

        user = dao.register_user(
            name=name,
            email=email,
            password=password,
            role=role,
            avatar_url=avatar_url  # có thể None nếu không upload
        )

        if user:
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email đã tồn tại!', 'danger')

    return render_template('register.html')

@app.route('/api/courses')
def get_courses():
    if current_user.is_authenticated:
        # Nếu đã đăng nhập → lọc các khóa học chưa đăng ký
        enrolled_ids = [
            e.course_id for e in Enrollment.query.filter_by(student_id=current_user.id).all()
        ]
        courses = Course.query.filter(
            ~Course.id.in_(enrolled_ids),
            Course.is_published == True
        ).all()
    else:
        # Nếu chưa đăng nhập → hiển thị tất cả khóa học public
        courses = Course.query.filter_by(is_published=True).all()

    course_list = []
    for c in courses:
        # Nếu thumbnail là tên file → tạo URL đúng
        thumbnail_url = (
            url_for('static', filename=f'uploads/{c.thumbnail_id}')
            if c.thumbnail_id and not c.thumbnail_id.startswith('http') else
            c.thumbnail_id or 'https://via.placeholder.com/300x200?text=EduOnline'
        )

        course_list.append({
            "id": c.id,
            "title": c.title,
            "price": c.price,
            "level": c.level,
            "thumbnail": thumbnail_url,
            "created_at": c.create_at.isoformat()
        })

    return jsonify(course_list)


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    instructor = User.query.get(course.instructor_id)
    modules = course.modules
    reviews = Review.query.filter_by(course_id=course.id).order_by(Review.create_at.desc()).all()
    comments = Comment.query.filter_by(course_id=course.id, parent_id=None).order_by(Comment.created_at.desc()).all()

    return render_template('details.html',
                           course=course,
                           instructor=instructor,
                           modules=modules,
                           reviews=reviews,
                           comments=comments)


@app.route('/api/register_free_course/<int:course_id>', methods=['POST'])
@login_required
def register_free_course(course_id):
    try:
        # 1. Kiểm tra khóa học tồn tại
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Khóa học không tồn tại.'}), 404

        # 2. Kiểm tra khóa học có phải miễn phí không
        if course.price > 0:
            return jsonify({'message': 'Khóa học này không miễn phí.'}), 400

        # 3. Kiểm tra người dùng đã đăng ký khóa học này chưa
        existing_enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if existing_enrollment:
            return jsonify({'message': 'Bạn đã đăng ký khóa học này.'}), 400

        # 4. Tạo bản ghi đăng ký mới
        enrollment = Enrollment(
            student_id=current_user.id,
            course_id=course_id,
            enrolled_at=datetime.utcnow(),
            payment_id=None  # Không có thanh toán cho khóa miễn phí
        )
        db.session.add(enrollment)
        db.session.commit()

        return jsonify({'message': 'Đăng ký thành công.'}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Lỗi máy chủ. Không thể đăng ký.'}), 500

@app.route('/api/purchase', methods=['POST'])
@login_required
def create_purchase():
    data = request.json
    payment = Payment(
        amount=data['amount'],
        payment_method=data['payment_method'],
        payment_status='pending',
        transaction_code=data['transaction_code']
    )
    db.session.add(payment)
    db.session.flush()

    enrollment = Enrollment(
        student_id=current_user.id,
        course_id=data['course_id'],
        payment_id=payment.id
    )
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({'success': True, 'payment_id': payment.id})


@app.route('/my-courses')
@login_required
def my_courses():
    # Lấy danh sách enrollment của user hiện tại
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()

    # Tạo dictionary để map course_id với progress
    course_progress = {e.course_id: e.progress_percent for e in enrollments}

    # Lấy danh sách course
    course_ids = [e.course_id for e in enrollments]
    courses = Course.query.filter(Course.id.in_(course_ids)).all()

    # Thêm thông tin progress vào mỗi course object
    for course in courses:
        course.progress = course_progress.get(course.id, 0.0)

    # Tính toán các thống kê
    total_courses = len(courses)

    # Tính tiến độ trung bình
    avg_progress = 0
    if total_courses > 0:
        total_progress = sum(course.progress for course in courses)
        avg_progress = round(total_progress / total_courses)

    # Đếm số khóa học đang học (progress < 100% và khóa học available + published)
    in_progress_count = 0
    for course in courses:
        if (course.progress < 100 and
                course.is_available and
                course.is_published):
            in_progress_count += 1

    return render_template('my_courses.html',
                           courses=courses,
                           total_courses=total_courses,
                           avg_progress=avg_progress,
                           in_progress_count=in_progress_count)


@app.route('/api/payment/confirm', methods=['POST'])
@login_required
def confirm_payment():
    payment_id = request.json['payment_id']
    payment = Payment.query.get(payment_id)
    payment.payment_status = 'completed'
    payment.paid_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True})



@app.route('/')
def home():
    return render_template('index.html')



if __name__ == '__main__':
    app.run(port=8080,debug=True)