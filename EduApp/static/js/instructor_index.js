let allCourses = [];
let filteredCourses = [];

// Hàm bỏ dấu tiếng Việt
function removeVietnameseTones(str) {
    return str
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd').replace(/Đ/g, 'D');
}

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
    return levels[level.toLowerCase()] || level;
}

// Tạo card khóa học HTML (của giảng viên)
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
                    <div class="course-category">
                        <i class="fas fa-tag"></i> ${course.category_name || 'Chưa phân loại'}
                    </div>
                    <div class="course-price">
                        ${formatPrice(course.price)}
                    </div>
                </div>
                <div class="course-actions">
                    <a href="/instructor/courses/${course.id}/progress/view" class="btn btn-outline">
                        <i class="fas fa-eye"></i> Xem tiến độ
                    </a>
                    <a href="/instructor/course/${course.id}/edit" class="btn btn-primary">
                        <i class="fas fa-edit"></i> Chỉnh sửa
                    </a>
                    <a href="/instructor/course/${course.id}/discussion" class="btn btn-outline">
                    <i class="fas fa-comments"></i> Thảo luận
                    </a>
                </div>
            </div>
        </div>
    `;
}

// Gọi API lấy danh sách khóa học của giảng viên
function fetchCourses() {
    const loading = document.getElementById('loading');
    loading.style.display = 'block';

    fetch('/api/instructor/courses')
        .then(response => response.json())
        .then(data => {
            allCourses = data;
            filteredCourses = [...allCourses];
            populateCategoryFilter();
            renderCourses(filteredCourses);
        })
        .catch(error => {
            console.error('Lỗi khi tải khóa học:', error);
        })
        .finally(() => {
            loading.style.display = 'none';
        });
}

// Tạo danh sách category cho filter
function populateCategoryFilter() {
    const categoryFilter = document.getElementById('categoryFilter');
    if (!categoryFilter) return;

    const categories = [...new Set(allCourses.map(course => course.category_name).filter(Boolean))];
    categories.sort();

    while (categoryFilter.children.length > 1) {
        categoryFilter.removeChild(categoryFilter.lastChild);
    }

    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });
}

// Áp dụng tất cả filter và tìm kiếm
function applyAllFilters() {
    const levelFilter = document.getElementById('levelFilter').value.toLowerCase();
    const priceFilter = document.getElementById('priceFilter').value;
    const categoryFilter = document.getElementById('categoryFilter')?.value || '';
    const sortBy = document.getElementById('sortBy').value;
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const queryNoAccent = removeVietnameseTones(query);

    filteredCourses = allCourses.filter(course => {
        const courseTitleNoAccent = removeVietnameseTones(course.title.toLowerCase());
        const matchesQuery = courseTitleNoAccent.includes(queryNoAccent);

        const matchesLevel = !levelFilter || course.level.toLowerCase() === levelFilter;
        const matchesPrice =
            !priceFilter ||
            (priceFilter === 'free' && course.price === 0) ||
            (priceFilter === 'paid' && course.price > 0);

        const matchesCategory = !categoryFilter || course.category_name === categoryFilter;

        return matchesQuery && matchesLevel && matchesPrice && matchesCategory;
    });

    // Sắp xếp
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
            case 'category':
                const categoryA = a.category_name || 'zzz';
                const categoryB = b.category_name || 'zzz';
                return categoryA.localeCompare(categoryB, 'vi');
            default:
                return 0;
        }
    });

    renderCourses(filteredCourses);
}

// Tìm kiếm khi gõ
function handleSearch() {
    applyAllFilters();
}

// Lọc khi thay đổi filter
function filterCourses() {
    applyAllFilters();
}

// Sắp xếp khi thay đổi
function sortCourses() {
    applyAllFilters();
}

// Hiển thị danh sách khóa học
function renderCourses(courses) {
    const grid = document.getElementById('coursesGrid');
    const noCourses = document.getElementById('noCourses');

    if (courses.length === 0) {
        grid.innerHTML = '';
        noCourses.style.display = 'block';
        return;
    }

    noCourses.style.display = 'none';
    grid.innerHTML = courses.map(course => createCourseCard(course)).join('');
}

// Xóa khóa học
function deleteCourse(courseId) {
    if (!confirm("Bạn có chắc muốn xóa khóa học này?")) return;

    fetch(`/api/instructor/courses/${courseId}`, {
        method: 'DELETE',
        credentials: 'include'
    })
        .then(res => {
            if (res.ok) {
                allCourses = allCourses.filter(c => c.id !== courseId);
                applyAllFilters();
                alert("Xóa khóa học thành công!");
            } else {
                alert("Không thể xóa khóa học!");
            }
        })
        .catch(error => {
            console.error("Lỗi khi xóa khóa học:", error);
            alert("Có lỗi xảy ra khi xóa khóa học.");
        });
}

// Gọi khi trang được tải
document.addEventListener('DOMContentLoaded', function () {
    fetchCourses();
});
