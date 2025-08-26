import hashlib
import hmac

import random
from functools import wraps
from flask_login import current_user
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required
from sqlalchemy import func
from EduApp import app, dao, login, db
import config
import cloudinary
import cloudinary.uploader
from EduApp.vnpay import vnpay
from models import Module, User, Course, Review, Comment, Enrollment, Payment, Progress, Lesson,UserRoleEnum,Category
from datetime import datetime


@login.user_loader
def get_user(user_id):
    return dao.get_user_by_id(user_id)

@app.route('/login-admin', methods=['POST'])
def login_admin_process():
    username = request.form.get('username')
    password = request.form.get('password')
    u = dao.auth_user(username=username, password=password, role=UserRoleEnum.ADMIN)
    if u:
        login_user(u)

    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        if not email or not password:
            flash("Vui lòng nhập đầy đủ email và mật khẩu.", 'info')
            return render_template('login.html')

        hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()
        user = User.query.filter_by(email=email, password=hashed_password, active=True).first()

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

    return render_template('cart.html', course=course, instructor=instructor)


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True,

        })
    return jsonify({'logged_in': False}), 401


@app.route('/user/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        user = User.query.filter_by(id=current_user.id, active=True).first()
        if not user:
            return jsonify({'message': 'Không tìm thấy thông tin người dùng'}), 404

        # Lấy tổng số khóa học đã đăng ký
        total_courses = len(user.enrollments)

        # Tính tiến độ trung bình của tất cả khóa học
        avg_progress = 0
        if total_courses > 0:
            avg_progress = sum(e.progress_percent for e in user.enrollments) / total_courses

        # Lấy số khóa học đang học (progress < 100%)
        in_progress_count = sum(1 for e in user.enrollments if e.progress_percent < 100)

        # Lấy danh sách đánh giá gần đây
        recent_reviews = [{
            'id': review.id,
            'course_id': review.course_id,
            'course_title': review.course.title,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.create_at.isoformat() if review.create_at else None,
            'updated_at': review.update_at.isoformat() if review.update_at else None
        } for review in user.reviews[:5]]  # Chỉ lấy 5 đánh giá gần nhất

        # Lấy danh sách khóa học đã đăng ký
        enrolled_courses = [{
            'id': enrollment.course.id,
            'title': enrollment.course.title,
            'progress': enrollment.progress_percent,
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            'thumbnail': enrollment.course.thumbnail_id
        } for enrollment in user.enrollments]

        # Tạo response object
        response = {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'avatar_url': user.avatar_url,
                'role': user.role.value,  # Chuyển enum thành string
                'created_at': user.create_at.isoformat() if user.create_at else None
            },
            'learning_stats': {
                'total_courses': total_courses,
                'average_progress': round(avg_progress, 2),
                'in_progress_courses': in_progress_count
            },
            'enrolled_courses': enrolled_courses,
            'recent_reviews': recent_reviews
        }

        # Thêm thông tin cho giảng viên
        if user.role == UserRoleEnum.INSTRUCTOR:
            instructor_courses = Course.query.filter_by(instructor_id=user.id).all()
            response['instructor_stats'] = {
                'total_courses_teaching': len(instructor_courses),
                'total_students': sum(len(course.enrollments) for course in instructor_courses),
                'courses': [{
                    'id': course.id,
                    'title': course.title,
                    'students_count': len(course.enrollments),
                    'is_published': course.is_published,
                    'created_at': course.create_at.isoformat() if course.create_at else None
                } for course in instructor_courses]
            }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy thông tin người dùng'}), 500


@app.route('/user/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        user = User.query.filter_by(id=current_user.id, active=True).first()
        if not user:
            return jsonify({'message': 'Không tìm thấy thông tin người dùng'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'message': 'Không có dữ liệu cập nhật'}), 400

        # Cập nhật tên nếu có
        if 'name' in data:
            user.name = data['name']

        # Cập nhật email nếu có
        if 'email' in data:
            # Kiểm tra email đã tồn tại chưa
            existing_user = User.query.filter(User.id != user.id, User.email == data['email']).first()
            if existing_user:
                return jsonify({'message': 'Email đã được sử dụng'}), 400
            user.email = data['email']

        # Cập nhật mật khẩu nếu có
        if 'current_password' in data and 'new_password' in data:
            hashed_current = hashlib.md5(data['current_password'].encode('utf-8')).hexdigest()
            if user.password != hashed_current:
                return jsonify({'message': 'Mật khẩu hiện tại không đúng'}), 400
            user.password = hashlib.md5(data['new_password'].encode('utf-8')).hexdigest()

        # Cập nhật avatar_url nếu có
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']

        db.session.commit()

        return jsonify({
            'message': 'Cập nhật thông tin thành công',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'avatar_url': user.avatar_url,
                'role': user.role.value,
                'created_at': user.create_at.isoformat() if user.create_at else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi cập nhật thông tin'}), 500


@app.route('/user/profile', methods=['DELETE'])
@login_required
def delete_profile():
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({
                'message': 'Vui lòng cung cấp mật khẩu để xác nhận',
                'code': 'MISSING_PASSWORD'
            }), 400

        user = User.query.filter_by(id=current_user.id, active=True).first()
        if not user:
            return jsonify({
                'message': 'Không tìm thấy thông tin người dùng',
                'code': 'USER_NOT_FOUND'
            }), 404

        # Xác thực mật khẩu
        hashed_password = hashlib.md5(data['password'].encode('utf-8')).hexdigest()
        if user.password != hashed_password:
            return jsonify({
                'message': 'Mật khẩu xác nhận không đúng',
                'code': 'INVALID_PASSWORD'
            }), 401

        # Kiểm tra nếu là giảng viên có khóa học active
        if user.role == UserRoleEnum.INSTRUCTOR:
            active_courses = Course.query.filter_by(
                instructor_id=user.id,
                is_published=True
            ).first()
            if active_courses:
                return jsonify({
                    'message': 'Không thể xóa tài khoản khi đang có khóa học đang hoạt động',
                    'code': 'HAS_ACTIVE_COURSES'
                }), 400

        try:
            # Thay vì xóa, chỉ cập nhật trạng thái active = False
            user.active = False
            db.session.commit()

            # Đăng xuất
            logout_user()
            return jsonify({
                'message': 'Đã vô hiệu hóa tài khoản thành công',
                'code': 'SUCCESS'
            }), 200
        except Exception as e:
            db.session.rollback()
            raise e

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'message': 'Lỗi server khi xóa tài khoản',
            'code': 'SERVER_ERROR',
            'error': str(e)
        }), 500


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
        # Join với Category để lấy thông tin danh mục
        courses_query = db.session.query(Course, Category.name.label('category_name'))\
            .outerjoin(Category, Course.category_id == Category.id)\
            .filter(
                ~Course.id.in_(enrolled_ids),
                Course.is_published == True
            ).all()
    else:
        # Nếu chưa đăng nhập → hiển thị tất cả khóa học public
        courses_query = db.session.query(Course, Category.name.label('category_name'))\
            .outerjoin(Category, Course.category_id == Category.id)\
            .filter(Course.is_published == True).all()

    course_list = []
    for course, category_name in courses_query:
        # Nếu thumbnail là tên file → tạo URL đúng
        thumbnail_url = (
            url_for('static', filename=f'uploads/{course.thumbnail_id}')
            if course.thumbnail_id and not course.thumbnail_id.startswith('http') else
            course.thumbnail_id or 'https://via.placeholder.com/300x200?text=EduOnline'
        )

        course_list.append({
            "id": course.id,
            "title": course.title,
            "price": course.price,
            "level": course.level,
            "thumbnail": thumbnail_url,
            "created_at": course.create_at.isoformat(),
            "category_name": category_name,
            "category_id": course.category_id
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


@app.route('/payment-history')
@login_required
def payment_history():
    payments = Payment.query.join(Enrollment).filter(Enrollment.student_id == current_user.id).order_by(
        Payment.created_at.desc()).all()
    return render_template('payment_history.html', payments=payments)


@app.route('/api/payment/<int:payment_id>', methods=['GET'])
@login_required
def get_payment_detail(payment_id):
    try:
        # Lấy thông tin payment và join với enrollment để lấy thêm thông tin khóa học
        payment = Payment.query.join(Enrollment).filter(
            Payment.id == payment_id,
            Enrollment.student_id == current_user.id
        ).first()

        if not payment:
            return jsonify({'message': 'Không tìm thấy thông tin giao dịch'}), 404

        # Lấy thông tin khóa học
        enrollment = Enrollment.query.filter_by(payment_id=payment.id).first()
        course = Course.query.get(enrollment.course_id) if enrollment else None

        # Tạo response
        payment_detail = {
            'id': payment.id,
            'amount': payment.amount,
            'payment_method': payment.payment_method,
            'payment_status': payment.payment_status,
            'transaction_code': payment.transaction_code,
            'created_at': payment.created_at.isoformat() if payment.created_at else None,
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
            'course': {
                'id': course.id,
                'title': course.title,
                'price': course.price
            } if course else None
        }

        return jsonify(payment_detail), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy thông tin giao dịch'}), 500


# @app.route('/api/purchase', methods=['POST'])
# @login_required
# def create_purchase():
#     data = request.json
#     payment = Payment(
#         amount=data['amount'],
#         payment_method=data['payment_method'],
#         payment_status='pending',
#         transaction_code=data['transaction_code']
#     )
#     db.session.add(payment)
#     db.session.flush()

#     enrollment = Enrollment(
#         student_id=current_user.id,
#         course_id=data['course_id'],
#         payment_id=payment.id
#     )
#     db.session.add(enrollment)
#     db.session.commit()

#     return jsonify({'success': True, 'payment_id': payment.id})


@app.route('/api/progress/<int:course_id>', methods=['GET'])
@login_required
def get_progress(course_id):
    try:
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if not enrollment:
            return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 404

        progress_data = {
            'course_id': course_id,
            'progress_percent': enrollment.progress_percent,
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            'total_modules': len(Course.query.get(course_id).modules)
        }

        return jsonify(progress_data), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy tiến độ học tập'}), 500


@app.route('/api/progress/update', methods=['POST'])
@login_required
def update_progress():
    try:
        data = request.json
        course_id = data.get('course_id')
        lesson_id = data.get('lesson_id')

        if not course_id or not lesson_id:
            return jsonify({'message': 'Thiếu thông tin khóa học hoặc bài học'}), 400

        # Kiểm tra enrollment
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if not enrollment:
            return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 404

        # Kiểm tra lesson có thuộc khóa học không
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.module.course_id != course_id:
            return jsonify({'message': 'Bài học không thuộc khóa học này'}), 400

        # Kiểm tra xem đã hoàn thành bài học này chưa
        existing_progress = Progress.query.filter_by(
            student_id=current_user.id,
            lesson_id=lesson_id,
            enrollment_id=enrollment.id
        ).first()

        if not existing_progress:
            # Tạo bản ghi progress mới
            progress = Progress(
                student_id=current_user.id,
                lesson_id=lesson_id,
                enrollment_id=enrollment.id
            )
            db.session.add(progress)

            # Cập nhật progress_percent trong enrollment
            total_lessons = sum(len(module.lessons) for module in lesson.module.course.modules)
            completed_lessons = Progress.query.filter_by(
                enrollment_id=enrollment.id
            ).count() + 1  # +1 for the new progress

            enrollment.progress_percent = min(100, round((completed_lessons / total_lessons) * 100, 2))

            db.session.commit()

            return jsonify({
                'message': 'Cập nhật tiến độ thành công',
                'progress_percent': enrollment.progress_percent,
                'completed_at': progress.complete_at.isoformat()
            }), 200

        return jsonify({
            'message': 'Bài học này đã được hoàn thành trước đó',
            'completed_at': existing_progress.complete_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi cập nhật tiến độ học tập'}), 500


@app.route('/student/progress/<int:course_id>', methods=['GET','POST'])
@login_required
def student_progress(course_id):
    try:
        # Lấy danh sách student_ids từ request
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        
        # Nếu không có student_ids, trả về lỗi
        if not student_ids:
            return jsonify({'message': 'Vui lòng cung cấp danh sách student_ids'}), 400

        # Lấy thông tin khóa học
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        modules = course.modules
        
        # Lấy danh sách enrollments cho tất cả student_ids
        enrollments = Enrollment.query.filter(
            Enrollment.student_id.in_(student_ids),
            Enrollment.course_id == course_id
        ).all()

        # Tạo mapping student_id -> enrollment để dễ truy cập
        enrollment_map = {e.student_id: e for e in enrollments}
        
        # Tạo chi tiết tiến độ khóa học cho mỗi student
        students_progress = []
        for student_id in student_ids:
            enrollment = enrollment_map.get(student_id)
            if enrollment:
                student_data = {
                    'student_id': student_id,
                    'enrollment': {
                        'progress_percent': enrollment.progress_percent,
                        'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
                    }
                }
                students_progress.append(student_data)

        # Tạo response data
        progress_data = {
            'course'    : {
                'id': course.id,
                'title': course.title,
                'total_modules': len(modules)
            },
            'modules': [{
                'id': module.id,
                'title': module.title,
                'order': module.ordering
            } for module in sorted(modules, key=lambda x: x.ordering)],
            'students': students_progress
        }

        return jsonify(progress_data), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy tiến độ học tập'}), 500


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


# @app.route('/api/payment/confirm', methods=['POST'])
# @login_required
# def confirm_payment():
#     payment_id = request.json['payment_id']
#     payment = Payment.query.get(payment_id)
#     payment.payment_status = 'completed'
#     payment.paid_at = datetime.utcnow()
#     db.session.commit()

#     return jsonify({'success': True})


@app.route('/')
def home():
    return render_template('index.html')


def role_required(*roles):
    """
    Decorator để kiểm tra role của user.
    Sử dụng: @role_required(UserRoleEnum.INSTRUCTOR)
    hoặc @role_required(UserRoleEnum.ADMIN, UserRoleEnum.INSTRUCTOR)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'message': 'Bạn chưa đăng nhập'}), 401

            user_role = UserRoleEnum(current_user.role)
            if user_role not in roles:
                return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Instructor APIs
@app.route('/instructor/courses', methods=['GET'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def get_instructor_courses():
    try:
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        return jsonify([{
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'price': course.price,
            'thumbnail_id': course.thumbnail_id,
            'level': course.level,
            'is_published': course.is_published,
            'is_available': course.is_available,
            'create_at': course.create_at.isoformat(),
            'total_students': len(course.enrollments)
        } for course in courses]), 200
    except Exception as e:
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/instructor/course/<int:course_id>', methods=['GET'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def get_instructor_course(course_id):
    try:
        course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học hoặc không có quyền truy cập'}), 404

        modules = Module.query.filter_by(course_id=course_id).order_by(Module.ordering).all()
        module_list = []
        
        for module in modules:
            lessons = Lesson.query.filter_by(module_id=module.id).order_by(Lesson.ordering).all()
            module_list.append({
                'id': module.id,
                'title': module.title,
                'ordering': module.ordering,
                'lessons': [{
                    'id': lesson.id,
                    'title': lesson.title,
                    'content_type': lesson.content_type,
                    'ordering': lesson.ordering,
                    'video_url': lesson.video_url,
                    'file_url': lesson.file_url,
                    'text_content': lesson.text_content
                } for lesson in lessons]
            })

        return jsonify({
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'price': course.price,
            'thumbnail_id': course.thumbnail_id,
            'level': course.level,
            'is_published': course.is_published,
            'is_available': course.is_available,
            'max_enrollment': course.max_enrollment,
            'create_at': course.create_at.isoformat(),
            'modules': module_list
        }), 200
    except Exception as e:
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/instructor/course', methods=['POST'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def create_instructor_course():
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['title', 'description', 'price', 'level']
        if not all(field in data for field in required):
            return jsonify({'message': 'Thiếu thông tin bắt buộc'}), 400

        course = Course(
            title=data['title'],
            description=data['description'],
            price=data['price'],
            thumbnail_id=data.get('thumbnail_id'),
            level=data.get('level'),
            instructor_id=current_user.id,
            is_published=False,
            is_available=True,
            max_enrollment=data.get('max_enrollment')
        )
        
        db.session.add(course)
        db.session.commit()

        return jsonify({
            'id': course.id,
            'title': course.title,
            'message': 'Tạo khóa học thành công'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/instructor/course/<int:course_id>', methods=['PUT'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def update_instructor_course(course_id):
    try:
        course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học hoặc không có quyền truy cập'}), 404

        data = request.get_json()
        
        if 'title' in data:
            course.title = data['title']
        if 'description' in data:
            course.description = data['description']
        if 'price' in data:
            course.price = data['price']
        if 'thumbnail_id' in data:
            course.thumbnail_id = data['thumbnail_id']
        if 'level' in data:
            course.level = data['level']
        if 'is_published' in data:
            course.is_published = data['is_published']
        if 'is_available' in data:
            course.is_available = data['is_available']
        if 'max_enrollment' in data:
            course.max_enrollment = data['max_enrollment']

        db.session.commit()
        return jsonify({'message': 'Cập nhật khóa học thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/instructor/course/<int:course_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def delete_instructor_course(course_id):
    try:
        course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học hoặc không có quyền truy cập'}), 404

        db.session.delete(course)
        db.session.commit()
        return jsonify({'message': 'Xóa khóa học thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/instructor/course/<int:course_id>/students', methods=['GET'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def get_course_students(course_id):
    try:
        course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học hoặc không có quyền truy cập'}), 404

        enrollments = Enrollment.query.filter_by(course_id=course_id).all()
        students = []
        
        for enrollment in enrollments:
            student = enrollment.student
            progress = Progress.query.filter_by(
                student_id=student.id,
                enrollment_id=enrollment.id
            ).order_by(Progress.complete_at.desc()).first()
            
            students.append({
                'id': student.id,
                'name': student.name,
                'email': student.email,
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'last_access': progress.complete_at.isoformat() if progress else None,
                'completed_lessons': Progress.query.filter_by(
                    student_id=student.id,
                    enrollment_id=enrollment.id
                ).count()
            })

        return jsonify(students), 200
    except Exception as e:
        return jsonify({'message': 'Lỗi server'}), 500


# Module Management APIs
@app.route('/api/course/<int:course_id>/module', methods=['POST'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def create_module(course_id):
    try:
        course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học hoặc không có quyền truy cập'}), 404

        data = request.get_json()
        if 'title' not in data:
            return jsonify({'message': 'Thiếu tiêu đề module'}), 400

        # Sử dụng order từ request nếu có, nếu không lấy max order + 1
        if 'ordering' in data:
            ordering = data['ordering']
            # Kiểm tra xem order đã tồn tại chưa
            existing_module = Module.query.filter_by(course_id=course_id, ordering=ordering).first()
            if existing_module:
                # Nếu order đã tồn tại, dịch chuyển các module có order >= ordering lên 1 bậc
                Module.query.filter(
                    Module.course_id == course_id,
                    Module.ordering >= ordering
                ).update({Module.ordering: Module.ordering + 1})
        else:
            # Get max ordering nếu không có order trong request
            ordering = (db.session.query(func.max(Module.ordering))
                      .filter_by(course_id=course_id).scalar() or 0) + 1

        module = Module(
            title=data['title'],
            course_id=course_id,
            ordering=ordering
        )
        
        db.session.add(module)
        db.session.commit()

        return jsonify({
            'id': module.id,
            'title': module.title,
            'ordering': module.ordering,
            'message': 'Tạo module thành công'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/api/module/<int:module_id>', methods=['PUT'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def update_module(module_id):
    try:
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'message': 'Không tìm thấy module'}), 404

        course = Course.query.filter_by(id=module.course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không có quyền truy cập'}), 403

        data = request.get_json()
        if 'title' in data:
            module.title = data['title']
        if 'ordering' in data:
            module.ordering = data['ordering']

        db.session.commit()
        return jsonify({'message': 'Cập nhật module thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/api/module/<int:module_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def delete_module(module_id):
    try:
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'message': 'Không tìm thấy module'}), 404

        course = Course.query.filter_by(id=module.course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không có quyền truy cập'}), 403

        db.session.delete(module)
        db.session.commit()
        return jsonify({'message': 'Xóa module thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


# Lesson Management APIs 
@app.route('/api/module/<int:module_id>/lesson', methods=['POST'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def create_lesson(module_id):
    try:
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'message': 'Không tìm thấy module'}), 404

        course = Course.query.filter_by(id=module.course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không có quyền truy cập'}), 403

        data = request.get_json()
        required = ['title', 'content_type']
        if not all(field in data for field in required):
            return jsonify({'message': 'Thiếu thông tin bắt buộc'}), 400

        # Sử dụng order từ request nếu có, nếu không lấy max order + 1
        if 'ordering' in data:
            ordering = data['ordering']
            # Kiểm tra xem order đã tồn tại chưa
            existing_lesson = Lesson.query.filter_by(module_id=module_id, ordering=ordering).first()
            if existing_lesson:
                # Nếu order đã tồn tại, dịch chuyển các lesson có order >= ordering lên 1 bậc
                Lesson.query.filter(
                    Lesson.module_id == module_id,
                    Lesson.ordering >= ordering
                ).update({Lesson.ordering: Lesson.ordering + 1})
        else:
            # Get max ordering nếu không có order trong request
            ordering = (db.session.query(func.max(Lesson.ordering))
                      .filter_by(module_id=module_id).scalar() or 0) + 1

        lesson = Lesson(
            title=data['title'],
            content_type=data['content_type'],
            video_url=data.get('video_url'),
            file_url=data.get('file_url'),
            text_content=data.get('text_content'),
            module_id=module_id,
            ordering=ordering
        )
        
        db.session.add(lesson)
        db.session.commit()

        return jsonify({
            'id': lesson.id,
            'title': lesson.title,
            'content_type': lesson.content_type,
            'ordering': lesson.ordering,
            'message': 'Tạo bài học thành công'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/api/lesson/<int:lesson_id>', methods=['PUT'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def update_lesson(lesson_id):
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return jsonify({'message': 'Không tìm thấy bài học'}), 404

        module = Module.query.get(lesson.module_id)
        course = Course.query.filter_by(id=module.course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không có quyền truy cập'}), 403

        data = request.get_json()
        
        if 'title' in data:
            lesson.title = data['title']
        if 'content_type' in data:
            lesson.content_type = data['content_type']
        if 'video_url' in data:
            lesson.video_url = data['video_url']
        if 'file_url' in data:
            lesson.file_url = data['file_url']
        if 'text_content' in data:
            lesson.text_content = data['text_content']
        if 'ordering' in data:
            lesson.ordering = data['ordering']

        db.session.commit()
        return jsonify({'message': 'Cập nhật bài học thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


@app.route('/api/lesson/<int:lesson_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.INSTRUCTOR)
def delete_lesson(lesson_id):
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return jsonify({'message': 'Không tìm thấy bài học'}), 404

        module = Module.query.get(lesson.module_id)
        course = Course.query.filter_by(id=module.course_id, instructor_id=current_user.id).first()
        if not course:
            return jsonify({'message': 'Không có quyền truy cập'}), 403

        db.session.delete(lesson)
        db.session.commit()
        return jsonify({'message': 'Xóa bài học thành công'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server'}), 500


# Module & Lesson APIs
@app.route('/api/course/<int:course_id>/modules', methods=['GET'])
def get_course_modules(course_id):
    try:
        # Kiểm tra khóa học tồn tại
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        # Lấy và sắp xếp modules theo thứ tự
        modules = Module.query.filter_by(course_id=course_id).order_by(Module.ordering).all()
        
        module_list = [{
            'id': module.id,
            'title': module.title,
            'ordering': module.ordering,
            'total_lessons': len(module.lessons)
        } for module in modules]

        return jsonify(module_list), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy danh sách module'}), 500


@app.route('/api/module/<int:module_id>/lessons', methods=['GET'])
def get_module_lessons(module_id):
    try:
        # Kiểm tra module tồn tại
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'message': 'Không tìm thấy module'}), 404

        # Lấy và sắp xếp lessons theo thứ tự
        lessons = Lesson.query.filter_by(module_id=module_id).order_by(Lesson.ordering).all()
        
        lesson_list = [{
            'id': lesson.id,
            'module_id': lesson.module_id,
            'title': lesson.title,
            'ordering': lesson.ordering,
            'content_type': lesson.content_type,
            'video_url': lesson.video_url,
            'file_url': lesson.file_url,
            'text_content': lesson.text_content
        } for lesson in lessons]

        return jsonify({
            'module': {
                'id': module.id,
                'title': module.title,
                'course_id': module.course_id,
                'ordering': module.ordering
            },
            'lessons': lesson_list
        }), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy danh sách bài học'}), 500


@app.route('/api/lesson/<int:lesson_id>', methods=['GET'])
@login_required
def get_lesson_detail(lesson_id):
    try:
        # Kiểm tra lesson tồn tại
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return jsonify({'message': 'Không tìm thấy bài học'}), 404

        # Kiểm tra user đã đăng ký khóa học chưa
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=lesson.module.course_id
        ).first()
        
        if not enrollment:
            return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 403

        # Kiểm tra bài học đã hoàn thành chưa
        progress = Progress.query.filter_by(
            student_id=current_user.id,
            lesson_id=lesson_id,
            enrollment_id=enrollment.id
        ).first()

        lesson_detail = {
            'id': lesson.id,
            'title': lesson.title,
            'content_type': lesson.content_type,
            'video_url': lesson.video_url,
            'file_url': lesson.file_url,
            'text_content': lesson.text_content,
            'ordering': lesson.ordering,
            'module': {
                'id': lesson.module.id,
                'title': lesson.module.title
            },
            'is_completed': True if progress else False,
            'completed_at': progress.complete_at.isoformat() if progress else None
        }

        return jsonify(lesson_detail), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy chi tiết bài học'}), 500


##VNPAY
def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


@app.route('/api/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        data = request.get_json()
        order_type = 'billpayment'
        course_id = data.get('course_id')
        user_id = current_user.id
        
        # Tạo payment record
        payment = Payment(
            amount=data.get('amount'),
            payment_method='VNPay',
            payment_status='pending'
        )
        db.session.add(payment)
        db.session.flush()  # Để lấy payment.id

        # Tạo enrollment
        enrollment = Enrollment(
            student_id=user_id,
            course_id=course_id,
            payment_id=payment.id,
            enrolled_at=datetime.utcnow()
        )
        db.session.add(enrollment)
        db.session.commit()

        order_id = payment.id  # dùng payment_id làm order_id
        amount = int(data.get('amount')) * 100
        order_desc = data.get('order_desc')
        bank_code = data.get('bank_code')
        language = data.get('language')

        ipaddr = get_client_ip()

        vnp = vnpay()
        vnp.requestData['vnp_Version'] = '2.1.0'
        vnp.requestData['vnp_Command'] = 'pay'
        vnp.requestData['vnp_TmnCode'] = config.VNPAY_TMN_CODE
        vnp.requestData['vnp_Amount'] = amount
        vnp.requestData['vnp_CurrCode'] = 'VND'
        vnp.requestData['vnp_TxnRef'] = order_id
        vnp.requestData['vnp_OrderInfo'] = order_desc
        vnp.requestData['vnp_OrderType'] = order_type
        vnp.requestData['vnp_Locale'] = language if language else 'vn'
        if bank_code:
            vnp.requestData['vnp_BankCode'] = bank_code
        vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
        vnp.requestData['vnp_IpAddr'] = ipaddr
        vnp.requestData['vnp_ReturnUrl'] = config.VNPAY_RETURN_URL

        vnpay_payment_url = vnp.get_payment_url(config.VNPAY_PAYMENT_URL, config.VNPAY_HASH_SECRET_KEY)
        return jsonify({'vnpay_url': vnpay_payment_url})


@app.route('/api/payment/ipn')
def payment_ipn():
    inputData = request.args
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.to_dict()

        order_id = inputData.get('vnp_TxnRef')
        amount = inputData.get('vnp_Amount')
        order_desc = inputData.get('vnp_OrderInfo')
        vnp_ResponseCode = inputData.get('vnp_ResponseCode')

        if vnp.validate_response(config.VNPAY_HASH_SECRET_KEY):
            # Giả lập kiểm tra và cập nhật trạng thái
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print("✅ Thanh toán thành công")
                    else:
                        print("❌ Thanh toán lỗi")

                    return print({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    return print({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                return print({'RspCode': '04', 'Message': 'Invalid amount'})
        else:
            return print({'RspCode': '97', 'Message': 'Invalid Signature'})
    else:
        return print({'RspCode': '99', 'Message': 'Invalid request'})


@app.route('/payment/return')
def payment_return():
    inputData = request.args
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.to_dict()

        order_id = inputData.get('vnp_TxnRef')
        amount = int(inputData.get('vnp_Amount')) / 100
        order_desc = inputData.get('vnp_OrderInfo')
        vnp_TransactionNo = inputData.get('vnp_TransactionNo')
        vnp_ResponseCode = inputData.get('vnp_ResponseCode')

        if vnp.validate_response(config.VNPAY_HASH_SECRET_KEY):
            result_text = "Thành công" if vnp_ResponseCode == '00' else "Lỗi"
            payment = Payment.query.filter_by(id=order_id).first()
            if vnp_ResponseCode == '00':
                # Cập nhật trạng thái thanh toán trong database
                
                if payment:
                    payment.payment_status = 'Success'
                    payment.paid_at = datetime.utcnow()
                    payment.transaction_code = vnp_TransactionNo
                    db.session.commit()
                    # Cập nhật trạng thái Enrollment liên quan
                    enrollment = Enrollment.query.filter_by(payment_id=payment.id).first()
                    if enrollment:
                        enrollment.enrolled_at = datetime.utcnow()
                        db.session.commit()
            else:
                if payment:
                    payment.payment_status = 'Failed'
                    enrollment = Enrollment.query.filter_by(payment_id=payment.id).first()
                    if enrollment:
                        db.session.delete(enrollment)
                db.session.commit()
            return render_template('payment_return.html', title="Kết quả thanh toán", result=result_text,
                                   order_id=order_id, amount=amount, order_desc=order_desc,
                                   vnp_TransactionNo=vnp_TransactionNo, vnp_ResponseCode=vnp_ResponseCode)
        else:
            return render_template('payment_return.html', title="Kết quả thanh toán", result="Lỗi",
                                   order_id=order_id, amount=amount, order_desc=order_desc,
                                   vnp_TransactionNo=vnp_TransactionNo, vnp_ResponseCode=vnp_ResponseCode,
                                   msg="Sai checksum")
    return render_template('payment_return.html', title="Kết quả thanh toán", result="")


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip


@app.route('/api/course/<int:course_id>/reviews', methods=['GET'])
def get_course_reviews(course_id):
    try:
        # Kiểm tra khóa học tồn tại
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        # Lấy tất cả reviews của khóa học, sắp xếp theo thời gian mới nhất
        reviews = Review.query.filter_by(course_id=course_id).order_by(Review.create_at.desc()).all()

        def format_review(review):
            review_dict = {
                'id': review.id,
                'content': review.comment,
                'rating': review.rating,
                'created_at': review.create_at.isoformat() if review.create_at else None,
                'updated_at': review.update_at.isoformat() if review.update_at else None,
                'user': {
                    'id': review.reviewer.id,
                    'name': review.reviewer.name,
                    'avatar_url': review.reviewer.avatar_url
                }
            }
            return review_dict

        review_list = [format_review(review) for review in reviews]

        return jsonify(review_list), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy đánh giá'}), 500


@app.route('/api/review/<int:course_id>', methods=['POST'])
@login_required
def create_review(course_id):
    try:
        # Kiểm tra khóa học tồn tại
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        # Kiểm tra user đã đăng ký khóa học chưa
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()
        if not enrollment:
            return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 403

        # Kiểm tra user đã review khóa học này chưa
        existing_review = Review.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()
        if existing_review:
            return jsonify({'message': 'Bạn đã đánh giá khóa học này rồi'}), 400

        data = request.json
        content = data.get('content')
        rating = data.get('rating')

        # Validate dữ liệu
        if not content or not rating:
            return jsonify({'message': 'Thiếu nội dung hoặc điểm đánh giá'}), 400
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'message': 'Điểm đánh giá phải từ 1-5'}), 400

        # Tạo review mới
        review = Review(
            student_id=current_user.id,
            course_id=course_id,
            comment=content,
            rating=rating,
            create_at=datetime.utcnow()
        )
        db.session.add(review)
        db.session.commit()

        return jsonify({
            'message': 'Đã thêm đánh giá thành công',
            'review': {
                'id': review.id,
                'content': review.comment,
                'rating': review.rating,
                'created_at': review.create_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi thêm đánh giá'}), 500


@app.route('/api/review/<int:review_id>', methods=['PUT'])
@login_required
def update_review(review_id):
    try:
        # Kiểm tra review tồn tại và thuộc về user hiện tại
        review = Review.query.filter_by(
            id=review_id,
            student_id=current_user.id
        ).first()
        
        if not review:
            return jsonify({'message': 'Không tìm thấy đánh giá hoặc không có quyền sửa'}), 404

        data = request.json
        content = data.get('content')
        rating = data.get('rating')

        # Validate dữ liệu
        if not content or not rating:
            return jsonify({'message': 'Thiếu nội dung hoặc điểm đánh giá'}), 400
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'message': 'Điểm đánh giá phải từ 1-5'}), 400

        # Cập nhật review
        review.comment = content
        review.rating = rating
        review.update_at = datetime.utcnow()  # Cập nhật thời gian sửa
        db.session.commit()

        return jsonify({
            'message': 'Đã cập nhật đánh giá thành công',
            'review': {
                'id': review.id,
                'content': review.comment,
                'rating': review.rating,
                'created_at': review.create_at.isoformat(),
                'updated_at': review.update_at.isoformat() if review.update_at else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi cập nhật đánh giá'}), 500


@app.route('/api/review/<int:review_id>', methods=['DELETE'])
@login_required
def delete_review(review_id):
    try:
        # Kiểm tra review tồn tại và thuộc về user hiện tại
        review = Review.query.filter_by(
            id=review_id,
            student_id=current_user.id
        ).first()
        
        if not review:
            return jsonify({'message': 'Không tìm thấy đánh giá hoặc không có quyền xóa'}), 404

        # Xóa review
        db.session.delete(review)
        db.session.commit()

        return jsonify({'message': 'Đã xóa đánh giá thành công'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi xóa đánh giá'}), 500


@app.route('/api/course/<int:course_id>/comments', methods=['GET'])
def get_course_comments(course_id):
    try:
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        # Chỉ lấy các comment gốc (không có parent_id)
        root_comments = Comment.query.filter_by(
            course_id=course_id,
            parent_id=None
        ).order_by(Comment.created_at.desc()).all()

        def format_comment(comment):
            comment_dict = {
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
                'user': {
                    'id': comment.user.id,
                    'name': comment.user.name,
                    'avatar_url': comment.user.avatar_url
                },
                'replies': [format_comment(reply) for reply in comment.replies]
            }
            return comment_dict

        comment_list = [format_comment(comment) for comment in root_comments]
        return jsonify(comment_list), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy bình luận'}), 500


@app.route('/api/comment/<int:course_id>', methods=['POST'])
@login_required
def create_comment(course_id):
    try:
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Không tìm thấy khóa học'}), 404

        data = request.json
        content = data.get('content')
        parent_id = data.get('parent_id')  # ID của comment cha nếu là reply

        if not content or not content.strip():
            return jsonify({'message': 'Nội dung bình luận không được để trống'}), 400

        # Nếu là reply, kiểm tra comment cha tồn tại
        if parent_id:
            parent_comment = Comment.query.get(parent_id)
            if not parent_comment or parent_comment.course_id != course_id:
                return jsonify({'message': 'Không tìm thấy bình luận gốc'}), 404
            # Không cho phép reply của reply (chỉ 1 cấp)
            if parent_comment.parent_id is not None:
                return jsonify({'message': 'Không thể trả lời comment reply'}), 400

        comment = Comment(
            user_id=current_user.id,
            course_id=course_id,
            parent_id=parent_id,
            content=content.strip(),
            created_at=datetime.utcnow()
        )
        db.session.add(comment)
        db.session.commit()

        return jsonify({
            'message': 'Đã thêm bình luận thành công',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'parent_id': comment.parent_id,
                'created_at': comment.created_at.isoformat(),
                'user': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'avatar_url': current_user.avatar_url
                }
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi thêm bình luận'}), 500


@app.route('/api/comment/<int:comment_id>', methods=['PUT'])
@login_required
def update_comment(comment_id):
    try:
        # Kiểm tra comment tồn tại và thuộc về user hiện tại
        comment = Comment.query.filter_by(
            id=comment_id,
            user_id=current_user.id
        ).first()

        if not comment:
            return jsonify({'message': 'Không tìm thấy bình luận hoặc không có quyền sửa'}), 404

        # Lấy nội dung mới
        data = request.json
        content = data.get('content')

        if not content or not content.strip():
            return jsonify({'message': 'Nội dung bình luận không được để trống'}), 400

        # Cập nhật comment
        comment.content = content.strip()
        comment.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Đã cập nhật bình luận thành công',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi cập nhật bình luận'}), 500


@app.route('/api/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    try:
        # Kiểm tra comment tồn tại và thuộc về user hiện tại 
        comment = Comment.query.filter_by(
            id=comment_id,
            user_id=current_user.id
        ).first()

        if not comment:
            return jsonify({'message': 'Không tìm thấy bình luận hoặc không có quyền xóa'}), 404

        # Xóa tất cả replies của comment này trước
        Comment.query.filter_by(parent_id=comment_id).delete()

        # Sau đó xóa comment gốc
        db.session.delete(comment)
        db.session.commit()

        return jsonify({'message': 'Đã xóa bình luận và các phản hồi thành công'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi xóa bình luận'}), 500

if __name__ == '__main__':
    app.run(port=8080, debug=True,use_reloader=False)