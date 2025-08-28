document.addEventListener("DOMContentLoaded", () => {
  const commentsList = document.getElementById("comments-list");
  const pagination = document.getElementById("pagination");
  const courseId = commentsList.dataset.courseId;

  // Escape HTML tránh XSS
  const escapeHTML = (str) => {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  };

  // Load comments theo trang
  async function loadComments(page = 1) {
    try {
      const res = await fetch(`/api/instructor/course/${courseId}/comments?page=${page}`);
      const data = await res.json();

      if (data.status === "success") {
        renderComments(data.comments);
        renderPagination(data);
      } else {
        commentsList.innerHTML = `<p class="text-muted">Không thể tải bình luận.</p>`;
      }
    } catch (err) {
      console.error(err);
      commentsList.innerHTML = `<p class="text-muted">Lỗi tải bình luận.</p>`;
    }
  }

  // Render danh sách bình luận
  function renderComments(comments) {
    commentsList.innerHTML = "";

    if (comments.length === 0) {
      commentsList.innerHTML = `<p class="text-muted">Chưa có bình luận nào.</p>`;
      return;
    }

    comments.forEach((cmt) => addCommentToDOM(cmt, false));
  }

  // Render phân trang
  function renderPagination(p) {
    pagination.innerHTML = "";
    if (p.pages <= 1) return;

    if (p.has_prev) {
      pagination.innerHTML += `
        <li class="page-item"><a class="page-link" href="#" data-page="${p.prev_num}">&laquo;</a></li>`;
    }

    for (let i = 1; i <= p.pages; i++) {
      pagination.innerHTML += `
        <li class="page-item ${i === p.page ? "active" : ""}">
          <a class="page-link" href="#" data-page="${i}">${i}</a>
        </li>`;
    }

    if (p.has_next) {
      pagination.innerHTML += `
        <li class="page-item"><a class="page-link" href="#" data-page="${p.next_num}">&raquo;</a></li>`;
    }
  }

  // Thêm 1 comment/reply vào DOM
  function addCommentToDOM(cmt, isReply, parentEl = null) {
    const displayName = cmt.is_current_user ? "Bạn" : cmt.username;
    const contentSafe = escapeHTML(cmt.content);

    const html = `
      <div class="${isReply ? "reply border-start ps-2 mb-2" : "comment-card card mb-3"}" data-id="${cmt.id}">
        <div class="${isReply ? "" : "card-body"}">
          <p><strong>${displayName}</strong> <small class="text-muted">${cmt.created_at}</small></p>
          <p>${contentSafe}</p>
          ${
            !isReply
              ? `
                <button class="btn btn-outline-primary reply-btn">↩ Trả lời</button>
                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${cmt.id}">🗑 Xóa</button>
                <form class="reply-form mt-2 d-none" method="POST" action="/instructor/course/${courseId}/comment">
                  <input type="hidden" name="parent_id" value="${cmt.id}">
                  <textarea name="content" class="form-control mb-2" rows="2" placeholder="Nhập trả lời..."></textarea>
                  <button type="submit" class="btn btn-sm btn-outline-primary">Gửi trả lời</button>
                </form>
                <div class="replies mt-3 ms-4"></div>
              `
              : `<button class="btn btn-sm btn-outline-danger delete-btn" data-id="${cmt.id}">🗑 Xóa</button>`
          }
        </div>
      </div>
    `;

    if (isReply && parentEl) {
      parentEl.querySelector(".replies").insertAdjacentHTML("beforeend", html);
    } else {
      commentsList.insertAdjacentHTML("beforeend", html);

      // Render replies nếu có
      if (cmt.replies && cmt.replies.length > 0) {
        const parent = commentsList.querySelector(`[data-id="${cmt.id}"]`);
        cmt.replies.forEach((reply) => addCommentToDOM(reply, true, parent));
      }
    }
  }

  // Click events: toggle reply + phân trang
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("reply-btn")) {
      const form = e.target.closest(".card-body").querySelector(".reply-form");
      form.classList.toggle("d-none");
    }

    if (e.target.closest(".page-link")) {
      e.preventDefault();
      const page = e.target.dataset.page;
      if (page) loadComments(page);
    }
  });

  // Gửi bình luận mới
  document.addEventListener("submit", async (e) => {
    if (e.target.id === "comment-form") {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);

      try {
        const res = await fetch(form.action, { method: "POST", body: formData });
        const data = await res.json();

        if (data.status === "success") {
          form.reset();
          loadComments(1); // Reload lại trang 1 cho chắc
        } else {
          alert(data.message || "Không thể thêm bình luận");
        }
      } catch (err) {
        console.error(err);
        alert("Lỗi hệ thống!");
      }
    }
  });

  // Gửi trả lời
  document.addEventListener("submit", async (e) => {
    if (e.target.classList.contains("reply-form")) {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);

      try {
        const res = await fetch(form.action, { method: "POST", body: formData });
        const data = await res.json();

        if (data.status === "success") {
          const parent = form.closest(".comment-card");
          addCommentToDOM(data.comment, true, parent);
          form.reset();
          form.classList.add("d-none");
        } else {
          alert(data.message || "Không thể thêm trả lời");
        }
      } catch (err) {
        console.error(err);
        alert("Lỗi hệ thống!");
      }
    }
  });

  // Xóa bình luận
  document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("delete-btn")) {
      e.preventDefault();
      const commentId = e.target.dataset.id;
      if (!confirm("Bạn có chắc muốn xóa bình luận này?")) return;

      try {
        const res = await fetch(`/instructor/comment/${commentId}/delete`, { method: "POST" });
        const data = await res.json();

        if (data.status === "success") {
          const el = document.querySelector(`[data-id="${commentId}"]`);
          if (el) el.remove();

          if (document.querySelectorAll("#comments-list .comment-card").length === 0) {
            commentsList.innerHTML = `<p class="text-muted">Chưa có bình luận nào.</p>`;
          }
        } else {
          alert(data.message || "Không thể xóa bình luận");
        }
      } catch (err) {
        console.error(err);
        alert("Lỗi hệ thống!");
      }
    }
  });

  // Load trang đầu tiên khi mở
  loadComments(1);
});