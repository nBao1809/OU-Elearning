from EduApp import app, db
from models import User, Course, UserRoleEnum, Module, Lesson, Payment, Enrollment, Review,Comment
from datetime import datetime, timedelta, timezone



if __name__ == '__main__':

    with app.app_context():
        # Xóa dữ liệu cũ và tạo lại bảng
        db.drop_all()
        db.create_all()
        admin = User(name="Admin User", email="admin@edu.vn", password="admin123", role=UserRoleEnum.ADMIN)
        instructor = User(name="Nguyễn Văn Giảng", email="teacher@edu.vn", password="teacher123",
                          role=UserRoleEnum.INSTRUCTOR)
        student = User(name="Trần Thị Học", email="student@edu.vn", password="student123", role=UserRoleEnum.STUDENT)

        db.session.add_all([admin, instructor, student])
        db.session.commit()
        image_url = "https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg"

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
                create_at=datetime(2025, 6, 10, tzinfo=timezone.utc)
            ),
            Course(
                title="Thành thạo chứng khoán",
                description="Khóa học Python số 2 giúp bạn làm chủ lập trình.",
                price=299000,
                instructor_id=instructor.id,
                thumbnail_id=image_url,
                level="Beginner",
                is_published=True,
                is_available=True,
                max_enrollment=100,
                create_at=datetime(2025, 6, 10, tzinfo=timezone.utc)
            ),
            Course(
                title="Bí kip làm giàu",
                description="Khóa học Python số 3 giúp bạn làm chủ lập trình.",
                price=299000,
                instructor_id=instructor.id,
                thumbnail_id=image_url,
                level="Intermediate",
                is_published=True,
                is_available=True,
                max_enrollment=100,
                create_at=datetime(2025, 6, 16, tzinfo=timezone.utc)
            ),
            Course(
                title="Nấu ăn trung cấp",
                description="Khóa học Python số 4 giúp bạn làm chủ lập trình.",
                price=0,
                instructor_id=instructor.id,
                thumbnail_id=image_url,
                level="Intermediate",
                is_published=True,
                is_available=True,
                max_enrollment=100,
                create_at=datetime(2025, 6, 15, tzinfo=timezone.utc)
            ),
            Course(
                title="OOP",
                description="Khóa học Python số 5 giúp bạn làm chủ lập trình.",
                price=0,
                instructor_id=instructor.id,
                thumbnail_id=image_url,
                level="Advanced",
                is_published=True,
                is_available=True,
                max_enrollment=100,
                create_at=datetime(2025, 6, 13, tzinfo=timezone.utc)
            ),
        ]

        db.session.add_all(mock_courses)
        db.session.commit()
        # 2️⃣ Tạo COURSE
        course = Course(
            title="Flask Web Fullstack",
            description="Khóa học Flask Web Fullstack từ cơ bản đến nâng cao, xây dựng dự án thực tế.",
            price=499000,
            instructor_id=instructor.id,
            thumbnail_id="https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg",
            level="Beginner",
            is_published=True,
            is_available=True,
            max_enrollment=100,
            create_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db.session.add(course)
        db.session.commit()

        # 3️⃣ Tạo MODULES & LESSONS
        module1 = Module(course_id=course.id, title="Giới thiệu Flask", ordering=1)
        module2 = Module(course_id=course.id, title="CRUD với Flask SQLAlchemy", ordering=2)
        db.session.add_all([module1, module2])
        db.session.commit()

        lesson1 = Lesson(module_id=module1.id, title="Flask là gì?", ordering=1, content_type="video",
                         video_url="https://www.youtube.com/watch?v=Z1RJmh_OqeA")
        lesson2 = Lesson(module_id=module1.id, title="Cài đặt môi trường", ordering=2, content_type="text",
                         text_content="Cài đặt Python, pip và Flask")
        lesson3 = Lesson(module_id=module2.id, title="Tạo Model với SQLAlchemy", ordering=1, content_type="video",
                         video_url="https://www.youtube.com/watch?v=cYWiDiIUxQc")
        db.session.add_all([lesson1, lesson2, lesson3])
        db.session.commit()

        # 4️⃣ Tạo PAYMENT & ENROLLMENT
        payment = Payment(amount=499000, payment_method="VNPay", payment_status="Success", transaction_code="TXN123456",
                          paid_at=datetime.now(timezone.utc))
        db.session.add(payment)
        db.session.commit()

        enrollment = Enrollment(student_id=student.id, course_id=course.id, payment_id=payment.id, progress_percent=0)
        db.session.add(enrollment)
        db.session.commit()

        # 5️⃣ Tạo REVIEW
        review = Review(student_id=student.id, course_id=course.id, rating=5,
                        comment="Khóa học cực kỳ dễ hiểu, thầy giảng hay!", create_at=datetime.now(timezone.utc))
        db.session.add(review)
        db.session.commit()

        # 6️⃣ Tạo COMMENT + REPLY
        comment1 = Comment(course_id=course.id, user_id=student.id, content="Khóa học có hỗ trợ thực hành không?",
                           created_at=datetime.now(timezone.utc))
        db.session.add(comment1)
        db.session.commit()

        reply = Comment(course_id=course.id, user_id=instructor.id, parent_id=comment1.id,
                        content="Có em nhé, thầy sẽ hướng dẫn trong từng bài.", created_at=datetime.now(timezone.utc))
        db.session.add(reply)
        db.session.commit()