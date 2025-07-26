let allCourses = [];
let filteredCourses = [];

// Định dạng giá tiền
function formatPrice(price) {
    if (price === 0) {
        return '<span class="price-free">Miễn phí</span>';
    }
    return `${price.toLocaleString('vi-VN')}đ`;
}

// Lấy class cấp độ
function getLevelClass(level) {
    return `level-${level}`;
}

// Hiển thị tên cấp độ tiếng Việt
function getLevelText(level) {
    const levels = {
        'beginner': 'Cơ bản',
        'intermediate': 'Trung cấp',
        'advanced': 'Nâng cao'
    };
    return levels[level] || level;
}

// Tạo card khóa học HTML
function createCourseCard(course) {
    return `
        <div class="course-card" data-level="${course.level}" data-price="${course.price}" data-created="${course.created_at}">
            <div class="course-thumbnail">
                <img src="${course.thumbnail}" alt="${course.title}" loading="lazy">
            </div>
            <div class="course-info">
                <h3 class="course-title">${course.title}</h3>
                <div class="course-meta">
                    <span class="level-badge ${getLevelClass(course.level)}">
                        ${getLevelText(course.level)}
                    </span>
                    <div class="course-price">
                        ${formatPrice(course.price)}
                    </div>
                </div>
                <div class="course-actions">
                    <a href="/course/${course.id}" class="btn btn-outline">
                        <i class="fas fa-eye"></i> Xem chi tiết
                    </a>
                    <button class="btn btn-primary" onclick="buyNow(${course.id})">
                        <i class="fas fa-shopping-cart"></i> Mua ngay
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Mua ngay (chuyển tới trang cart)
function buyNow(courseId) {
    fetch('/api/auth/check', { credentials: 'include' })
        .then(res => {
            if (res.status === 200) {
                // Đã đăng nhập → chuyển tới cart
                window.location.href = `/cart?course_id=${courseId}`;
            } else {
                // Chưa đăng nhập → thông báo và chuyển trang login
                alert("Bạn cần đăng nhập để mua khóa học!");
                window.location.href = "/login";
            }
        })
        .catch(error => {
            console.error("Lỗi khi kiểm tra đăng nhập:", error);
            alert("Không thể xác minh trạng thái đăng nhập. Vui lòng thử lại.");
        });
}

// Hiển thị danh sách khóa học
function renderCourses(courses) {
    const grid = document.getElementById('coursesGrid');
    const loading = document.getElementById('loading');
    const noCourses = document.getElementById('noCourses');

    if (courses.length === 0) {
        grid.innerHTML = '';
        noCourses.style.display = 'block';
        return;
    }

    noCourses.style.display = 'none';
    grid.innerHTML = courses.map(course => createCourseCard(course)).join('');
}

// Gọi API lấy danh sách khóa học
function fetchCourses() {
    const loading = document.getElementById('loading');
    loading.style.display = 'block';

    fetch('/api/courses')
        .then(response => response.json())
        .then(data => {
            allCourses = data;
            filteredCourses = [...allCourses];
            renderCourses(filteredCourses);
        })
        .catch(error => {
            console.error('Lỗi khi tải khóa học:', error);
        })
        .finally(() => {
            loading.style.display = 'none';
        });
}

// Lọc khóa học theo cấp độ và giá
function filterCourses() {
    const levelFilter = document.getElementById('levelFilter').value;
    const priceFilter = document.getElementById('priceFilter').value;

    filteredCourses = allCourses.filter(course => {
        const levelMatch = !levelFilter || course.level === levelFilter;
        const priceMatch = !priceFilter ||
            (priceFilter === 'free' && course.price === 0) ||
            (priceFilter === 'paid' && course.price > 0);
        return levelMatch && priceMatch;
    });

    sortCourses(); // Sắp xếp sau khi lọc
}

// Sắp xếp khóa học
function sortCourses() {
    const sortBy = document.getElementById('sortBy').value;

    filteredCourses.sort((a, b) => {
        switch (sortBy) {
            case 'newest':
                return new Date(b.created_at) - new Date(a.created_at);
            case 'oldest':
                return new Date(a.created_at) - new Date(b.created_at);
            case 'price_low':
                return a.price - b.price;
            case 'price_high':
                return b.price - a.price;
            case 'title':
                return a.title.localeCompare(b.title, 'vi');
            default:
                return 0;
        }
    });

    renderCourses(filteredCourses);
}

// Tìm kiếm khóa học
function searchCourses(query) {
    if (!query.trim()) {
        filteredCourses = [...allCourses];
    } else {
        filteredCourses = allCourses.filter(course =>
            course.title.toLowerCase().includes(query.toLowerCase())
        );
    }

    filterCourses(); // Áp dụng bộ lọc sau tìm kiếm
}

// Gọi khi người dùng gõ vào thanh tìm kiếm
function handleSearch() {
    const query = document.getElementById('searchInput').value.trim();
    searchCourses(query);
}

// Gọi khi trang được tải
document.addEventListener('DOMContentLoaded', function () {
    fetchCourses();
});
