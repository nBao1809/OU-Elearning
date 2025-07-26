let allCourses = [];

// Lấy tham số từ URL
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

// Lấy ID khóa học từ các input hidden
function getCourseId() {
    const freeInput = document.getElementById('freeCourseId');
    const paidInput = document.getElementById('paidCourseId');
    return freeInput?.value || paidInput?.value || null;
}

// Đăng ký khóa học miễn phí
function registerFreeCourse(event) {
    event.preventDefault();
    const courseId = document.getElementById("freeCourseId").value;

    fetch(`/api/register_free_course/${courseId}`, {
        method: "POST",
        credentials: "include"
    })
    .then(async res => {
        if (res.ok) {
            alert("Đăng ký khóa học miễn phí thành công!");
            window.location.href = "/";
        } else if (res.status === 401) {
            alert("Bạn cần đăng nhập để đăng ký khóa học.");
            window.location.href = "/login";
        } else {
            // Nếu không ok và không phải 401 => cố đọc JSON nếu có, hoặc text
            let message = "Có lỗi xảy ra.";
            try {
                const data = await res.json();
                message = data.message || message;
            } catch (_) {
                const text = await res.text();
                console.error("Server trả về:", text); // HTML có thể in ra đây
            }
            throw new Error(message);
        }
    })
    .catch(error => {
        console.error("Lỗi đăng ký miễn phí:", error);
        alert(error.message || "Không thể đăng ký khóa học.");
    });
}


// Xử lý thanh toán khóa học trả phí
async function processPurchase(event) {
    event.preventDefault();

    const courseId = getCourseId();
    const paymentMethod = document.getElementById('paymentMethod')?.value || 'vnpay';

    if (!courseId) {
        alert('Không tìm thấy khóa học.');
        return;
    }

    const course = allCourses.find(c => c.id === parseInt(courseId));
    if (!course) {
        alert('Không tìm thấy thông tin khóa học.');
        return;
    }

    const statusDiv = document.getElementById('paymentStatus');
    if (statusDiv) {
        statusDiv.innerHTML = `<p><i class="fas fa-spinner fa-spin"></i> Đang xử lý thanh toán...</p>`;
    }

    try {
        const res = await fetch('/api/payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                course_id: parseInt(courseId),
                amount: course.price,
                order_desc: `Thanh toan khoa hoc ${removeVietnameseTones(course.title)}`,
                language: 'vn'
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
window.location.href =data['vnpay_url']
        // Gửi xác nhận thanh toán (nếu có)
        if (statusDiv) {
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
        }
    } catch (error) {
        console.error('Lỗi thanh toán:', error);
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div style="color: red; text-align: center;">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Đã xảy ra lỗi khi thanh toán, vui lòng thử lại.</p>
                </div>
            `;
        }
    }
}

// Chuyển đến trang học
function goToCourse() {
    window.location.href = '/my-courses';
}
function removeVietnameseTones(str) {
  return str
    .normalize("NFD") // tách dấu
    .replace(/[\u0300-\u036f]/g, "") // xóa dấu
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .replace(/[^a-zA-Z0-9 ]/g, ""); // xóa ký tự đặc biệt, chỉ giữ chữ, số và khoảng trắng
}

// Khởi tạo khi load trang
document.addEventListener('DOMContentLoaded', async () => {
    await fetchCourses();

    const courseIdParam = getParameterByName('course_id');
    const freeInput = document.getElementById('freeCourseId');
    const paidInput = document.getElementById('paidCourseId');
    if (courseIdParam) {
        if (freeInput) freeInput.value = courseIdParam;
        if (paidInput) paidInput.value = courseIdParam;
    }
});
