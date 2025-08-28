// =================== TẠO COURSE JS ===================
let moduleIndex = 0;
const modulesContainer = document.getElementById('modulesContainer');
const moduleCountInput = document.getElementById('module_count');
const btnAddModule = document.getElementById('btnAddModule');
const form = document.getElementById('createCourseForm');

// =================== LOAD DANH MỤC ===================
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    if (!res.ok) throw new Error("Không lấy được danh mục");
    const data = await res.json();

    const categorySelect = document.getElementById('category_id');
    data.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      categorySelect.appendChild(opt);
    });
  } catch (err) {
    console.error(err);
    alert("Lỗi tải danh mục!");
  }
}
loadCategories();

// =================== MODULE ===================
btnAddModule.addEventListener('click', () => addModule());

function addModule(prefill = {}) {
  moduleIndex++;
  moduleCountInput.value = moduleIndex;

  const moduleId = moduleIndex;
  const card = document.createElement('div');
  card.className = 'module-card';
  card.id = `module_${moduleId}`;

  card.innerHTML = `
    <div class="module-head">
      <h3>Module ${moduleId}</h3>
      <div class="module-actions">
        <button type="button" class="btn btn-secondary" onclick="addLesson(${moduleId})">+ Thêm lesson</button>
        <button type="button" class="btn btn-danger" onclick="removeModule(${moduleId})">Xóa module</button>
      </div>
    </div>

    <div class="module-title-row">
      <label>Tiêu đề Module</label>
      <input type="text" name="module_${moduleId}_title" placeholder="VD: Giới thiệu" required>
    </div>

    <input type="hidden" name="module_${moduleId}_lesson_count" id="module_${moduleId}_lesson_count" value="0">
    <div class="lessons" id="module_${moduleId}_lessons"></div>
    <div class="error-text" id="module_${moduleId}_error" style="display:none;color:red;font-size:14px;"></div>
  `;

  modulesContainer.appendChild(card);
  addLesson(moduleId); // lesson mặc định
}

function removeModule(moduleId) {
  const el = document.getElementById(`module_${moduleId}`);
  if (el) el.remove();
  moduleCountInput.value = modulesContainer.querySelectorAll('.module-card').length;
}

// =================== LESSON ===================
function addLesson(moduleId) {
  const cntInput = document.getElementById(`module_${moduleId}_lesson_count`);
  const lessonsWrap = document.getElementById(`module_${moduleId}_lessons`);
  const nextIndex = parseInt(cntInput.value || '0', 10) + 1;
  cntInput.value = nextIndex;

  const row = document.createElement('div');
  row.className = 'lesson-row';
  row.id = `module_${moduleId}_lesson_${nextIndex}`;

  row.innerHTML = `
    <label>Lesson ${nextIndex}</label>
    <div class="lesson-actions">
      <input type="text" name="module_${moduleId}_lesson_${nextIndex}_title" placeholder="Tiêu đề bài học" required>
      <select name="module_${moduleId}_lesson_${nextIndex}_content_type">
        <option value="text">Text</option>
        <option value="video">Video (YouTube URL)</option>
        <option value="file">File (link)</option>
      </select>
      <input type="text" name="module_${moduleId}_lesson_${nextIndex}_content" placeholder="Nhập nội dung hoặc link...">
      <button type="button" class="btn btn-danger" onclick="removeLesson(${moduleId}, ${nextIndex})">Xóa</button>
    </div>
  `;

  lessonsWrap.appendChild(row);
}

function removeLesson(moduleId, lessonIndex) {
  const row = document.getElementById(`module_${moduleId}_lesson_${lessonIndex}`);
  if (!row) return;
  row.remove();
  const lessonsWrap = document.getElementById(`module_${moduleId}_lessons`);
  document.getElementById(`module_${moduleId}_lesson_count`).value = lessonsWrap.querySelectorAll('.lesson-row').length;
}

// =================== HELPER: CHUYỂN LINK YOUTUBE THÀNH EMBED ===================
function toYouTubeEmbed(url) {
  if (!url) return null;
  url = url.trim();

  // https://www.youtube.com/watch?v=VIDEOID
  let match = url.match(/v=([A-Za-z0-9_-]{11})/);
  if (match) return `https://www.youtube.com/embed/${match[1]}`;

  // https://youtu.be/VIDEOID
  match = url.match(/youtu\.be\/([A-Za-z0-9_-]{11})/);
  if (match) return `https://www.youtube.com/embed/${match[1]}`;

  // https://www.youtube.com/embed/VIDEOID
  match = url.match(/embed\/([A-Za-z0-9_-]{11})/);
  if (match) return `https://www.youtube.com/embed/${match[1]}`;

  // https://www.youtube.com/shorts/VIDEOID
  match = url.match(/shorts\/([A-Za-z0-9_-]{11})/);
  if (match) return `https://www.youtube.com/embed/${match[1]}`;

  return url;
}

// =================== VALIDATE & SUBMIT ===================
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const categorySelect = document.getElementById('category_id');
  const currentModules = modulesContainer.querySelectorAll('.module-card');
  moduleCountInput.value = currentModules.length;

  if (currentModules.length < 2) {
    alert('Khóa học phải có ít nhất 2 module.');
    return;
  }

  const priceVal = parseFloat(document.getElementById('price').value);
  const maxEnrollVal = parseInt(document.getElementById('max_enrollment').value);

  if (isNaN(priceVal) || priceVal < 0) {
    alert("⚠️ Bạn phải nhập giá >= 0");
    return;
  }
  if (isNaN(maxEnrollVal) || maxEnrollVal < 20) {
    alert("⚠️ Số học viên tối đa phải ≥ 20");
    return;
  }

  // =================== BUILD MODULES ===================
  let modules = [];
  currentModules.forEach((m) => {
    const moduleId = m.id.split('_')[1];
    const moduleTitle = m.querySelector(`input[name="module_${moduleId}_title"]`).value;
    const lessons = [];
    m.querySelectorAll('.lesson-row').forEach((row) => {
      const ltitle = row.querySelector(`input[name^="module_${moduleId}_lesson_"][name$="_title"]`).value;
      const type = row.querySelector(`select[name^="module_${moduleId}_lesson_"][name$="_content_type"]`).value;
      const content = row.querySelector(`input[name^="module_${moduleId}_lesson_"][name$="_content"]`).value;

      lessons.push({
        title: ltitle,
        content_type: type,
        video_url: type === 'video' ? toYouTubeEmbed(content) : null,
        text_content: type === 'text' ? content : null,
        file_url: type === 'file' ? content : null
      });
    });

    modules.push({ title: moduleTitle, lessons });
  });

  // =================== BUILD FORM DATA ===================
  const formData = new FormData();
  formData.append('title', document.getElementById('title').value);
  formData.append('description', document.getElementById('description').value);
  formData.append('price', priceVal);
  formData.append('level', document.getElementById('level').value);
  formData.append('category_id', parseInt(categorySelect.value));
  formData.append('max_enrollment', maxEnrollVal);
  formData.append('is_published', document.getElementById('is_published').checked);
  formData.append('is_available', document.getElementById('is_available').checked);
  formData.append('modules', JSON.stringify(modules));

  // thumbnail (nếu có input file)
  const thumbnailInput = document.getElementById('thumbnail');
  if (thumbnailInput && thumbnailInput.files.length > 0) {
    formData.append('thumbnail', thumbnailInput.files[0]);
  }

  // =================== GỬI API ===================
  try {
    const res = await fetch('/api/instructor/courses', {
      method: 'POST',
      body: formData
    });

    const result = await res.json();
    if (res.ok) {
      alert("✅ Tạo khóa học thành công!");
      window.location.href = "/instructor";
    } else {
      alert("❌ Lỗi: " + result.error);
    }
  } catch (err) {
    console.error(err);
    alert("Lỗi khi gửi dữ liệu!");
  }
});
