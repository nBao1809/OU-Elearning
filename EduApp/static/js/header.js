// Header JavaScript Functions

// Toggle mobile menu
function toggleMobileMenu() {
    const navMenu = document.getElementById('navMenu');
    const toggleBtn = document.querySelector('.mobile-menu-toggle');

    navMenu.classList.toggle('show');

    // Change icon based on menu state
    const icon = toggleBtn.querySelector('i');
    if (navMenu.classList.contains('show')) {
        icon.className = 'fas fa-times';
    } else {
        icon.className = 'fas fa-bars';
    }
}

// Toggle user dropdown
function toggleDropdown() {
    const dropdownMenu = document.getElementById('dropdownMenu');
    dropdownMenu.classList.toggle('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.querySelector('.user-dropdown');
    const dropdownMenu = document.getElementById('dropdownMenu');

    if (dropdown && !dropdown.contains(event.target)) {
        dropdownMenu.classList.remove('show');
    }
});

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
    const navMenu = document.getElementById('navMenu');
    const toggleBtn = document.querySelector('.mobile-menu-toggle');
    const headerContent = document.querySelector('.header-content');

    if (navMenu && navMenu.classList.contains('show') &&
        !headerContent.contains(event.target)) {
        navMenu.classList.remove('show');
        const icon = toggleBtn.querySelector('i');
        icon.className = 'fas fa-bars';
    }
});

// Close mobile menu when clicking on a link
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-item a');
    const navMenu = document.getElementById('navMenu');
    const toggleBtn = document.querySelector('.mobile-menu-toggle');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('show');
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                icon.className = 'fas fa-bars';
            }
        });
    });
});

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('.search-form');
    const searchBox = document.querySelector('.search-box');
    const searchBtn = document.querySelector('.search-btn');

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchTerm = searchBox.value.trim();
            if (!searchTerm) {
                e.preventDefault();
                searchBox.focus();
                return false;
            }
        });
    }

    // Search suggestion (optional - can be enhanced later)
    if (searchBox) {
        searchBox.addEventListener('input', function() {
            const searchTerm = this.value.trim();
            // Here you can add search suggestions functionality
            // For example, show dropdown with course suggestions
        });

        // Clear search when ESC is pressed
        searchBox.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.value = '';
                this.blur();
            }
        });
    }
});

// Smooth scroll for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');

    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;

            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Cart functionality
function updateCartCount(count) {
    const cartBadge = document.querySelector('.notification-badge');
    if (cartBadge) {
        cartBadge.textContent = count;
        cartBadge.style.display = count > 0 ? 'flex' : 'none';
    }
}

// Add to cart animation
function addToCartAnimation(button) {
    const cart = document.querySelector('.cart-icon');
    const rect = button.getBoundingClientRect();
    const cartRect = cart.getBoundingClientRect();

    // Create animated element
    const flyingItem = document.createElement('div');
    flyingItem.innerHTML = '<i class="fas fa-plus"></i>';
    flyingItem.style.cssText = `
        position: fixed;
        left: ${rect.left + rect.width/2}px;
        top: ${rect.top + rect.height/2}px;
        z-index: 9999;
        color: #667eea;
        font-size: 20px;
        pointer-events: none;
        transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1);
    `;

    document.body.appendChild(flyingItem);

    // Animate to cart
    setTimeout(() => {
        flyingItem.style.left = cartRect.left + cartRect.width/2 + 'px';
        flyingItem.style.top = cartRect.top + cartRect.height/2 + 'px';
        flyingItem.style.transform = 'scale(0)';
        flyingItem.style.opacity = '0';
    }, 100);

    // Remove element after animation
    setTimeout(() => {
        document.body.removeChild(flyingItem);
    }, 1000);
}

// Header scroll effect
window.addEventListener('scroll', function() {
    const header = document.querySelector('.header');
    if (window.scrollY > 100) {
        header.style.transform = 'translateY(-5px)';
        header.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
    } else {
        header.style.transform = 'translateY(0)';
        header.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
    }
});

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    // Add notification styles if not already added
    if (!document.querySelector('#notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 100px;
                right: 20px;
                background: white;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 9999;
                animation: slideIn 0.3s ease;
                max-width: 350px;
            }
            .notification-success { border-left: 4px solid #28a745; }
            .notification-error { border-left: 4px solid #dc3545; }
            .notification-info { border-left: 4px solid #17a2b8; }
            .notification button {
                background: none;
                border: none;
                color: #666;
                cursor: pointer;
                margin-left: auto;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styles);
    }

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Loading state for buttons
function setButtonLoading(button, loading = true) {
    if (loading) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';
    } else {
        button.disabled = false;
        // Restore original content - you might want to store this
        button.innerHTML = button.getAttribute('data-original-text') || 'Hoàn thành';
    }
}

// Initialize tooltips (if needed)
document.addEventListener('DOMContentLoaded', function() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');

    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            tooltip.style.cssText = `
                position: absolute;
                background: #333;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 12px;
                z-index: 9999;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;

            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + rect.width/2 - tooltip.offsetWidth/2 + 'px';
            tooltip.style.top = rect.bottom + 10 + 'px';
            tooltip.style.opacity = '1';

            this._tooltip = tooltip;
        });

        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
});