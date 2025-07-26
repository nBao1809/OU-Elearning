// static/js/cart.js - EduOnline CLEAN FIXED

let allCourses = [];
let selectedCourseId = null;

// Lấy tham số URL
function getParameterByName(name) {
    const url = window.location.href;
    const params = new URLSearchParams(new URL(url).search);
    return params.get(name);
}

// Gọi API lấy danh sách khóa học
async function fetchCourses() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        allCourses = data;
        return data;
    } catch (error) {
        console.error('Lỗi khi tải khóa học:', error);
        return [];
    }
}

// Xử lý thanh toán
async function processPurchase(event) {
    event.preventDefault();

    const courseId = document.getElementById('courseId').value;
    const paymentMethod = document.getElementById('paymentMethod') ? document.getElementById('paymentMethod').value : 'vnpay';

    if (!courseId) {
        alert('Không tìm thấy khóa học.');
        return;
    }

    const course = allCourses.find(c => c.id === parseInt(courseId));
    if (!course) {
        alert('Không tìm thấy thông tin khóa học.');
        return;
    }

    // Hiển thị trạng thái
    const statusDiv = document.getElementById('paymentStatus');
    statusDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> Đang xử lý thanh toán...</p>';

    try {
        const res = await fetch('/api/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: parseInt(courseId),
                amount: course.price,
                payment_method: paymentMethod,
                transaction_code: 'TXN-' + Date.now()
            })
        });

        if (!res.ok) {
            if (res.status === 401) {
                alert('Bạn cần đăng nhập để mua khóa học.');
                window.location.href = '/login';
                return;
            }
            throw new Error('Lỗi khi xử lý thanh toán.');
        }

        const data = await res.json();

        // Xác nhận thanh toán
        await fetch('/api/payment/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payment_id: data.payment_id })
        });

        // Hiển thị thành công
        statusDiv.innerHTML = `
            <div style="color: green; text-align: center;">
                <i class="fas fa-check-circle"></i>
                <h3>Thanh toán thành công!</h3>
                <p>Bạn đã mua khóa học "${course.title}" thành công.</p>
                <button class="btn btn-primary" onclick="goToCourse()">
                    <i class="fas fa-play"></i> Bắt đầu học
                </button>
            </div>
        `;
    } catch (error) {
        console.error(error);
        statusDiv.innerHTML = `
            <div style="color: red; text-align: center;">
                <i class="fas fa-exclamation-circle"></i>
                <p>Đã xảy ra lỗi khi thanh toán, vui lòng thử lại.</p>
            </div>
        `;
    }
}

// Chuyển đến giao diện học khóa học
function goToCourse() {
    window.location.href = '/my-courses';
}

// Khởi tạo khi load trang
document.addEventListener('DOMContentLoaded', async () => {
    await fetchCourses();

    const courseIdParam = getParameterByName('course_id');
    if (courseIdParam) {
        const courseIdInput = document.getElementById('courseId');
        if (courseIdInput) {
            courseIdInput.value = courseIdParam;
        }
    }
});
