// =====================
// API Helper
// =====================
async function apiRequest(url, method = "GET", data = null) {
  const options = {
    method: method,
    headers: { "Content-Type": "application/json" }
  };
  if (data) options.body = JSON.stringify(data);

  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("API Error:", err);
    alert("Có lỗi xảy ra khi gọi API!");
  }
}

// =====================
// Course
// =====================
function updateCourseField(courseId, field, value) {
  if (!value.trim()) {
    alert("Trường không được để trống!");
    return;
  }
  apiRequest(`/api/course/${courseId}`, "PUT", { [field]: value.trim() })
    .then(() => alert("Cập nhật khóa học thành công"));
}

// =====================
// Module
// =====================
function addModule(courseId) {
  const title = prompt("Nhập tên module:");
  if (!title || !title.trim()) {
    alert("Tên module không được để trống!");
    return;
  }
  apiRequest(`/api/course/${courseId}/module`, "POST", { title: title.trim() })
    .then(() => location.reload());
}

// Nút lưu chung module + lessons
async function saveModule(moduleId) {
  const moduleTitle = document.getElementById(`module-title-${moduleId}`).value.trim();
  if (!moduleTitle) {
    alert("Tên module không được để trống!");
    return;
  }

  // Update module
  await apiRequest(`/api/module/${moduleId}`, "PUT", { title: moduleTitle });

  // Update lessons trong module
  const lessonItems = document.querySelectorAll(`#module-title-${moduleId} ~ ul li`);
  for (let item of lessonItems) {
    const lessonId = item.querySelector("[id^=lesson-title-]").id.split("-").pop();
    const title = document.getElementById(`lesson-title-${lessonId}`).value.trim();
    const type = document.getElementById(`lesson-type-${lessonId}`).value.trim();
    const content = document.getElementById(`lesson-content-${lessonId}`).value.trim();

    if (!title || !type || !content) {
      alert(`Lesson ${lessonId} có trường trống, vui lòng điền đầy đủ!`);
      return;
    }

    await apiRequest(`/api/lesson/${lessonId}`, "PUT", { title, type, content });
  }

  alert("Lưu module và lessons thành công!");
}

// =====================
// Lesson
// =====================
function addLesson(moduleId) {
  const title = prompt("Nhập tên lesson:");
  if (!title || !title.trim()) {
    alert("Tên lesson không được để trống!");
    return;
  }
  apiRequest(`/api/module/${moduleId}/lesson`, "POST", {
    title: title.trim(),
    type: "text",
    content: "Nội dung mới"
  }).then(() => location.reload());
}

// =====================
// Preview Renderer
// =====================
function renderPreview(lessonId) {
  const type = document.getElementById(`lesson-type-${lessonId}`).value;
  const content = document.getElementById(`lesson-content-${lessonId}`).value.trim();
  const previewDiv = document.getElementById(`lesson-preview-${lessonId}`);

  if (!content) {
    previewDiv.innerHTML = "";
    return;
  }

  if (type === "video") {
    let embedUrl = content;
    if (content.includes("youtube.com/watch?v=")) {
      const videoId = new URL(content).searchParams.get("v");
      embedUrl = `https://www.youtube.com/embed/${videoId}`;
    } else if (content.includes("youtu.be/")) {
      const videoId = content.split("youtu.be/")[1];
      embedUrl = `https://www.youtube.com/embed/${videoId}`;
    }
    previewDiv.innerHTML = `
      <iframe class="lesson-iframe" src="${embedUrl}" frameborder="0" allowfullscreen></iframe>
    `;
  } else if (type === "file") {
    previewDiv.innerHTML = `<iframe class="lesson-iframe" src="${content}"></iframe>`;
  } else {
    previewDiv.innerHTML = `<div class="p-2 border rounded">${content}</div>`;
  }
}

// =====================
// Auto-render preview khi load
// =====================
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[id^=lesson-content-]").forEach(input => {
    const lessonId = input.id.split("-").pop();
    renderPreview(lessonId);
  });
});
