class ProgressView(AdminView):
    column_list = ['id', 'student', 'lesson', 'enrollment', 'complete_at']
    column_filters = ['student', 'lesson', 'enrollment']
    can_export = True
    can_create = False
    column_labels = {
        'student': 'Học viên',
        'lesson': 'Bài học',
        'enrollment': 'Đăng ký',
        'complete_at': 'Ngày hoàn thành'
    }

admin.add_view(ProgressView(Progress, db.session, name='Tiến độ học tập'))
