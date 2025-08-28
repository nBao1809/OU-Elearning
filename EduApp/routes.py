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

            # Xét role để redirect
            if user.role.value == "STUDENT":
                return redirect(url_for('home'))   # Trang chính hiển thị khóa học
            elif user.role.value == "INSTRUCTOR":
                return redirect(url_for('instructor_dashboard'))  # Route riêng cho giảng viên


            # Nếu lỡ có role không xác định thì fallback
            return redirect(url_for('home'))
        else:
            flash('Email hoặc mật khẩu không đúng!', 'error')

    return render_template('login.html')

def hash_password(password: str) -> str:
    # băm mật khẩu thành chuỗi hex SHA256
    return hashlib.md5(password.encode("utf-8")).hexdigest()



@app.route("/my_account", methods=["GET", "POST"])
@login_required
def my_account():
    if request.method == "POST":
        action = request.form.get("action")

        # === Cập nhật tên + avatar ===
        if action == "update_profile":
            new_name = request.form.get("name").strip()
            avatar = request.files.get("avatar")

            if new_name:
                current_user.name = new_name

            if avatar:
                upload_result = cloudinary.uploader.upload(
                    avatar,
                    folder="eduonline/avatars",
                    public_id=f"user_{current_user.id}",
                    overwrite=True,
                    transformation=[{"width": 300, "height": 300, "crop": "fill"}]
                )
                current_user.avatar_url = upload_result["secure_url"]

            db.session.commit()
            flash("✅ Cập nhật hồ sơ thành công!", "success")
            return redirect(url_for("my_account"))

        # === Đổi mật khẩu ===
        elif action == "change_password":
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            # So sánh mật khẩu cũ
            if current_user.password != hash_password(old_password):
                flash("❌ Mật khẩu cũ không đúng!", "danger")
            elif new_password != confirm_password:
                flash("❌ Mật khẩu mới không khớp!", "danger")
            else:
                current_user.password = hash_password(new_password)
                db.session.commit()
                flash("✅ Đổi mật khẩu thành công!", "success")

            return redirect(url_for("my_account"))

    return render_template("my_account.html", user=current_user)


@app.route('/instructor')
def instructor_dashboard():
    return render_template('instructor_index.html')

@app.route('/instructor/courses/create')
@login_required
def create_course():
    return render_template('create_course.html')



@app.route("/instructor/courses/<int:course_id>/progress", methods=["GET"])
@login_required
def get_course_progress(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền xem tiến độ khóa học này"}), 403

    # tổng số lesson trong khóa học
    total_lessons = Lesson.query.join(Module).filter(Module.course_id == course.id).count()

    # danh sách enrollments
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    results = []

    for e in enrollments:
        student = User.query.get(e.student_id)
        if not student:
            continue

        completed_lessons = Progress.query.filter_by(enrollment_id=e.id).count()
        progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        results.append({
            "student_id": student.id,
            "student_name": student.name,
            "student_email": student.email,
            "student_avatar": student.avatar_url or "",
            "progress_percent": round(progress_percent, 2),
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None
        })

    return jsonify({
        "course_id": course.id,
        "course_title": course.title,
        "students": results
    })



@app.route("/instructor/courses/<int:course_id>/progress/view", methods=["GET"])
@login_required
def course_progress_page(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        return "Không có quyền truy cập", 403

    return render_template("course_progress.html", course=course)





@app.route('/api/instructor/courses', methods=['POST'])
@login_required
def create_course_api():

    title = request.form.get('title')
    description = request.form.get('description')
    price = float(request.form.get('price', 0.0))
    level = request.form.get('level')
    category_id = request.form.get('category_id')
    max_enrollment = request.form.get('max_enrollment') or None
    is_published = request.form.get('is_published', 'false').lower() == 'true'
    is_available = request.form.get('is_available', 'false').lower() == 'true'

    # modules truyền dạng JSON string trong form-data
    modules_raw = request.form.get('modules', '[]')
    try:
        import json
        modules_data = json.loads(modules_raw)
    except Exception:
        return jsonify({"error": "Dữ liệu modules không hợp lệ"}), 400

    # Validate cơ bản
    if not title:
        return jsonify({"error": "Tên khóa học không được bỏ trống"}), 400

    if not category_id:
        return jsonify({"error": "Khóa học phải thuộc một danh mục"}), 400

    if len(modules_data) < 2:
        return jsonify({"error": "Khóa học phải có ít nhất 2 module"}), 400

    for idx, module in enumerate(modules_data, start=1):
        if not module.get('title'):
            return jsonify({"error": f"Module {idx} thiếu tiêu đề"}), 400
        lessons = module.get('lessons', [])
        if len(lessons) < 1:
            return jsonify({"error": f"Module {idx} phải có ít nhất 1 lesson"}), 400
        for jdx, lesson in enumerate(lessons, start=1):
            if not lesson.get('title'):
                return jsonify({"error": f"Lesson {jdx} trong Module {idx} thiếu tiêu đề"}), 400

    # Upload thumbnail nếu có
    thumbnail_url = None
    thumbnail_file = request.files.get('thumbnail')
    if thumbnail_file and thumbnail_file.filename != '':
        upload_result = cloudinary.uploader.upload(
           thumbnail_file
        )
        thumbnail_url = upload_result.get('secure_url')

    # Tạo Course mới
    new_course = Course(
        title=title,
        description=description,
        price=price,
        level=level,
        category_id=category_id,
        thumbnail_id=thumbnail_url,
        max_enrollment=max_enrollment,
        instructor_id=current_user.id,
        is_published=is_published,
        is_available=is_available
    )
    db.session.add(new_course)
    db.session.flush()  # để có new_course.id

    # Thêm Modules và Lessons
    for idx, module_data in enumerate(modules_data, start=1):
        module = Module(
            course_id=new_course.id,
            title=module_data['title'],
            ordering=idx
        )
        db.session.add(module)
        db.session.flush()

        for jdx, lesson_data in enumerate(module_data['lessons'], start=1):
            lesson = Lesson(
                module_id=module.id,
                title=lesson_data['title'],
                ordering=jdx,
                content_type=lesson_data.get('content_type'),
                video_url=lesson_data.get('video_url'),
                file_url=lesson_data.get('file_url'),
                text_content=lesson_data.get('text_content')
            )
            db.session.add(lesson)

    db.session.commit()

    return jsonify({
        "message": "Khóa học đã được tạo thành công",
        "course_id": new_course.id,
        "thumbnail_url": thumbnail_url,
        "is_published": new_course.is_published,
        "is_available": new_course.is_available
    }), 201



@app.route('/api/categories')
def get_categories():
    categories = Category.query.all()
    result = [{
        "id": c.id,
        "name": c.name,
        "description": c.description if hasattr(c, 'description') else None
    } for c in categories]

    return jsonify(result)


@app.route('/api/instructor/courses')
@login_required
def instructor_courses():
    if current_user.role.value != 'INSTRUCTOR':
        return jsonify({"error": "Bạn không có quyền!"}), 403

    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    course_list = [{
        "id": c.id,
        "title": c.title,
        "thumbnail": c.thumbnail_id,
        "price": c.price,
        "level": c.level,
        "category_name": c.category.name if c.category else None,
        "created_at": c.create_at.isoformat()
    } for c in courses]

    return jsonify(course_list)

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

@app.route('/instructor/course/<int:course_id>/edit')
@login_required
def course_edit(course_id):
    course = Course.query.get_or_404(course_id)

    # Check quyền Instructor
    if current_user.id != course.instructor_id:
        flash("Bạn không có quyền chỉnh sửa khoá học này!", "danger")
        return redirect(url_for("study", course_id=course.id))

    modules = Module.query.filter_by(course_id=course.id).order_by(Module.id).all()
    page = request.args.get("page", 1, type=int)
    comments = Comment.query.filter_by(course_id=course.id, parent_id=None) \
                .order_by(Comment.created_at.desc()) \
                .paginate(page=page, per_page=5)

    return render_template("course_edit.html",
                           course=course,
                           modules=modules,
                           comments=comments)

@app.route('/api/module/<int:module_id>', methods=['PUT'])
@login_required
def update_module(module_id):
    module = Module.query.get_or_404(module_id)
    if current_user.id != module.course.instructor_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    module.title = data.get("title", module.title)
    db.session.commit()
    return jsonify({"status": "success", "title": module.title})


@app.route('/api/course/<int:course_id>/module', methods=['POST'])
@login_required
def add_module(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.id != course.instructor_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_module = Module(
        course_id=course.id,
        title=data.get("title", "Module mới")
    )
    db.session.add(new_module)
    db.session.commit()

    # 🔥 Tạo luôn 1 lesson mặc định
    first_lesson = Lesson(
        module_id=new_module.id,
        title="Lesson mới",
        content_type="text",
        text_content="Nội dung mới"
    )
    db.session.add(first_lesson)
    db.session.commit()

    return jsonify({"status": "success", "module_id": new_module.id, "lesson_id": first_lesson.id})


# Cập nhật tên bài học
@app.route('/api/lesson/<int:lesson_id>', methods=['PUT'])
@login_required
def update_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    data = request.get_json()

    if "title" in data:
        lesson.title = data["title"].strip()
    if "type" in data:
        # reset content trước
        lesson.text_content = None
        lesson.video_url = None
        lesson.file_url = None
        if data["type"] == "text":
            lesson.text_content = lesson.text_content or ""
        elif data["type"] == "video":
            lesson.video_url = lesson.video_url or ""
        elif data["type"] == "file":
            lesson.file_url = lesson.file_url or ""
    if "content" in data:
        if lesson.video_url is not None:
            lesson.video_url = data["content"]
        elif lesson.file_url is not None:
            lesson.file_url = data["content"]
        else:
            lesson.text_content = data["content"]

    db.session.commit()
    return jsonify({"message": "Lesson updated", "id": lesson.id})



# Cập nhật URL bài học (video/file)
@app.route('/api/lesson/<int:lesson_id>/url', methods=['PUT'])
@login_required
def update_lesson_url(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if current_user.id != lesson.module.course.instructor_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    url = data.get("url")
    if url:
        if "youtube.com" in url or "youtu.be" in url:
            lesson.video_url = url
            lesson.content_type = "video"
        elif url.endswith((".pdf", ".docx", ".pptx")):
            lesson.file_url = url
            lesson.content_type = "file"
        else:
            lesson.text_content = url
            lesson.content_type = "text"
    db.session.commit()
    return jsonify({"status": "success"})


# Thêm lesson mới
@app.route('/api/module/<int:module_id>/lesson', methods=['POST'])
@login_required
def add_lesson(module_id):
    module = Module.query.get_or_404(module_id)
    if current_user.id != module.course.instructor_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    new_lesson = Lesson(
        module_id=module.id,
        title=data.get("title", "Lesson mới"),
        content_type="text",
        text_content="Nội dung mới"
    )
    db.session.add(new_lesson)
    db.session.commit()
    return jsonify({"status": "success", "lesson_id": new_lesson.id})

@app.route('/api/course/<int:course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Check quyền Instructor
    if current_user.id != course.instructor_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    if "title" in data:
        course.title = data["title"].strip()
    if "description" in data:
        course.description = data["description"].strip()

    db.session.commit()
    return jsonify({"status": "success", "id": course.id})

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

    # Lấy tổng số review và rating trung bình
    all_reviews = Review.query.filter_by(course_id=course.id).all()
    total_reviews = len(all_reviews)
    avg_rating = round(sum(r.rating for r in all_reviews) / total_reviews, 1) if total_reviews > 0 else None

    # Lấy trang review đầu tiên
    page = 1
    per_page = 5
    pagination = Review.query.filter_by(course_id=course.id)\
        .order_by(Review.create_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    reviews = pagination.items

    return render_template('details.html',
                           course=course,
                           instructor=instructor,
                           modules=modules,
                           reviews=reviews,
                           total_reviews=total_reviews,
                           avg_rating=avg_rating,
                           has_next=pagination.has_next
                           )


@app.route('/course/<int:course_id>/reviews')
def load_reviews(course_id):
    page = request.args.get('page', 1, type=int)
    per_page = 5

    pagination = Review.query.filter_by(course_id=course_id) \
        .order_by(Review.create_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    reviews = [{
        "id": r.id,
        "name": r.reviewer.name,
        "rating": r.rating,
        "comment": r.comment,
        "created_day": r.create_at.strftime("%d-%m-%Y")
    } for r in pagination.items]

    return jsonify({
        "reviews": reviews,
        "has_next": pagination.has_next
    })



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

        # 4. Kiểm tra số lượng học viên đã đạt tối đa chưa
        if course.max_enrollment:  # Chỉ kiểm tra nếu có giới hạn số lượng
            current_enrollments = Enrollment.query.filter_by(course_id=course_id).count()
            if current_enrollments >= course.max_enrollment:
                return jsonify({
                    'message': 'Khóa học đã đạt số lượng đăng ký tối đa.',
                    'current_enrollments': current_enrollments,
                    'max_enrollment': course.max_enrollment
                }), 400

        # 5. Tạo bản ghi đăng ký mới
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


@app.route("/complete_lesson/<int:lesson_id>", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    # Kiểm tra đã có progress chưa
    existing = Progress.query.filter_by(
        student_id=current_user.id,
        lesson_id=lesson_id
    ).first()

    # Lấy enrollment tương ứng
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=lesson.module.course_id
    ).first()

    if not existing:
        new_progress = Progress(
            student_id=current_user.id,
            lesson_id=lesson_id,
            enrollment_id=enrollment.id
        )
        db.session.add(new_progress)
        db.session.commit()

    # Cập nhật progress_percent
    total_lessons = Lesson.query.join(Module).filter(
        Module.course_id == lesson.module.course_id
    ).count()

    completed_lessons = Progress.query.filter_by(
        student_id=current_user.id,
        enrollment_id=enrollment.id
    ).count()

    enrollment.progress_percent = round((completed_lessons / total_lessons) * 100, 2)
    db.session.commit()

    return jsonify({"status": "success", "lesson_id": lesson_id, "progress_percent": enrollment.progress_percent})


@app.route('/course/<int:course_id>/study')
@login_required
def study(course_id):
    # Lấy khoá học
    course = Course.query.get_or_404(course_id)

    # Kiểm tra user có đăng ký chưa
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()

    if not enrollment:
        flash("Bạn chưa đăng ký khoá học này.", "error")
        return redirect(url_for("course_detail", course_id=course.id))

    # Lấy modules + lessons
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.ordering).all()

    # Lấy bình luận (phân trang)
    page = request.args.get("page", 1, type=int)
    comments = Comment.query.filter_by(course_id=course.id, parent_id=None) \
                .order_by(Comment.created_at.desc()) \
                .paginate(page=page, per_page=5)

    # Lấy đánh giá
    reviews = Review.query.filter_by(course_id=course.id).all()

    return render_template(
        "study.html",
        course=course,
        modules=modules,
        comments=comments,   # pagination object
        reviews=reviews,
        enrollment=enrollment
    )




@app.route('/course/<int:course_id>/comment', methods=['POST'])
@login_required
def add_comment(course_id):
    content = request.form.get("content")
    parent_id = request.form.get("parent_id")

    if not content.strip():
        # Lỗi -> quay lại trang study với query error
        return redirect(url_for("study", course_id=course_id, msg="empty"))

    comment = Comment(
        course_id=course_id,
        user_id=current_user.id,
        content=content.strip(),
        parent_id=parent_id if parent_id else None
    )
    db.session.add(comment)
    db.session.commit()

    # Thành công -> quay lại study với query success
    return redirect(url_for("study", course_id=course_id, msg="success"))




@app.route("/instructor/course/<int:course_id>/edit", methods=["GET"])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        return "Bạn không có quyền chỉnh sửa khóa học này", 403

    modules = Module.query.filter_by(course_id=course_id).all()
    comments = Comment.query.filter_by(course_id=course_id).order_by(Comment.created_at.desc()).all()

    return render_template("course_edit.html",
                           course=course,
                           modules=modules,
                           comments=comments)


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and current_user.id != comment.course.instructor_id:
        return jsonify({"status": "error", "message": "Không có quyền xóa"}), 403

    for reply in comment.replies:
        db.session.delete(reply)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"status": "success"})


@app.route('/instructor/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def instructor_delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)


    if current_user.id != comment.user_id and current_user.id != comment.course.instructor_id:
        return jsonify({"status": "error", "message": "Bạn không có quyền xoá bình luận này"}), 403


    if comment.parent_id is None:
        for reply in comment.replies:
            db.session.delete(reply)

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"status": "success", "message": "Xóa bình luận và các trả lời thành công"})




@app.route('/instructor/course/<int:course_id>/comment', methods=['POST'])
@login_required
def instructor_add_comment(course_id):
    course = Course.query.get_or_404(course_id)


    if current_user.id != course.instructor_id:
        return jsonify({"status": "error", "message": "Bạn không có quyền bình luận ở đây"}), 403

    content = request.form.get("content")
    parent_id = request.form.get("parent_id")

    if not content or not content.strip():
        return jsonify({"status": "error", "message": "Nội dung không được để trống"}), 400

    comment = Comment(
        course_id=course.id,
        user_id=current_user.id,
        content=content.strip(),
        parent_id=parent_id if parent_id else None
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "status": "success",
        "comment": {
            "id": comment.id,
            "course_id": course.id,
            "username": current_user.name,
            "is_current_user": True,
            "content": comment.content,
            "created_at": comment.created_at.strftime("%d/%m/%Y %H:%M")
        }
    })



@app.route("/instructor/course/<int:course_id>/discussion")
@login_required
def instructor_discussion(course_id):
    course = Course.query.get_or_404(course_id)

    if current_user.id != course.instructor_id:
        flash("Bạn không có quyền xem thảo luận khoá học này!", "danger")
        return redirect(url_for("study", course_id=course.id))

    page = request.args.get("page", 1, type=int)
    comments = Comment.query.filter_by(course_id=course.id, parent_id=None) \
                .order_by(Comment.created_at.desc()) \
                .paginate(page=page, per_page=5)

    return render_template(
        "instructor_discussion.html",
        course=course,
        comments=comments
    )

@app.route("/api/instructor/course/<int:course_id>/comments")
@login_required
def api_instructor_comments(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.id != course.instructor_id:
        return jsonify({"status": "error", "message": "Không có quyền"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = 5
    pagination = Comment.query.filter_by(course_id=course.id, parent_id=None) \
        .order_by(Comment.created_at.desc()) \
        .paginate(page=page, per_page=per_page)

    comments_data = []
    for cmt in pagination.items:
        comments_data.append({
            "id": cmt.id,
            "username": cmt.user.name,
            "is_current_user": (cmt.user_id == current_user.id),
            "content": cmt.content,
            "created_at": cmt.created_at.strftime("%d/%m/%Y %H:%M"),
            "replies": [
                {
                    "id": r.id,
                    "username": r.user.name,
                    "is_current_user": (r.user_id == current_user.id),
                    "content": r.content,
                    "created_at": r.created_at.strftime("%d/%m/%Y %H:%M"),
                } for r in cmt.replies
            ]
        })

    return jsonify({
        "status": "success",
        "comments": comments_data,
        "page": pagination.page,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_num": pagination.next_num,
        "prev_num": pagination.prev_num,
    })



@app.route('/course/<int:course_id>/review', methods=['POST'])
@login_required
def add_review(course_id):
    data = request.get_json()  # nhận JSON từ JS
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not rating or not comment:
        return jsonify({"status": "error", "message": "Bạn phải nhập đủ nội dung và chọn số sao."})

    review = Review(
        student_id=current_user.id,
        course_id=course_id,
        rating=int(rating),
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"status": "success", "message": "Đã gửi đánh giá."})




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
            is_available=False,
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

        # Kiểm tra khóa học tồn tại
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'message': 'Khóa học không tồn tại.'}), 404

        # Kiểm tra người dùng đã đăng ký khóa học này chưa
        existing_enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if existing_enrollment:
            return jsonify({'message': 'Bạn đã đăng ký khóa học này.'}), 400

        # Kiểm tra số lượng học viên đã đạt tối đa chưa
        if course.max_enrollment:  # Chỉ kiểm tra nếu có giới hạn số lượng
            current_enrollments = Enrollment.query.filter_by(course_id=course_id).count()
            if current_enrollments >= course.max_enrollment:
                return jsonify({
                    'message': 'Khóa học đã đạt số lượng đăng ký tối đa.',
                    'current_enrollments': current_enrollments,
                    'max_enrollment': course.max_enrollment
                }), 400
        
        # Tạo payment record
        payment = Payment(
            amount=course.price,  # Lấy giá từ course thay vì từ request
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

#
# @app.route('/api/course/<int:course_id>/reviews', methods=['GET'])
# def get_course_reviews(course_id):
#     try:
#         # Kiểm tra khóa học tồn tại
#         course = Course.query.get(course_id)
#         if not course:
#             return jsonify({'message': 'Không tìm thấy khóa học'}), 404
#
#         # Lấy tất cả reviews của khóa học, sắp xếp theo thời gian mới nhất
#         reviews = Review.query.filter_by(course_id=course_id).order_by(Review.create_at.desc()).all()
#
#         def format_review(review):
#             review_dict = {
#                 'id': review.id,
#                 'content': review.comment,
#                 'rating': review.rating,
#                 'created_at': review.create_at.isoformat() if review.create_at else None,
#                 'updated_at': review.update_at.isoformat() if review.update_at else None,
#                 'user': {
#                     'id': review.reviewer.id,
#                     'name': review.reviewer.name,
#                     'avatar_url': review.reviewer.avatar_url
#                 }
#             }
#             return review_dict
#
#         review_list = [format_review(review) for review in reviews]
#
#         return jsonify(review_list), 200
#
#     except Exception as e:
#         return jsonify({'message': 'Lỗi server khi lấy đánh giá'}), 500
#
#
# @app.route('/api/review/<int:course_id>', methods=['POST'])
# @login_required
# def create_review(course_id):
#     try:
#         # Kiểm tra khóa học tồn tại
#         course = Course.query.get(course_id)
#         if not course:
#             return jsonify({'message': 'Không tìm thấy khóa học'}), 404
#
#         # Kiểm tra user đã đăng ký khóa học chưa
#         enrollment = Enrollment.query.filter_by(
#             student_id=current_user.id,
#             course_id=course_id
#         ).first()
#         if not enrollment:
#             return jsonify({'message': 'Bạn chưa đăng ký khóa học này'}), 403
#
#         # Kiểm tra user đã review khóa học này chưa
#         existing_review = Review.query.filter_by(
#             student_id=current_user.id,
#             course_id=course_id
#         ).first()
#         if existing_review:
#             return jsonify({'message': 'Bạn đã đánh giá khóa học này rồi'}), 400
#
#         data = request.json
#         content = data.get('content')
#         rating = data.get('rating')
#
#         # Validate dữ liệu
#         if not content or not rating:
#             return jsonify({'message': 'Thiếu nội dung hoặc điểm đánh giá'}), 400
#
#         if not isinstance(rating, int) or rating < 1 or rating > 5:
#             return jsonify({'message': 'Điểm đánh giá phải từ 1-5'}), 400
#
#         # Tạo review mới
#         review = Review(
#             student_id=current_user.id,
#             course_id=course_id,
#             comment=content,
#             rating=rating,
#             create_at=datetime.utcnow()
#         )
#         db.session.add(review)
#         db.session.commit()
#
#         return jsonify({
#             'message': 'Đã thêm đánh giá thành công',
#             'review': {
#                 'id': review.id,
#                 'content': review.comment,
#                 'rating': review.rating,
#                 'created_at': review.create_at.isoformat()
#             }
#         }), 201
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi thêm đánh giá'}), 500
#
#
# @app.route('/api/review/<int:review_id>', methods=['PUT'])
# @login_required
# def update_review(review_id):
#     try:
#         # Kiểm tra review tồn tại và thuộc về user hiện tại
#         review = Review.query.filter_by(
#             id=review_id,
#             student_id=current_user.id
#         ).first()
#
#         if not review:
#             return jsonify({'message': 'Không tìm thấy đánh giá hoặc không có quyền sửa'}), 404
#
#         data = request.json
#         content = data.get('content')
#         rating = data.get('rating')
#
#         # Validate dữ liệu
#         if not content or not rating:
#             return jsonify({'message': 'Thiếu nội dung hoặc điểm đánh giá'}), 400
#
#         if not isinstance(rating, int) or rating < 1 or rating > 5:
#             return jsonify({'message': 'Điểm đánh giá phải từ 1-5'}), 400
#
#         # Cập nhật review
#         review.comment = content
#         review.rating = rating
#         review.update_at = datetime.utcnow()  # Cập nhật thời gian sửa
#         db.session.commit()
#
#         return jsonify({
#             'message': 'Đã cập nhật đánh giá thành công',
#             'review': {
#                 'id': review.id,
#                 'content': review.comment,
#                 'rating': review.rating,
#                 'created_at': review.create_at.isoformat(),
#                 'updated_at': review.update_at.isoformat() if review.update_at else None
#             }
#         }), 200
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi cập nhật đánh giá'}), 500
#
#
# @app.route('/api/review/<int:review_id>', methods=['DELETE'])
# @login_required
# def delete_review(review_id):
#     try:
#         # Kiểm tra review tồn tại và thuộc về user hiện tại
#         review = Review.query.filter_by(
#             id=review_id,
#             student_id=current_user.id
#         ).first()
#
#         if not review:
#             return jsonify({'message': 'Không tìm thấy đánh giá hoặc không có quyền xóa'}), 404
#
#         # Xóa review
#         db.session.delete(review)
#         db.session.commit()
#
#         return jsonify({'message': 'Đã xóa đánh giá thành công'}), 200
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi xóa đánh giá'}), 500
#
#
# @app.route('/api/course/<int:course_id>/comments', methods=['GET'])
# def get_course_comments(course_id):
#     try:
#         course = Course.query.get(course_id)
#         if not course:
#             return jsonify({'message': 'Không tìm thấy khóa học'}), 404
#
#         # Chỉ lấy các comment gốc (không có parent_id)
#         root_comments = Comment.query.filter_by(
#             course_id=course_id,
#             parent_id=None
#         ).order_by(Comment.created_at.desc()).all()
#
#         def format_comment(comment):
#             comment_dict = {
#                 'id': comment.id,
#                 'content': comment.content,
#                 'created_at': comment.created_at.isoformat(),
#                 'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
#                 'user': {
#                     'id': comment.user.id,
#                     'name': comment.user.name,
#                     'avatar_url': comment.user.avatar_url
#                 },
#                 'replies': [format_comment(reply) for reply in comment.replies]
#             }
#             return comment_dict
#
#         comment_list = [format_comment(comment) for comment in root_comments]
#         return jsonify(comment_list), 200
#
#     except Exception as e:
#         return jsonify({'message': 'Lỗi server khi lấy bình luận'}), 500
#
#
# @app.route('/api/comment/<int:course_id>', methods=['POST'])
# @login_required
# def create_comment(course_id):
#     try:
#         course = Course.query.get(course_id)
#         if not course:
#             return jsonify({'message': 'Không tìm thấy khóa học'}), 404
#
#         data = request.json
#         content = data.get('content')
#         parent_id = data.get('parent_id')  # ID của comment cha nếu là reply
#
#         if not content or not content.strip():
#             return jsonify({'message': 'Nội dung bình luận không được để trống'}), 400
#
#         # Nếu là reply, kiểm tra comment cha tồn tại
#         if parent_id:
#             parent_comment = Comment.query.get(parent_id)
#             if not parent_comment or parent_comment.course_id != course_id:
#                 return jsonify({'message': 'Không tìm thấy bình luận gốc'}), 404
#             # Không cho phép reply của reply (chỉ 1 cấp)
#             if parent_comment.parent_id is not None:
#                 return jsonify({'message': 'Không thể trả lời comment reply'}), 400
#
#         comment = Comment(
#             user_id=current_user.id,
#             course_id=course_id,
#             parent_id=parent_id,
#             content=content.strip(),
#             created_at=datetime.utcnow()
#         )
#         db.session.add(comment)
#         db.session.commit()
#
#         return jsonify({
#             'message': 'Đã thêm bình luận thành công',
#             'comment': {
#                 'id': comment.id,
#                 'content': comment.content,
#                 'parent_id': comment.parent_id,
#                 'created_at': comment.created_at.isoformat(),
#                 'user': {
#                     'id': current_user.id,
#                     'name': current_user.name,
#                     'avatar_url': current_user.avatar_url
#                 }
#             }
#         }), 201
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi thêm bình luận'}), 500
#
#
# @app.route('/api/comment/<int:comment_id>', methods=['PUT'])
# @login_required
# def update_comment(comment_id):
#     try:
#         # Kiểm tra comment tồn tại và thuộc về user hiện tại
#         comment = Comment.query.filter_by(
#             id=comment_id,
#             user_id=current_user.id
#         ).first()
#
#         if not comment:
#             return jsonify({'message': 'Không tìm thấy bình luận hoặc không có quyền sửa'}), 404
#
#         # Lấy nội dung mới
#         data = request.json
#         content = data.get('content')
#
#         if not content or not content.strip():
#             return jsonify({'message': 'Nội dung bình luận không được để trống'}), 400
#
#         # Cập nhật comment
#         comment.content = content.strip()
#         comment.updated_at = datetime.utcnow()
#         db.session.commit()
#
#         return jsonify({
#             'message': 'Đã cập nhật bình luận thành công',
#             'comment': {
#                 'id': comment.id,
#                 'content': comment.content,
#                 'created_at': comment.created_at.isoformat(),
#                 'updated_at': comment.updated_at.isoformat()
#             }
#         }), 200
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi cập nhật bình luận'}), 500
#
#
# @app.route('/api/comment/<int:comment_id>', methods=['DELETE'])
# @login_required
# def delete_comment(comment_id):
#     try:
#         # Kiểm tra comment tồn tại và thuộc về user hiện tại
#         comment = Comment.query.filter_by(
#             id=comment_id,
#             user_id=current_user.id
#         ).first()
#
#         if not comment:
#             return jsonify({'message': 'Không tìm thấy bình luận hoặc không có quyền xóa'}), 404
#
#         # Xóa tất cả replies của comment này trước
#         Comment.query.filter_by(parent_id=comment_id).delete()
#
#         # Sau đó xóa comment gốc
#         db.session.delete(comment)
#         db.session.commit()
#
#         return jsonify({'message': 'Đã xóa bình luận và các phản hồi thành công'}), 200
#
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Lỗi server khi xóa bình luận'}), 500

if __name__ == '__main__':
    app.run(port=8080, debug=True,use_reloader=False)