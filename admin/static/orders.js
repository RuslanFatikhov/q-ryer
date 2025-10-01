/**
 * Управление заказами в админ-панели
 */

let currentPage = 1;
let currentFilters = {
    status: '',
    dateFrom: '',
    dateTo: ''
};

// Загрузка заказов
async function loadOrders(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            status: currentFilters.status,
            date_from: currentFilters.dateFrom,
            date_to: currentFilters.dateTo
        });
        
        const data = await AdminAPI.get(`/api/admin/orders?${params}`);
        
        renderOrdersTable(data.orders);
        Pagination.render('pagination', page, data.pagination.pages, loadOrders);
        
        currentPage = page;
    } catch (error) {
        alert('Ошибка загрузки заказов: ' + error.message);
    }
}

// Рендер таблицы заказов
function renderOrdersTable(orders) {
    const tbody = document.getElementById('ordersTableBody');
    tbody.innerHTML = '';
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Заказы не найдены</td></tr>';
        return;
    }
    
    orders.forEach(order => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${order.id}</td>
            <td>${order.user_name || 'User #' + order.user_id}</td>
            <td>${order.pickup.name}</td>
            <td>${order.dropoff.address}</td>
            <td>${Format.money(order.amount)}</td>
            <td>${Format.status(order.status, 'order')}</td>
            <td>${Format.date(order.created_at)}</td>
            <td>
                <button class="btn btn-secondary btn-small" onclick="viewOrderDetails(${order.id})">
                    Детали
                </button>
                ${order.status === 'active' ? 
                    `<button class="btn btn-danger btn-small" onclick="cancelOrder(${order.id})">Отменить</button>` 
                    : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Просмотр деталей заказа
async function viewOrderDetails(orderId) {
    try {
        // Находим заказ в текущем списке
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 20,
            status: currentFilters.status
        });
        
        const data = await AdminAPI.get(`/api/admin/orders?${params}`);
        const order = data.orders.find(o => o.id === orderId);
        
        if (!order) {
            alert('Заказ не найден');
            return;
        }
        
        // Формируем HTML с деталями
        const detailsHTML = `
            <div style="display: grid; gap: 16px;">
                <div>
                    <strong>ID заказа:</strong> ${order.id}<br>
                    <strong>Статус:</strong> ${Format.status(order.status, 'order')}<br>
                    <strong>Пользователь:</strong> ${order.user_name || 'User #' + order.user_id}
                </div>
                
                <div>
                    <strong>Откуда:</strong> ${order.pickup.name}<br>
                    <strong>Координаты:</strong> ${order.pickup.lat.toFixed(4)}, ${order.pickup.lng.toFixed(4)}
                </div>
                
                <div>
                    <strong>Куда:</strong> ${order.dropoff.address}<br>
                    <strong>Координаты:</strong> ${order.dropoff.lat.toFixed(4)}, ${order.dropoff.lng.toFixed(4)}
                </div>
                
                <div>
                    <strong>Расстояние:</strong> ${order.distance_km} км<br>
                    <strong>Таймер:</strong> ${Math.floor(order.timer_seconds / 60)} мин<br>
                    <strong>Сумма:</strong> ${Format.money(order.amount)}
                </div>
                
                <div>
                    <strong>Создан:</strong> ${Format.date(order.created_at)}<br>
                    ${order.pickup_time ? `<strong>Забран:</strong> ${Format.date(order.pickup_time)}<br>` : ''}
                    ${order.delivery_time ? `<strong>Доставлен:</strong> ${Format.date(order.delivery_time)}` : ''}
                </div>
            </div>
        `;
        
        document.getElementById('orderDetailsBody').innerHTML = detailsHTML;
        Modal.open('orderDetailsModal');
    } catch (error) {
        alert('Ошибка загрузки деталей: ' + error.message);
    }
}

// Отмена заказа
async function cancelOrder(orderId) {
    if (!confirm('Вы уверены, что хотите отменить этот заказ?')) {
        return;
    }
    
    try {
        await AdminAPI.post(`/api/order/cancel`, {
            user_id: 1, // Отмена от имени системы
            order_id: orderId
        });
        
        Notification.show('Заказ отменен');
        loadOrders(currentPage);
    } catch (error) {
        alert('Ошибка отмены заказа: ' + error.message);
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Загрузка заказов
    loadOrders();
    
    // Применение фильтров
    document.getElementById('applyFilters').addEventListener('click', () => {
        currentFilters.status = document.getElementById('statusFilter').value;
        currentFilters.dateFrom = document.getElementById('dateFrom').value;
        currentFilters.dateTo = document.getElementById('dateTo').value;
        loadOrders(1);
    });
});
