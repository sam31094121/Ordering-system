let orders = [];
let currentFilter = 'all';

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed bottom-0 end-0 m-3`;
    alertDiv.style.zIndex = 1000;
    alertDiv.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning">待處理</span>',
        'received': '<span class="badge bg-info">已接單</span>',
        'cooking': '<span class="badge bg-primary">烹調中</span>',
        'ready': '<span class="badge bg-success">準備好</span>',
        'completed': '<span class="badge bg-secondary">已完成</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">未知</span>';
}

function getStatusButtons(order) {
    switch (order.status) {
        case 'pending':
            return `
                <button class="btn btn-info btn-sm" onclick="updateStatus(${order.id}, 'received')">
                    👀 接單
                </button>
            `;
        case 'received':
            return `
                <button class="btn btn-primary btn-sm" onclick="updateStatus(${order.id}, 'cooking')">
                    🍳 開始烹調
                </button>
            `;
        case 'cooking':
            return `
                <button class="btn btn-success btn-sm" onclick="updateStatus(${order.id}, 'ready')">
                    ✅ 標記完成
                </button>
            `;
        case 'ready':
            return `
                <button class="btn btn-secondary btn-sm" onclick="updateStatus(${order.id}, 'completed')">
                    ✔️ 訂單送達
                </button>
            `;
        default:
            return '';
    }
}

async function confirmDeleteOrder(orderId) {
    if (confirm('確定要刪除此訂單嗎？此操作無法復原！')) {
        try {
            const response = await fetch(`/api/orders/${orderId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                orders = orders.filter(order => order.id !== orderId);
                displayOrders();
                showAlert('訂單已成功刪除', 'success');
            } else {
                const errorData = await response.json();
                showAlert(`刪除訂單失敗: ${errorData.error || '未知錯誤'}`, 'danger');
            }
        } catch (error) {
            console.error('Error deleting order:', error);
            showAlert('刪除訂單時發生錯誤', 'danger');
        }
    }
}

async function loadOrders() {
    try {
        const url = `/api/orders?filter=${currentFilter}`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        orders = await response.json();
        for (let order of orders) {
            order.items = JSON.parse(order.items); // 還原 items 為陣列
        }
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
        const orderTime = new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
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
                    <div class="mt-2">
                        <button class="btn btn-danger btn-sm" onclick="confirmDeleteOrder(${order.id})">
                            🗑️ 刪除訂單
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function updateStatus(orderId, newStatus) {
    try {
        const response = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            const updatedOrder = await response.json();
            updatedOrder.items = JSON.parse(updatedOrder.items); // 還原 items
            const index = orders.findIndex(order => order.id === orderId);
            if (index !== -1) {
                orders[index] = updatedOrder;
                displayOrders();
            }
            socket.emit('order_updated', updatedOrder); // 修正為 socket 而非 socketio
            showAlert('訂單狀態更新成功', 'success');
        } else {
            const errorData = await response.json();
            showAlert(`更新訂單狀態失敗: ${errorData.error || '未知錯誤'}`, 'danger');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showAlert('更新狀態時發生錯誤', 'danger');
    }
}

// Socket.IO 連線
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        loadOrders();
    });

    socket.on('new_order', (order) => {
        console.log('New order received:', order); // 添加日誌以便排查
        order.items = JSON.parse(order.items);
        orders.unshift(order);
        displayOrders();
        showAlert('收到新訂單！', 'success');
    });

    socket.on('order_updated', (updatedOrder) => {
        console.log('Order updated:', updatedOrder); // 添加日誌以便排查
        updatedOrder.items = JSON.parse(updatedOrder.items);
        const index = orders.findIndex(order => order.id === updatedOrder.id);
        if (index !== -1) {
            orders[index] = updatedOrder;
            displayOrders();
        }
    });

    socket.on('order_deleted', (data) => {
        console.log('Order deleted:', data); // 添加日誌以便排查
        orders = orders.filter(order => order.id !== data.order_id);
        displayOrders();
        showAlert('訂單已刪除', 'success');
    });

    socket.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error);
        showAlert('無法連接到服務器，請檢查網絡', 'danger');
    });

    document.querySelectorAll('input[name="filter"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentFilter = e.target.value;
            loadOrders();
        });
    });
});
