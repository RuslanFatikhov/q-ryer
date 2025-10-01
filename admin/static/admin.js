/**
 * Общие функции для админ-панели Courier Sim
 */

// Утилиты для работы с API
const AdminAPI = {
    /**
     * Базовый запрос к API
     */
    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Ошибка запроса');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    /**
     * GET запрос
     */
    async get(url) {
        return this.request(url, { method: 'GET' });
    },
    
    /**
     * POST запрос
     */
    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Утилиты для работы с модальными окнами
const Modal = {
    /**
     * Открыть модальное окно
     */
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
        }
    },
    
    /**
     * Закрыть модальное окно
     */
    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    },
    
    /**
     * Инициализация закрытия по клику
     */
    init() {
        // Закрытие по клику на крестик
        document.querySelectorAll('.modal .close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.classList.remove('show');
                }
            });
        });
        
        // Закрытие по клику вне модального окна
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('show');
                }
            });
        });
    }
};

// Утилиты для пагинации
const Pagination = {
    /**
     * Рендер пагинации
     */
    render(containerId, currentPage, totalPages, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        // Кнопка "Назад"
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '← Назад';
        prevBtn.disabled = currentPage === 1;
        prevBtn.addEventListener('click', () => onPageChange(currentPage - 1));
        container.appendChild(prevBtn);
        
        // Номера страниц
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.textContent = i;
            pageBtn.classList.toggle('active', i === currentPage);
            pageBtn.addEventListener('click', () => onPageChange(i));
            container.appendChild(pageBtn);
        }
        
        // Кнопка "Вперед"
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Вперед →';
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.addEventListener('click', () => onPageChange(currentPage + 1));
        container.appendChild(nextBtn);
    }
};

// Утилиты для форматирования
const Format = {
    /**
     * Форматирование даты
     */
    date(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    /**
     * Форматирование денег
     */
    money(amount) {
        return `$${parseFloat(amount).toFixed(2)}`;
    },
    
    /**
     * Форматирование статуса
     */
    status(status, type = 'user') {
        const statusMap = {
            user: {
                online: { text: 'Онлайн', class: 'status-online' },
                offline: { text: 'Оффлайн', class: 'status-offline' }
            },
            order: {
                pending: { text: 'Ожидание', class: 'status-pending' },
                active: { text: 'Активный', class: 'status-active' },
                completed: { text: 'Завершен', class: 'status-completed' },
                cancelled: { text: 'Отменен', class: 'status-cancelled' }
            },
            report: {
                pending: { text: 'Ожидание', class: 'status-pending' },
                resolved: { text: 'Решено', class: 'status-completed' },
                rejected: { text: 'Отклонено', class: 'status-cancelled' }
            }
        };
        
        const statusInfo = statusMap[type]?.[status] || { text: status, class: '' };
        return `<span class="status-badge ${statusInfo.class}">${statusInfo.text}</span>`;
    }
};

// Уведомления
const Notification = {
    /**
     * Показать уведомление
     */
    show(message, duration = 3000) {
        // Создаем элемент уведомления если его нет
        let notification = document.getElementById('globalNotification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'globalNotification';
            notification.className = 'notification';
            document.body.appendChild(notification);
        }
        
        notification.textContent = message;
        notification.classList.add('show');
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, duration);
    }
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    Modal.init();
});
