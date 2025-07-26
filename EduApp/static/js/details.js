function addToCart(courseId) {
    // Add to cart functionality
    fetch('/api/cart/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            course_id: courseId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showNotification('Đã thêm vào giỏ hàng!', 'success');
            updateCartCount();
        } else {
            showNotification('Có lỗi xảy ra!', 'error');
        }
    })
    .catch(error => {
        showNotification('Có lỗi xảy ra!', 'error');
    });
}

function addToWishlist(courseId) {
    // Add to wishlist functionality
    fetch('/api/wishlist/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            course_id: courseId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Đã thêm vào danh sách yêu thích!', 'success');
            // Update heart icon
            event.target.innerHTML = '<i class="fas fa-heart"></i>';
        }
    });
}

function toggleReviewForm() {
    // Toggle review form visibility
    const form = document.getElementById('reviewForm');
    if (form) {
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }
}

function toggleCommentForm() {
    const form = document.getElementById('commentForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

function toggleReplyForm(commentId) {
    // Toggle reply form for specific comment
    console.log('Toggle reply for comment:', commentId);
}

function showNotification(message, type) {
    // Create and show notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function updateCartCount() {
    // Update cart count in header
    fetch('/api/cart/count')
    .then(response => response.json())
    .then(data => {
        const cartCount = document.querySelector('.cart-count');
        if (cartCount) {
            cartCount.textContent = data.count;
        }
    });
}