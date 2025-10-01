/**
 * Управление пользователями в админ-панели
 */

let currentPage = 1;
let currentFilters = {
    status: 'all',
    search: ''
};

// Загрузка пользователей
async function loadUsers(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            status: currentFilters.status === 'all' ? '' : currentFilters.status,
            search: currentFilters.search
        });
        
        const data = await AdminAPI.get(`/api/admin/users?${params}`);
        
        renderUsersTable(data.users);
        Pagination.render('pagination', page, data.pagination.pages, loadUsers);
        
        currentPage = page;
    } catch (error) {
        alert('Ошибка загрузки пользователей: ' + error.message);
    }
}

// Рендер таблицы пользователей
function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Пользователи не найдены</td></tr>';
        return;
    }
    
    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.email || '-'}</td>
            <td>${Format.money(user.balance)}</td>
            <td>${user.total_deliveries}</td>
            <td>${Format.status(user.is_online ? 'online' : 'offline', 'user')}</td>
            <td>
                <button class="btn btn-secondary btn-small" onclick="editUser(${user.id})">
                    Редактировать
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Редактирование пользователя
async function editUser(userId) {
    try {
        const user = await AdminAPI.get(`/api/admin/users/${userId}`);
        
        document.getElementById('editUserId').value = user.id;
        document.getElementById('editUsername').value = user.username;
        document.getElementById('editBalance').value = user.balance;
        document.getElementById('editIsActive').checked = user.is_active;
        
        Modal.open('editUserModal');
    } catch (error) {
        alert('Ошибка загрузки пользователя: ' + error.message);
    }
}

// Сохранение изменений пользователя
async function saveUser(event) {
    event.preventDefault();
    
    const userId = document.getElementById('editUserId').value;
    const balance = parseFloat(document.getElementById('editBalance').value);
    const isActive = document.getElementById('editIsActive').checked;
    
    try {
        await AdminAPI.post(`/api/admin/users/${userId}`, {
            balance: balance,
            is_active: isActive
        });
        
        Modal.close('editUserModal');
        Notification.show('Пользователь обновлен');
        loadUsers(currentPage);
    } catch (error) {
        alert('Ошибка сохранения: ' + error.message);
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Загрузка пользователей
    loadUsers();
    
    // Фильтр по статусу
    document.getElementById('statusFilter').addEventListener('change', (e) => {
        currentFilters.status = e.target.value;
        loadUsers(1);
    });
    
    // Поиск
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentFilters.search = e.target.value;
            loadUsers(1);
        }, 500);
    });
    
    // Форма редактирования
    document.getElementById('editUserForm').addEventListener('submit', saveUser);
});
