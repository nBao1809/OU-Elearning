# Tài liệu API (Tiếng Việt)

## 1. APIs Xác thực và Quản lý User

### Quản lý tài khoản
- **POST /login**
  - Chức năng: Đăng nhập vào hệ thống
  - Yêu cầu gửi lên: email, password
  - Trả về: Thông tin user và trạng thái đăng nhập
  
- **GET /logout**
  - Chức năng: Đăng xuất khỏi hệ thống
  - Kết quả: Chuyển về trang chủ
  
- **GET /api/auth/check**
  - Chức năng: Kiểm tra người dùng đã đăng nhập chưa
  - Trả về: Trạng thái đăng nhập

### Quản lý thông tin cá nhân
- **POST /register**
  - Chức năng: Đăng ký tài khoản mới
  - Yêu cầu: name, email, password, xác nhận password
  - Tùy chọn: role (mặc định: STUDENT), ảnh đại diện

- **GET /user/profile**
  - Chức năng: Xem thông tin cá nhân
  - Yêu cầu: Đã đăng nhập

- **PUT /user/profile**
  - Chức năng: Cập nhật thông tin cá nhân
  - Yêu cầu: Đã đăng nhập
  - Có thể sửa: tên, mật khẩu, ảnh đại diện

- **DELETE /user/profile**
  - Chức năng: Xóa tài khoản
  - Yêu cầu: Đã đăng nhập và nhập mật khẩu xác nhận

## 2. APIs Quản lý Khóa học

### Xem khóa học (Công khai)
- **GET /api/courses**
  - Chức năng: Xem danh sách khóa học
  - Nếu đã đăng nhập: Hiện khóa học chưa đăng ký
  - Chưa đăng nhập: Hiện tất cả khóa học công khai

- **GET /course/{course_id}**
  - Chức năng: Xem chi tiết một khóa học
  - Hiển thị: Thông tin khóa học, danh sách module, đánh giá và bình luận

- **GET /api/course/{course_id}/modules**
  - Chức năng: Xem danh sách module trong khóa học

- **GET /api/module/{module_id}/lessons**
  - Chức năng: Xem danh sách bài học trong module

- **GET /api/lesson/{lesson_id}**
  - Chức năng: Xem chi tiết bài học
  - Yêu cầu: Đã đăng nhập và đã đăng ký khóa học

### Quản lý khóa học (Dành cho Giảng viên)
- **GET /instructor/courses**
  - Chức năng: Xem danh sách khóa học mình đang dạy
  - Yêu cầu: Là giảng viên

- **GET /instructor/course/{course_id}**
  - Chức năng: Xem chi tiết khóa học của mình
  - Yêu cầu: Là giảng viên của khóa học đó

- **POST /instructor/course**
  - Chức năng: Tạo khóa học mới
  - Yêu cầu nhập: tiêu đề, mô tả, giá, cấp độ
  - Tùy chọn: ảnh thu nhỏ, số học viên tối đa

- **PUT /instructor/course/{course_id}**
  - Chức năng: Cập nhật thông tin khóa học
  - Có thể sửa: tiêu đề, mô tả, giá, ảnh, trạng thái,...

- **DELETE /instructor/course/{course_id}**
  - Chức năng: Xóa khóa học
  - Yêu cầu: Là giảng viên của khóa học

- **GET /instructor/course/{course_id}/students**
  - Chức năng: Xem danh sách học viên đã đăng ký
  - Hiển thị: Thông tin học viên và tiến độ học tập

### Quản lý Module
- **POST /api/course/{course_id}/module**
  - Chức năng: Thêm module mới vào khóa học
  - Yêu cầu nhập: tiêu đề
  - Tự động sắp xếp thứ tự

- **PUT /api/module/{module_id}**
  - Chức năng: Cập nhật thông tin module
  - Có thể sửa: tiêu đề, thứ tự

- **DELETE /api/module/{module_id}**
  - Chức năng: Xóa module

### Quản lý Bài học
- **POST /api/module/{module_id}/lesson**
  - Chức năng: Thêm bài học vào module
  - Yêu cầu nhập: tiêu đề, loại nội dung
  - Tùy chọn: link video, file, nội dung text

- **PUT /api/lesson/{lesson_id}**
  - Chức năng: Cập nhật bài học
  - Có thể sửa: tiêu đề, nội dung, thứ tự,...

- **DELETE /api/lesson/{lesson_id}**
  - Chức năng: Xóa bài học

## 3. APIs Đăng ký và Theo dõi Tiến độ

### Đăng ký khóa học
- **POST /api/register_free_course/{course_id}**
  - Chức năng: Đăng ký khóa học miễn phí
  - Yêu cầu: Đã đăng nhập

### Theo dõi tiến độ
- **GET /api/progress/{course_id}**
  - Chức năng: Xem tiến độ học tập của khóa học
  - Hiển thị: Phần trăm hoàn thành, ngày đăng ký, tổng số module

- **POST /api/progress/update**
  - Chức năng: Cập nhật hoàn thành bài học
  - Yêu cầu: ID khóa học và ID bài học
  - Tự động: Cập nhật phần trăm hoàn thành khóa học

- **GET /student/progress/{course_id}**
  - Chức năng: Xem chi tiết tiến độ học tập
  - Hiển thị: Thông tin chi tiết về tiến độ theo từng module và bài học

- **GET /my-courses**
  - Chức năng: Xem danh sách khóa học đã đăng ký
  - Hiển thị: 
    - Danh sách khóa học
    - Tổng số khóa học
    - Tiến độ trung bình
    - Số khóa học đang học

## 4. APIs Thanh toán

### Xử lý thanh toán
- **POST /api/payment**
  - Chức năng: Tạo giao dịch thanh toán khóa học
  - Yêu cầu nhập: số tiền, ID khóa học
  - Tùy chọn: ngân hàng, ngôn ngữ

- **GET /payment-history**
  - Chức năng: Xem lịch sử thanh toán

- **GET /api/payment/{payment_id}**
  - Chức năng: Xem chi tiết giao dịch

### Tích hợp VNPay
- **GET /api/payment/ipn**
  - Chức năng: Nhận thông báo kết quả từ VNPay
  
- **GET /payment/return**
  - Chức năng: Xử lý sau khi thanh toán xong

## 5. APIs Đánh giá và Bình luận

### Đánh giá khóa học
- **GET /api/course/{course_id}/reviews**
  - Chức năng: Xem đánh giá của khóa học
  - Hiển thị: Danh sách đánh giá với thông tin người đánh giá

- **POST /api/review/{course_id}**
  - Chức năng: Đăng đánh giá mới
  - Yêu cầu: Đã đăng nhập và đã đăng ký khóa học
  - Yêu cầu nhập: nội dung, điểm đánh giá (1-5)
  - Lưu ý: Mỗi học viên chỉ được đánh giá một lần

- **PUT /api/review/{review_id}**
  - Chức năng: Sửa đánh giá của mình
  - Yêu cầu: Là người viết đánh giá
  - Có thể sửa: nội dung và điểm đánh giá

- **DELETE /api/review/{review_id}**
  - Chức năng: Xóa đánh giá của mình
  - Yêu cầu: Là người viết đánh giá

### Bình luận
- **GET /api/course/{course_id}/comments**
  - Chức năng: Xem bình luận của khóa học

- **POST /api/comment/{course_id}**
  - Chức năng: Thêm bình luận mới
  - Yêu cầu: Đã đăng nhập
  - Yêu cầu nhập: nội dung
  - Tùy chọn: parent_id (ID bình luận gốc nếu là reply)

- **PUT /api/comment/{comment_id}**
  - Chức năng: Sửa bình luận
  - Yêu cầu: Đã đăng nhập và là người viết bình luận
  - Yêu cầu nhập: nội dung mới

- **DELETE /api/comment/{comment_id}**
  - Chức năng: Xóa bình luận
  - Yêu cầu: Đã đăng nhập và là người viết bình luận
  - Lưu ý: Sẽ xóa cả các reply của bình luận này
