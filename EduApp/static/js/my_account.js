document.addEventListener("DOMContentLoaded", () => {
    const avatarInput = document.getElementById("avatar");
    const avatarPreview = document.getElementById("avatar-preview");
    const form = document.getElementById("account-form");
    const msgBox = document.getElementById("msg-box");

    // Preview avatar
    if (avatarInput && avatarPreview) {
        avatarInput.addEventListener("change", () => {
            const file = avatarInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    avatarPreview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // AJAX submit form
    if (form && msgBox) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(this.action, {
                method: "POST",
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    msgBox.innerHTML = `<p class="${data.status}">${data.message}</p>`;
                })
                .catch(err => {
                    console.error(err);
                    msgBox.innerHTML = `<p class="error">❌ Lỗi server!</p>`;
                });
        });
    }
});
