import hashlib
import hmac

import random
from flask_login import current_user
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required
from EduApp import app, dao, login, db
import config
import cloudinary
import cloudinary.uploader
from EduApp.vnpay import vnpay
from models import Module, User, Course, Review, Comment, Enrollment, Payment, Progress, Lesson
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
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'message': 'Không tìm thấy thông tin người dùng'}), 404

        return jsonify({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatar_url': user.avatar_url,
            'role': user.role,
            'created_at': user.create_at.isoformat() if user.create_at else None
        }), 200

    except Exception as e:
        return jsonify({'message': 'Lỗi server khi lấy thông tin người dùng'}), 500


@app.route('/user/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'message': 'Không tìm thấy thông tin người dùng'}), 404

        # Lấy dữ liệu từ form data
        name = request.form.get('name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        avatar_file = request.files.get('avatar_file')

        # Cập nhật tên nếu có
        if name:
            user.name = name

        # Cập nhật mật khẩu nếu có
        if current_password and new_password:
            hashed_current = hashlib.md5(current_password.encode('utf-8')).hexdigest()
            if user.password != hashed_current:
                return jsonify({'message': 'Mật khẩu hiện tại không đúng'}), 400
            
            user.password = hashlib.md5(new_password.encode('utf-8')).hexdigest()

        # Cập nhật avatar nếu có
        if avatar_file and avatar_file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(avatar_file)
                user.avatar_url = upload_result.get('secure_url')
            except Exception as e:
                return jsonify({'message': 'Lỗi khi upload avatar'}), 500

        db.session.commit()
        return jsonify({
            'message': 'Cập nhật thông tin thành công',
            'user': {
                'name': user.name,
                'email': user.email,
                'avatar_url': user.avatar_url
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi cập nhật thông tin'}), 500


@app.route('/user/profile', methods=['DELETE'])
@login_required
def delete_profile():
    try:
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'message': 'Không tìm thấy thông tin người dùng'}), 404

        # Kiểm tra mật khẩu xác nhận
        password = request.json.get('password')
        if not password:
            return jsonify({'message': 'Vui lòng nhập mật khẩu để xác nhận'}), 400

        hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()
        if user.password != hashed_password:
            return jsonify({'message': 'Mật khẩu không đúng'}), 400

        # Xóa các dữ liệu liên quan
        Enrollment.query.filter_by(student_id=user.id).delete()
        Review.query.filter_by(user_id=user.id).delete()
        Comment.query.filter_by(user_id=user.id).delete()
        
        # Nếu là giảng viên, kiểm tra có khóa học không
        if user.role == 'INSTRUCTOR':
            courses = Course.query.filter_by(instructor_id=user.id).all()
            if courses:
                return jsonify({'message': 'Không thể xóa tài khoản vì bạn đang có khóa học'}), 400

        # Xóa người dùng
        db.session.delete(user)
        db.session.commit()

        # Đăng xuất sau khi xóa
        logout_user()
        
        return jsonify({'message': 'Đã xóa tài khoản thành công'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lỗi server khi xóa tài khoản'}), 500


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


@app.route('/student/progress/<int:course_id>', methods=['GET'])
@login_required
def student_progress(course_id):
    try:
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if not enrollment:
            return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 404

        course = Course.query.get(course_id)
        modules = course.modules

        # Tạo chi tiết tiến độ khóa học
        progress_data = {
            'course': {
                'id': course.id,
                'title': course.title,
                'total_modules': len(modules)
            },
            'enrollment': {
                'progress_percent': enrollment.progress_percent,
                'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
            },
            'modules': [{
                'id': module.id,
                'title': module.title,
                'order': module.order
            } for module in sorted(modules, key=lambda x: x.order)]
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
        payment_id = dao.create_payment(
            amount=data.get('amount'),
            payment_method='VNPay',
            payment_status='pending',
            transaction_code=None,
        )
        dao.create_enrollment(student_id=user_id, course_id=course_id, payment_id=payment_id)
        order_id = payment_id  # dùng payment_id làm order_id
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
            if vnp_ResponseCode == '00':
                # Cập nhật trạng thái thanh toán trong database
                payment = Payment.query.filter_by(id=order_id).first()
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
        reviews = Review.query.filter_by(course_id=course_id)\
            .order_by(Review.create_at.desc()).all()

        review_list = [{
            'id': review.id,
            'content': review.content,
            'rating': review.rating,
            'created_at': review.create_at.isoformat() if review.create_at else None,
            'user': {
                'id': review.user.id,
                'name': review.user.name,
                'avatar_url': review.user.avatar_url
            }
        } for review in reviews]

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
            user_id=current_user.id,
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
            user_id=current_user.id,
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
                'content': review.content,
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
            user_id=current_user.id
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
        review.updated_at = datetime.utcnow()  # Cập nhật thời gian sửa
        db.session.commit()

        return jsonify({
            'message': 'Đã cập nhật đánh giá thành công',
            'review': {
                'id': review.id,
                'content': review.content,
                'rating': review.rating,
                'created_at': review.create_at.isoformat(),
                'updated_at': review.updated_at.isoformat() if review.updated_at else None
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
            user_id=current_user.id
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
    app.run(port=8080, debug=True)