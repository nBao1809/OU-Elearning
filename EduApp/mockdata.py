from EduApp import app, db
from models import User, Course, Category, UserRoleEnum
import hashlib
from datetime import datetime, timezone

with app.app_context():
    db.drop_all()
    db.create_all()

    # ====== 1. Tạo USERS (hash password bằng MD5) ======
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

    # ====== 2. Tạo CATEGORY ======
    cate1 = Category(name="Lập trình", description="Các khóa học về lập trình và phát triển phần mềm.")
    cate2 = Category(name="Kinh doanh", description="Kiến thức kinh doanh, tài chính và quản lý.")
    cate3 = Category(name="Nấu ăn", description="Các khóa học nấu ăn từ cơ bản đến nâng cao.")
    cate4 = Category(name="Phát triển cá nhân", description="Kỹ năng mềm và phát triển bản thân.")
    cate5 = Category(name="Thiết kế", description="Thiết kế đồ họa, UI/UX và sáng tạo.")

    db.session.add_all([cate1, cate2, cate3, cate4, cate5])
    db.session.commit()

    # ====== 3. Mock thumbnail URL (có thể thay bằng upload thật) ======
    image_url = "https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg"

    # ====== 4. Tạo COURSES ======
    mock_courses = [
        Course(
            title="Khóa học Python 1",
            description="Khóa học Python số 1 giúp bạn làm chủ lập trình.",
            price=199000,
            instructor_id=instructor.id,
            thumbnail_id=image_url,
            level="Intermediate",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime(2025, 6, 10, tzinfo=timezone.utc),
            category_id=cate1.id
        ),
        Course(
            title="Thành thạo chứng khoán",
            description="Khóa học chứng khoán giúp bạn đầu tư thông minh.",
            price=299000,
            instructor_id=instructor.id,
            thumbnail_id=image_url,
            level="Beginner",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime(2025, 6, 10, tzinfo=timezone.utc),
            category_id=cate2.id
        ),
        Course(
            title="Bí kíp làm giàu",
            description="Chiến lược làm giàu và quản lý tài chính hiệu quả.",
            price=299000,
            instructor_id=instructor.id,
            thumbnail_id=image_url,
            level="Intermediate",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime(2025, 6, 16, tzinfo=timezone.utc),
            category_id=cate2.id
        ),
        Course(
            title="Nấu ăn trung cấp",
            description="Kỹ thuật nấu ăn nâng cao cho người đã có nền tảng.",
            price=0,
            instructor_id=instructor.id,
            thumbnail_id=image_url,
            level="Intermediate",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
            category_id=cate3.id
        ),
        Course(
            title="OOP",
            description="Lập trình hướng đối tượng từ cơ bản đến nâng cao.",
            price=0,
            instructor_id=instructor.id,
            thumbnail_id=image_url,
            level="Advanced",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime(2025, 6, 13, tzinfo=timezone.utc),
            category_id=cate1.id
        ),
    ]

    db.session.add_all(mock_courses)
    db.session.commit()

    print("✅ Mock data đã được tạo thành công!")
