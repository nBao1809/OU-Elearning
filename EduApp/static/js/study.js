document.addEventListener("DOMContentLoaded", () => {
    console.log("📘 Study page loaded!");

    // Focus effect cho textarea (bình luận)
    const textarea = document.querySelector("textarea[name='content']");
    if (textarea) {
        textarea.addEventListener("focus", () => textarea.classList.add("textarea-focus"));
        textarea.addEventListener("blur", () => textarea.classList.remove("textarea-focus"));
    }

    // Highlight comment mới gửi (nếu có hash #comment-ID)
    if (window.location.hash.startsWith("#comment-")) {
        const comment = document.querySelector(window.location.hash);
        if (comment) {
            comment.classList.add("highlight-comment");
            setTimeout(() => comment.classList.remove("highlight-comment"), 3000);
        }
    }

    // Smooth scroll khi click phân trang
    const paginationLinks = document.querySelectorAll(".pagination a");
    paginationLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const url = e.target.getAttribute("href");
            if (url) {
                window.location.href = url;
                window.scrollTo({ top: 0, behavior: "smooth" });
            }
        });
    });

    // AJAX gửi review (không reload)
    const reviewForm = document.getElementById("review-form");
    const reviewSuccess = document.getElementById("review-success");
    if (reviewForm) {
        reviewForm.addEventListener("submit", function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());

            fetch(this.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken()
                },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(result => {
                if (result.status === "success") {
                    reviewSuccess.classList.remove("d-none");
                    setTimeout(() => reviewSuccess.classList.add("d-none"), 3000);
                    reviewForm.reset();
                } else {
                    alert("❌ Gửi đánh giá thất bại!");
                }
            })
            .catch(err => {
                console.error(err);
                alert("Lỗi kết nối server!");
            });
        });
    }
});

// Toggle hiển thị nội dung bài học
function toggleLesson(lessonId) {
    const content = document.getElementById("lesson-" + lessonId);
    if (content) content.classList.toggle("d-none");
}

// Ajax hoàn thành bài học
function completeLesson(lessonId) {
    fetch(`/complete_lesson/${lessonId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {   // đúng key JSON từ Flask
            const statusDiv = document.getElementById("lesson-status-" + lessonId);
            const completeSection = document.getElementById("complete-section-" + lessonId);
            if (statusDiv) statusDiv.innerHTML = '<small class="text-success">✅ Hoàn thành</small>';
            if (completeSection) completeSection.innerHTML = '<span class="badge bg-success">✅ Bạn đã hoàn thành bài học này</span>';
        } else {
            alert("❌ Có lỗi xảy ra!");
        }
    })
    .catch(err => {
        console.error("Error:", err);
        alert("Lỗi kết nối server!");
    });
}


// Lấy CSRF token nếu dùng Flask-WTF
function getCSRFToken() {
    const cookie = document.cookie.split(";").find(c => c.trim().startsWith("csrf_token="));
    return cookie ? cookie.split("=")[1] : "";
}
