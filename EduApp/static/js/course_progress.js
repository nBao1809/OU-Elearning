// Get progress class for styling
function getProgressClass(percent) {
    if (percent >= 100) return 'completed';
    if (percent >= 75) return 'high';
    if (percent >= 25) return 'medium';
    return 'low';
}

// Get student initials for avatar
function getStudentInitials(name) {
    return name.split(' ')
        .map(word => word.charAt(0))
        .slice(0, 2)
        .join('')
        .toUpperCase();
}

// Create student row HTML
function createStudentRow(student) {
    const progress = student.progress_percent || 0;
    const progressClass = getProgressClass(progress);
    const initials = getStudentInitials(student.student_name);

    return `
        <tr>
            <td>
                <div class="student-info">
                    <div class="student-avatar">${initials}</div>
                    <div class="student-details">
                        <h4>${student.student_name}</h4>
                        <div class="student-email">${student.student_email}</div>
                    </div>
                </div>
            </td>
            <td>${student.student_email}</td>
            <td>
                <div class="join-date">
                    ${new Date(student.enrolled_at).toLocaleDateString('vi-VN')}
                </div>
            </td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill ${progressClass}" style="width: ${progress}%"></div>
                    </div>
                    <span class="progress-text ${progressClass}">${Math.round(progress)}%</span>
                </div>
            </td>

        </tr>
    `;
}

// Render students table
function renderStudentsTable() {
    const tableContainer = document.getElementById('tableContainer');
    const studentsBody = document.getElementById('studentsBody');
    const emptyState = document.getElementById('emptyState');
    const noResults = document.getElementById('noResults');
    const resultsCount = document.getElementById('resultsCount');

    // Hide all states first
    tableContainer.classList.add('hidden');
    emptyState.classList.add('hidden');
    noResults.classList.add('hidden');

    if (allStudents.length === 0) {
        emptyState.classList.remove('hidden');
        return;
    }

    if (filteredStudents.length === 0) {
        noResults.classList.remove('hidden');
        return;
    }

    // Show table and render students
    tableContainer.classList.remove('hidden');
    studentsBody.innerHTML = filteredStudents.map(student => createStudentRow(student)).join('');

    // Update results count
    const count = filteredStudents.length;
    resultsCount.textContent = `${count} ${count === 1 ? 'kết quả' : 'kết quả'}`;
}

// Handle search input
function handleSearch(event) {
    const query = event.target.value;
    const clearBtn = document.getElementById('clearSearch');

    // Show/hide clear button
    if (query.length > 0) {
        clearBtn.style.display = 'block';
    } else {
        clearBtn.style.display = 'none';
    }

    // Apply search filter
    applyFilters();
}

// Clear search input
function clearSearchInput() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');

    searchInput.value = '';
    clearBtn.style.display = 'none';

    applyFilters();
}

// Apply filters and search
function applyFilters() {
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const progressFilter = document.getElementById('progressFilter').value;
    const sortBy = document.getElementById('sortBy').value;

    // Start with all students
    filteredStudents = [...allStudents];

    // Apply search filter
    if (query) {
        const queryNoAccent = removeVietnameseTones(query);
        filteredStudents = filteredStudents.filter(student => {
            const name = removeVietnameseTones(student.student_name.toLowerCase());
            const email = student.student_email.toLowerCase();
            return name.includes(queryNoAccent) || email.includes(query);
        });
    }

    // Apply progress filter
    if (progressFilter) {
        filteredStudents = filteredStudents.filter(student => {
            const progress = student.progress_percent || 0;
            switch (progressFilter) {
                case 'completed':
                    return progress >= 100;
                case 'high':
                    return progress >= 75 && progress < 100;
                case 'medium':
                    return progress >= 25 && progress < 75;
                case 'low':
                    return progress < 25;
                default:
                    return true;
            }
        });
    }

    // Apply sorting
    filteredStudents.sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return a.student_name.localeCompare(b.student_name);
            case 'progress':
                return (b.progress_percent || 0) - (a.progress_percent || 0);
            case 'date':
                return new Date(b.enrolled_at) - new Date(a.enrolled_at);
            default:
                return 0;
        }
    });

    // Render filtered results
    renderStudentsTable();
}

// Show student detail modal
function showStudentDetail(studentId) {
    const student = allStudents.find(s => s.student_id === studentId);
    if (!student) return;

    const modal = document.getElementById('studentModal');
    const modalBody = document.getElementById('modalBody');

    const progress = student.progress_percent || 0;
    const progressClass = getProgressClass(progress);

    modalBody.innerHTML = `
        <div class="student-detail">
            <div class="detail-header">
                <div class="student-avatar large">${getStudentInitials(student.student_name)}</div>
                <div class="student-info-detail">
                    <h3>${student.student_name}</h3>
                    <p>${student.student_email}</p>
                    <p class="join-info">
                        <i class="fas fa-calendar-alt"></i>
                        Tham gia ngày: ${new Date(student.enrolled_at).toLocaleDateString('vi-VN')}
                    </p>
                </div>
            </div>

            <div class="progress-detail">
                <h4><i class="fas fa-chart-bar"></i> Tiến độ học tập</h4>
                <div class="progress-container large">
                    <div class="progress-bar large">
                        <div class="progress-fill ${progressClass}" style="width: ${progress}%"></div>
                    </div>
                    <span class="progress-text ${progressClass} large">${Math.round(progress)}%</span>
                </div>
                <p class="progress-description">
                    ${progress >= 100 ? '🎉 Đã hoàn thành khóa học!' :
                      progress >= 75 ? '👍 Sắp hoàn thành khóa học' :
                      progress >= 25 ? '📚 Đang học tập tích cực' :
                      '🚀 Mới bắt đầu học'
                    }
                </p>
            </div>
        </div>
    `;

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Close student detail modal


// Show error message
function showError(message) {
    const emptyState = document.getElementById('emptyState');
    emptyState.innerHTML = `
        <div class="empty-icon">
            <i class="fas fa-exclamation-triangle"></i>
        </div>
        <h3>Có lỗi xảy ra</h3>
        <p>${message}</p>
        <button class="action-btn" onclick="location.reload()" style="margin-top: 15px;">
            <i class="fas fa-refresh"></i>
            Thử lại
        </button>
    `;
    emptyState.classList.remove('hidden');
}// Enhanced Course Progress JavaScript
let allStudents = [];
let filteredStudents = [];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    init();
});

// Initialize application
function init() {
    setupEventListeners();
    loadStudents();
}

// Setup event listeners
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const clearSearch = document.getElementById('clearSearch');
    const progressFilter = document.getElementById('progressFilter');
    const sortBy = document.getElementById('sortBy');
    const closeModal = document.getElementById('closeModal');
    const modal = document.getElementById('studentModal');

    // Search functionality
    searchInput.addEventListener('input', handleSearch);
    clearSearch.addEventListener('click', clearSearchInput);

    // Filter and sort functionality
    progressFilter.addEventListener('change', applyFilters);
    sortBy.addEventListener('change', applyFilters);

    // Modal functionality
    if (closeModal) {
        closeModal.addEventListener('click', closeStudentModal);
    }
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeStudentModal();
            }
        });
    }

    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeStudentModal();
        }
    });
}

// Remove Vietnamese accents for search
function removeVietnameseTones(str) {
    return str
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/đ/g, "d")
        .replace(/Đ/g, "D");
}

// Load students data
async function loadStudents() {
    try {
        showLoading();

        const response = await fetch(`/instructor/courses/${courseId}/progress`);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        allStudents = data.students || [];
        filteredStudents = [...allStudents];

        updateHeaderStats();
        renderStudentsTable();
        hideLoading();

    } catch (error) {
        console.error('Error loading students:', error);
        showError('Không thể tải dữ liệu học viên. Vui lòng thử lại sau.');
        hideLoading();
    }
}

// Show loading state
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('tableContainer').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('noResults').classList.add('hidden');
}

// Hide loading state
function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// Update header statistics
function updateHeaderStats() {
    const totalStudents = allStudents.length;
    const completedStudents = allStudents.filter(s => (s.progress_percent || 0) >= 100).length;
    const avgProgress = totalStudents > 0
        ? Math.round(allStudents.reduce((sum, s) => sum + (s.progress_percent || 0), 0) / totalStudents)
        : 0;

    document.getElementById('totalStudents').textContent = totalStudents;
    document.getElementById('completedStudents').textContent = completedStudents;
    document.getElementById('avgProgress').textContent = avgProgress + '%';
}