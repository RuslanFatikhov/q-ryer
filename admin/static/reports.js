/**
 * Управление жалобами в админ-панели
 */

let currentPage = 1;
let currentFilters = {
    status: ''
};

// Загрузка жалоб
async function loadReports(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            status: currentFilters.status
        });
        
        const data = await AdminAPI.get(`/api/admin/reports?${params}`);
        
        renderReportsTable(data.reports);
        Pagination.render('pagination', page, data.pagination.pages, loadReports);
        
        currentPage = page;
    } catch (error) {
        alert('Ошибка загрузки жалоб: ' + error.message);
    }
}

// Рендер таблицы жалоб
function renderReportsTable(reports) {
    const tbody = document.getElementById('reportsTableBody');
    tbody.innerHTML = '';
    
    if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Жалобы не найдены</td></tr>';
        return;
    }
    
    reports.forEach(report => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${report.id}</td>
            <td>User #${report.user_id}</td>
            <td>${report.order_id || '-'}</td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${report.message}
            </td>
            <td>${Format.status(report.status, 'report')}</td>
            <td>${Format.date(report.created_at)}</td>
            <td>
                <button class="btn btn-secondary btn-small" onclick="handleReport(${report.id})">
                    Обработать
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Обработка жалобы
async function handleReport(reportId) {
    try {
        // Находим жалобу в текущем списке
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 20,
            status: currentFilters.status
        });
        
        const data = await AdminAPI.get(`/api/admin/reports?${params}`);
        const report = data.reports.find(r => r.id === reportId);
        
        if (!report) {
            alert('Жалоба не найдена');
            return;
        }
        
        // Заполняем форму
        document.getElementById('reportId').value = report.id;
        document.getElementById('reportMessage').textContent = report.message;
        document.getElementById('reportStatus').value = report.status;
        document.getElementById('adminResponse').value = '';
        
        Modal.open('reportModal');
    } catch (error) {
        alert('Ошибка загрузки жалобы: ' + error.message);
    }
}

// Сохранение решения по жалобе
async function saveReport(event) {
    event.preventDefault();
    
    const reportId = document.getElementById('reportId').value;
    const status = document.getElementById('reportStatus').value;
    const adminResponse = document.getElementById('adminResponse').value;
    
    try {
        await AdminAPI.post(`/api/admin/reports/${reportId}/status`, {
            status: status,
            admin_response: adminResponse
        });
        
        Modal.close('reportModal');
        Notification.show('Жалоба обработана');
        loadReports(currentPage);
    } catch (error) {
        alert('Ошибка сохранения: ' + error.message);
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Загрузка жалоб
    loadReports();
    
    // Фильтр по статусу
    document.getElementById('applyFilters').addEventListener('click', () => {
        currentFilters.status = document.getElementById('statusFilter').value;
        loadReports(1);
    });
    
    // Форма обработки жалобы
    document.getElementById('reportForm').addEventListener('submit', saveReport);
});
