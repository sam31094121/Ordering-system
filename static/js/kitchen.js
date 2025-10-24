const socket = io();
let orders = [];
let currentFilter = 'all';

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('new_order', (order) => {
    console.log('New order received:', order);
    playNotificationSound();
    orders.unshift(order);
    displayOrders();
    showAlert(`新訂單：${order.order_number}`, 'warning');
});

socket.on('order_updated', (order) => {
    console.log('Order updated:', order);
    const index = orders.findIndex(o => o.id === order.id);
    if (index !== -1) {
        orders[index] = order;
        displayOrders();
    }
});

async function loadOrders() {
    try {
        const endpoint = currentFilter === 'all' ? '/api/orders' : '/api/orders/pending';
        const response = await fetch(endpoint);
        orders = await response.json();
        displayOrders();
    } catch (error) {
        console.error('Error loading orders:', error);
        showAlert('載入訂單時發生錯誤', 'danger');
    }
}

function displayOrders() {
    const container = document.getElementById('orders-container');
    const noOrders = document.getElementById('no-orders');
    let filteredOrders = orders;
    if (currentFilter !== 'all') {
        filteredOrders = orders.filter(order => order.status === currentFilter);
    }
    const pendingCount = orders.filter(o => o.status === 'pending').length;
    document.getElementById('pending-count').textContent = `${pendingCount} 待處理`;
    if (filteredOrders.length === 0) {
        container.innerHTML = '';
        noOrders.classList.remove('d-none');
        return;
    }
    noOrders.classList.add('d-none');
    let html = '';
    filteredOrders.forEach(order => {
        const statusClass = `status-${order.status}`;
        const orderTime = new Date(order.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
        html += `
            <div class="col-lg-4 col-md-6">
                <div class="order-card ${statusClass}">
                    <div class="order-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="order-number">${order.order_number}</div>
                            ${getStatusBadge(order.status)}
                        </div>
                        <div class="order-time">⏰ ${orderTime}</div>
                    </div>
                    <div class="order-items">
                        <h6>項目：</h6>
                        ${order.items.map(item => `
                            <div class="order-item">
                                <div class="d-flex justify-content-between">
                                    <span>${item.quantity}x ${item.name}</span>
                                    <span class="text-success">$${(item.price * item.quantity).toFixed(2)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    ${order.notes ? `<div class="alert alert-info mt-2 mb-2"><small><strong>備註：</strong> ${order.notes}</small></div>` : ''}
                    <div class="mt-3 mb-2">
                        <strong>總計：<span class="order-total">$${order.total_amount.toFixed(2)}</span></strong>
                    </div>
                    <div class="status-buttons mt-3">
                        ${getStatusButtons(order)}
                    </div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning status-badge">⏳ 待處理</span>',
        'received': '<span class="badge bg-info status-badge">👀 已接單</span>',
        'cooking': '<span class="badge bg-primary status-badge">🍳 烹調中</span>',
        'ready': '<span class="badge bg-success status-badge">✅ 已完成</span>'
    };
    return badges[status] || badges['pending'];
}

function getStatusButtons(order) {
    switch (order.status) {
        case 'pending':
            return `<button class="btn btn-info btn-sm" onclick="updateStatus(${order.id}, 'received')">👀 接單</button>`;
        case 'received':
            return `<button class="btn btn-primary btn-sm" onclick="updateStatus(${order.id}, 'cooking')">🍳 開始烹調</button>`;
        case 'cooking':
            return `<button class="btn btn-success btn-sm" onclick="updateStatus(${order.id}, 'ready')">✅ 標記完成</button>`;
        default:
            return '';
    }
}

const statusTranslations = {
    'pending': '待處理',
    'received': '已接單',
    'cooking': '烹調中',
    'ready': '已完成'
};

async function updateStatus(orderId, newStatus) {
    try {
        const response = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const result = await response.json();
        const index = orders.findIndex(o => o.id === orderId);
        if (index !== -1) {
            orders[index] = result;
            displayOrders();
        }
        const statusText = statusTranslations[newStatus] || newStatus;
        showAlert(`訂單 ${result.order_number} 已更新為 ${statusText}`, 'success');
    } catch (error) {
        console.error('Error updating order:', error);
        showAlert('更新訂單狀態時發生錯誤', 'danger');
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

function playNotificationSound() {
    const audio = document.getElementById('notification-sound');
    audio.play().catch(e => console.log('Could not play sound:', e));
}

document.querySelectorAll('input[name="filter"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        currentFilter = e.target.value;
        loadOrders();
    });
});

loadOrders();