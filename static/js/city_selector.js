/**
 * Модуль выбора города при первом запуске
 */

class CitySelector {
    constructor() {
        this.selectedCity = null;
        this.modal = null;
    }

    /**
     * Инициализация модального окна выбора города
     */
    async init() {
        // Проверяем, выбран ли уже город
        const savedCity = localStorage.getItem('selectedCity');
        
        if (savedCity) {
            console.log('Город уже выбран:', savedCity);
            this.selectedCity = savedCity;
            return savedCity;
        }

        // Если город не выбран - показываем модалку
        await this.showCitySelector();
        return this.selectedCity;
    }

    /**
     * Показать модальное окно выбора города
     */
    async showCitySelector() {
        // Загружаем список активных городов
        const cities = await this.loadActiveCities();
        
        if (!cities || cities.length === 0) {
            console.error('Нет доступных городов');
            // По умолчанию Алматы
            this.selectCity('almaty');
            return;
        }

        // Создаем и показываем модальное окно
        this.createModal(cities);
        this.modal.style.display = 'flex';

        // Ждем выбора города
        return new Promise((resolve) => {
            this.onCitySelected = resolve;
        });
    }

    /**
     * Загрузка списка активных городов с сервера
     */
    async loadActiveCities() {
        try {
            const response = await fetch('/api/cities');
            const data = await response.json();
            
            if (data.success) {
                return data.cities;
            }
            
            console.error('Ошибка загрузки городов:', data.error);
            return [];
        } catch (error) {
            console.error('Ошибка при запросе городов:', error);
            return [];
        }
    }

    /**
     * Создание HTML модального окна
     */
    createModal(cities) {
        // Удаляем старую модалку если есть
        const oldModal = document.getElementById('citySelectorModal');
        if (oldModal) {
            oldModal.remove();
        }

        // Создаем новую модалку
        const modalHTML = `
            <div id="citySelectorModal" class="modal-overlay">
                <div class="modal-content city-selector">
                    <div class="modal-header">
                        <h2>🏙️ Выберите город</h2>
                        <p>В каком городе вы хотите работать курьером?</p>
                    </div>
                    
                    <div class="modal-body">
                        <div id="citiesList" class="cities-list">
                            ${this.generateCityCards(cities)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Добавляем в body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        this.modal = document.getElementById('citySelectorModal');

        // Добавляем обработчики кликов
        this.attachEventListeners(cities);
    }

    /**
     * Генерация HTML карточек городов
     */
    generateCityCards(cities) {
        return cities.map(city => {
            const isActive = city.active;
            const disabledClass = isActive ? '' : 'disabled';
            const statusText = isActive ? 'Доступен' : 'Скоро';

            return `
                <div class="city-card ${disabledClass}" data-city-id="${city.id}" data-active="${isActive}">
                    <div class="city-card-content">
                        <div style="display: flex; align-items: center;">
                            <span class="city-icon">🏙️</span>
                            <div class="city-info">
                                <h3>${city.name}</h3>
                                <p>${city.name_en}</p>
                            </div>
                        </div>
                        <div class="city-status">${statusText}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Добавление обработчиков событий
     */
    attachEventListeners(cities) {
        const cityCards = document.querySelectorAll('.city-card');
        
        cityCards.forEach(card => {
            const cityId = card.dataset.cityId;
            const isActive = card.dataset.active === 'true';

            if (isActive) {
                card.addEventListener('click', () => {
                    this.selectCity(cityId);
                    this.closeModal();
                    
                    if (this.onCitySelected) {
                        this.onCitySelected(cityId);
                    }
                });
            }
        });
    }

    /**
     * Выбор города
     */
    selectCity(cityId) {
        this.selectedCity = cityId;
        localStorage.setItem('selectedCity', cityId);
        console.log('Город выбран:', cityId);

        // Уведомляем другие части приложения
        window.dispatchEvent(new CustomEvent('citySelected', { 
            detail: { cityId } 
        }));
    }

    /**
     * Закрытие модального окна
     */
    closeModal() {
        if (this.modal) {
            this.modal.style.display = 'none';
            this.modal.remove();
        }
    }

    /**
     * Получить текущий выбранный город
     */
    getSelectedCity() {
        return this.selectedCity || localStorage.getItem('selectedCity') || 'almaty';
    }

    /**
     * Сбросить выбор города (для тестирования)
     */
    resetCity() {
        localStorage.removeItem('selectedCity');
        this.selectedCity = null;
    }
}

// Экспортируем глобально
window.CitySelector = CitySelector;
