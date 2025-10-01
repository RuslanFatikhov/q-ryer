/**
 * Управление настройками системы
 */

// Загрузка текущих настроек
async function loadConfig() {
    try {
        const data = await AdminAPI.get('/api/admin/config');
        const config = data.game_config;
        
        // Заполняем форму
        document.getElementById('base_payment').value = config.base_payment;
        document.getElementById('pickup_fee').value = config.pickup_fee;
        document.getElementById('dropoff_fee').value = config.dropoff_fee;
        document.getElementById('distance_rate').value = config.distance_rate;
        document.getElementById('on_time_bonus').value = config.on_time_bonus;
        document.getElementById('pickup_radius').value = config.pickup_radius;
        document.getElementById('dropoff_radius').value = config.dropoff_radius;
        document.getElementById('delivery_speed_kmh').value = config.delivery_speed_kmh;
        document.getElementById('delivery_base_time').value = config.delivery_base_time;
        document.getElementById('max_gps_accuracy').value = config.max_gps_accuracy;
    } catch (error) {
        alert('Ошибка загрузки настроек: ' + error.message);
    }
}

// Сохранение настроек
async function saveConfig(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const config = {};
    
    // Собираем данные из формы
    formData.forEach((value, key) => {
        config[key] = parseFloat(value);
    });
    
    try {
        await AdminAPI.post('/api/admin/config', config);
        
        // Показываем уведомление
        const notification = document.getElementById('saveNotification');
        notification.classList.add('show');
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    } catch (error) {
        alert('Ошибка сохранения настроек: ' + error.message);
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Загрузка текущих настроек
    loadConfig();
    
    // Обработка формы
    document.getElementById('configForm').addEventListener('submit', saveConfig);
});
