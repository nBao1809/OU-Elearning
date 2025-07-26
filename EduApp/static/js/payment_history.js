function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Đã sao chép mã giao dịch!');
    });
}

function viewDetails(paymentId) {
    console.log('View details for payment:', paymentId);
    // Có thể thêm modal hoặc redirect tại đây
}

function downloadReceipt(paymentId) {
    console.log('Download receipt for payment:', paymentId);
    // Có thể mở file PDF hoặc gửi request backend
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const paymentRows = document.querySelectorAll('.payment-row');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const status = this.getAttribute('data-status');
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            paymentRows.forEach(row => {
                row.style.display = (status === 'all' || row.getAttribute('data-status') === status) ? '' : 'none';
            });
        });
    });
});
