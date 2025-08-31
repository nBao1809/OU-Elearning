import hashlib

from models import User, Course, Review, Comment, Enrollment, Payment, UserRoleEnum, Module, Lesson, Progress
from flask_admin import Admin, BaseView, expose, AdminIndexView
from EduApp import app, db
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from flask import redirect
from wtforms import PasswordField
from sqlalchemy import func


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return True  # Cho phép truy cập trang đăng nhập

    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not hasattr(current_user, 'role') or current_user.role != UserRoleEnum.ADMIN:
            return self.render('admin/index.html')  # Hiển thị form đăng nhập
        return super(MyAdminIndexView, self).index()  # Hiển thị trang admin khi đã đăng nhập

admin = Admin(app=app, name='OU E-Learning Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and hasattr(current_user, 'role') and current_user.role == UserRoleEnum.ADMIN


class UserView(AdminView):
    column_list = ['id', 'name', 'email', 'role', 'create_at']
    column_searchable_list = ['name', 'email']
    column_filters = ['role']
    can_export = True
    form_excluded_columns = ['password']  # Không hiện mật khẩu hash trong form
    form_extra_fields = {
        'new_password': PasswordField('Mật khẩu mới')
    }
    column_labels = {
        'name': 'Họ tên',
        'email': 'Email',
        'role': 'Vai trò',
        'create_at': 'Ngày tạo',
        'avatar_url': 'Ảnh đại diện'
    }

    def on_model_change(self, form, model, is_created):
        if is_created:
            if form.password.data:
                model.password = str(hashlib.md5(form.password.data.encode('utf-8')).hexdigest())
            if not model.role:
                model.role = UserRoleEnum.STUDENT
        else:
            if form.password.data:
                model.password = str(hashlib.md5(form.password.data.encode('utf-8')).hexdigest())

        # Kiểm tra không cho phép hạ cấp admin cuối cùng
        if model.role != UserRoleEnum.ADMIN:
            admin_count = User.query.filter_by(role=UserRoleEnum.ADMIN).count()
            if admin_count <= 1:
                raise ValueError('Không thể hạ cấp admin cuối cùng')

        self.change = super().on_model_change(form, model, is_created)
        return self.change


class CourseView(AdminView):
    column_list = ['id', 'title', 'price', 'instructor_id', 'level', 'is_published', 'is_available', 'max_enrollment', 'create_at', 'student_count', 'total_revenue']
    column_searchable_list = ['title', 'description']
    column_filters = ['level', 'is_published', 'is_available', 'instructor_id']
    column_editable_list = ['title', 'price', 'is_published', 'is_available', 'max_enrollment']
    can_export = True
    column_labels = {
        'title': 'Tên khóa học',
        'instructor': 'Giảng viên',
        'price': 'Giá',
        'level': 'Cấp độ',
        'is_published': 'Đã xuất bản',
        'create_at': 'Ngày tạo',
        'student_count': 'Số học viên',
        'total_revenue': 'Doanh thu'
    }

    def _student_count(view, context, model, name):
        return len(model.enrollments)

    def _total_revenue(view, context, model, name):
        total = db.session.query(func.sum(Payment.amount))\
            .join(Enrollment)\
            .filter(Enrollment.course_id == model.id)\
            .filter(Payment.payment_status == 'Success')\
            .scalar()
        return '{:,.0f} VND'.format(total if total else 0)

    column_formatters = {
        'student_count': _student_count,
        'total_revenue': _total_revenue
    }


class ReviewView(AdminView):
    column_list = ['id', 'student_id', 'course_id', 'rating', 'comment', 'create_at', 'update_at']
    column_searchable_list = ['comment']
    column_filters = ['rating', 'student_id', 'course_id']
    can_export = True
    can_create = False
    column_labels = {
        'student_id': 'Học viên',
        'course_id': 'Khóa học',
        'rating': 'Đánh giá',
        'comment': 'Nội dung',
        'create_at': 'Ngày tạo',
        'update_at': 'Ngày cập nhật'
    }


class CommentView(AdminView):
    column_list = ['id', 'user_id', 'course_id', 'content', 'parent_id', 'created_at', 'updated_at']
    column_searchable_list = ['content']
    column_filters = ['user_id', 'course_id']
    can_export = True
    can_create = False
    column_labels = {
        'user_id': 'Người dùng',
        'course_id': 'Khóa học',
        'content': 'Nội dung',
        'parent_id': 'Trả lời cho',
        'created_at': 'Ngày tạo',
        'updated_at': 'Ngày cập nhật'
    }


class EnrollmentView(AdminView):
    column_list = ['id', 'student_id', 'course_id', 'enrolled_at', 'payment_id', 'progress_percent']
    column_filters = ['student_id', 'course_id']
    can_export = True
    can_create = False
    column_labels = {
        'student_id': 'Học viên',
        'course_id': 'Khóa học',
        'enrolled_at': 'Ngày đăng ký',
        'payment_id': 'Thanh toán',
        'progress_percent': 'Tiến độ (%)'
    }


class PaymentView(AdminView):
    column_list = ['id', 'amount', 'payment_method', 'payment_status', 'transaction_code', 'created_at', 'paid_at']
    column_filters = ['payment_status', 'payment_method']
    can_export = True
    can_create = False
    can_edit = False
    column_labels = {
        'amount': 'Số tiền',
        'payment_method': 'Phương thức',
        'payment_status': 'Trạng thái',
        'transaction_code': 'Mã giao dịch',
        'created_at': 'Ngày tạo',
        'paid_at': 'Ngày thanh toán'
    }


class AuthenticatedView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated


class LogoutView(AuthenticatedView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/admin')


# Thêm các view vào admin
admin.add_view(UserView(User, db.session, name='Người dùng'))
admin.add_view(CourseView(Course, db.session, name='Khóa học'))
admin.add_view(ReviewView(Review, db.session, name='Đánh giá'))
admin.add_view(CommentView(Comment, db.session, name='Bình luận'))
admin.add_view(EnrollmentView(Enrollment, db.session, name='Đăng ký học'))
admin.add_view(PaymentView(Payment, db.session, name='Thanh toán'))

class ProgressView(AdminView):
    column_list = ['id', 'student_id', 'lesson_id', 'enrollment_id', 'complete_at']
    column_filters = ['student_id', 'lesson_id', 'enrollment_id']
    can_export = True
    can_create = False
    column_labels = {
        'student_id': 'Học viên',
        'lesson_id': 'Bài học',
        'enrollment_id': 'Đăng ký',
        'complete_at': 'Ngày hoàn thành'
    }

admin.add_view(ProgressView(Progress, db.session, name='Tiến độ học tập'))

class ModuleView(AdminView):
    column_list = ['id', 'course_id', 'title', 'ordering']
    column_filters = ['course_id']
    column_searchable_list = ['title']
    column_editable_list = ['title', 'ordering']
    can_export = True
    column_labels = {
        'course_id': 'Khóa học',
        'title': 'Tên chương',
        'ordering': 'Thứ tự'
    }


class LessonView(AdminView):
    column_list = ['id', 'module_id', 'title', 'ordering', 'content_type', 'video_url', 'file_url']
    column_filters = ['module_id', 'content_type']
    column_searchable_list = ['title']
    column_editable_list = ['title', 'ordering', 'content_type']
    can_export = True
    column_labels = {
        'module_id': 'Chương',
        'title': 'Tên bài học',
        'ordering': 'Thứ tự',
        'content_type': 'Loại nội dung',
        'video_url': 'URL Video',
        'file_url': 'URL Tài liệu',
        'text_content': 'Nội dung'
    }

admin.add_view(ModuleView(Module, db.session, name='Chương'))
admin.add_view(LessonView(Lesson, db.session, name='Bài học'))
admin.add_view(LogoutView(name='Đăng xuất'))
