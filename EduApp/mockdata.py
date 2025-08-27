from EduApp import app, db
from models import User, Course, Category, Module, Lesson, Comment, Review, UserRoleEnum
import hashlib
from datetime import datetime, timezone

with app.app_context():
    db.drop_all()
    db.create_all()

    # ====== 1. USERS ======
    admin = User(
        name="Admin User",
        email="admin@edu.vn",
        password=hashlib.md5("admin123".encode("utf-8")).hexdigest(),
        role=UserRoleEnum.ADMIN
    )
    instructor = User(
        name="Nguyễn Văn Giảng",
        email="teacher@edu.vn",
        password=hashlib.md5("teacher123".encode("utf-8")).hexdigest(),
        role=UserRoleEnum.INSTRUCTOR
    )
    student = User(
        name="Trần Thị Học",
        email="student@edu.vn",
        password=hashlib.md5("student123".encode("utf-8")).hexdigest(),
        role=UserRoleEnum.STUDENT
    )

    db.session.add_all([admin, instructor, student])
    db.session.commit()

    # ====== 2. CATEGORY ======
    cate1 = Category(name="Lập trình", description="Khoá học về lập trình.")
    cate2 = Category(name="Kinh doanh", description="Khoá học về kinh doanh.")
    cate3 = Category(name="Nấu ăn", description="Khoá học về nấu ăn.")
    db.session.add_all([cate1, cate2, cate3])
    db.session.commit()

    # ====== 3. COURSES ======
    image_url = "https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg"

    python_course = Course(
        title="Python Cơ bản",
        description="Khoá học Python từ A-Z.",
        price=0,
        instructor_id=instructor.id,
        thumbnail_id=image_url,
        level="Beginner",
        is_published=True,
        is_available=True,
        max_enrollment=100,
        create_at=datetime(2025, 6, 10, tzinfo=timezone.utc),
        category_id=cate1.id
    )

    business_course = Course(
        title="Kinh doanh Online",
        description="Bí quyết bán hàng online thành công.",
        price=299000,
        instructor_id=instructor.id,
        thumbnail_id=image_url,
        level="Intermediate",
        is_published=True,
        is_available=True,
        max_enrollment=100,
        create_at=datetime(2025, 6, 12, tzinfo=timezone.utc),
        category_id=cate2.id
    )

    cooking_course = Course(
        title="Nấu ăn gia đình",
        description="Các món ăn ngon cho gia đình.",
        price=199000,
        instructor_id=instructor.id,
        thumbnail_id=image_url,
        level="Beginner",
        is_published=True,
        is_available=True,
        max_enrollment=100,
        create_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        category_id=cate3.id
    )

    db.session.add_all([python_course, business_course, cooking_course])
    db.session.commit()

    # ====== 4. MODULES + LESSONS ======
    # Tạo module
    module1 = Module(course_id=python_course.id, title="Giới thiệu Python", ordering=1)
    module2 = Module(course_id=python_course.id, title="Cấu trúc dữ liệu", ordering=2)

    # Tạo lesson (chỉ video YouTube)
    lesson1 = Lesson(
        module=module1,
        title="Cài đặt môi trường",
        ordering=1,
        content_type="video",
        video_url="https://www.youtube.com/embed/KnWvZrngKYU"
    )
    lesson2 = Lesson(
        module=module1,
        title="Hello World",
        ordering=2,
        content_type="video",
        video_url="https://www.youtube.com/embed/kqtD5dpn9C8"
    )
    lesson3 = Lesson(
        module=module2,
        title="List & Tuple",
        ordering=1,
        content_type="video",
        video_url="https://www.youtube.com/embed/W8KRzm-HUcc"
    )

    # Lưu vào DB
    db.session.add_all([module1, module2, lesson1, lesson2, lesson3])
    db.session.commit()

    # ====== 5. COMMENTS ======
    comment1 = Comment(course_id=python_course.id, user_id=student.id,
                       content="Khoá học rất dễ hiểu, cảm ơn thầy!")
    comment2 = Comment(course_id=python_course.id, user_id=instructor.id,
                       content="Cảm ơn bạn đã ủng hộ!", parent=comment1)

    db.session.add_all([comment1, comment2])
    db.session.commit()

    # ====== 6. REVIEWS ======
    review1 = Review(student_id=student.id, course_id=python_course.id,
                     rating=5, comment="Khoá học tuyệt vời!")
    review2 = Review(student_id=student.id, course_id=business_course.id,
                     rating=4, comment="Khá hay, áp dụng được vào thực tế.")

    db.session.add_all([review1, review2])
    db.session.commit()

    print("✅ Mock data đã được tạo thành công!")