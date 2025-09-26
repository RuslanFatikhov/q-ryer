// static/js/geolocation.js

/**
 * Модуль для работы с геолокацией в курьерском симуляторе
 * Обрабатывает запросы местоположения, отслеживание и валидацию GPS
 */

class GeolocationManager {
  constructor() {
    this.watchId = null;
    this.currentPosition = null;
    this.isTracking = false;
    this.onPositionUpdate = null;
    this.onPermissionGranted = null;
    this.onPermissionDenied = null;
  }

  /**
   * Проверка поддержки геолокации браузером
   * @returns {boolean} Поддерживается ли геолокация
   */
  isSupported() {
    return 'geolocation' in navigator;
  }

  /**
   * Запрос разрешения на геолокацию
   * @returns {Promise<Position>} Промис с позицией пользователя
   */
  async requestPermission() {
    if (!this.isSupported()) {
      throw new Error('Геолокация не поддерживается браузером');
    }

    return new Promise((resolve, reject) => {
      // Опции для высокой точности GPS
      const options = {
        enableHighAccuracy: true,
        timeout: 10000, // 10 секунд на получение позиции
        maximumAge: 60000 // Кэш позиции на 1 минуту
      };

      navigator.geolocation.getCurrentPosition(
        (position) => {
          console.log('✅ GPS разрешение получено:', position);
          this.currentPosition = position;
          
          // Вызываем callback если установлен
          if (this.onPermissionGranted) {
            this.onPermissionGranted(position);
          }
          
          resolve(position);
        },
        (error) => {
          console.error('❌ GPS ошибка:', error);
          
          // Вызываем callback если установлен
          if (this.onPermissionDenied) {
            this.onPermissionDenied(error);
          }
          
          reject(error);
        },
        options
      );
    });
  }

  /**
   * Начать отслеживание позиции пользователя
   * @param {Function} callback Функция для обновлений позиции
   */
  startTracking(callback) {
    if (!this.isSupported()) {
      console.error('❌ Геолокация не поддерживается');
      return false;
    }

    if (this.isTracking) {
      console.log('⚠️ Отслеживание уже активно');
      return true;
    }

    const options = {
      enableHighAccuracy: true,
      timeout: 30000,
      maximumAge: 5000 // Обновлять позицию каждые 5 секунд
    };

    this.watchId = navigator.geolocation.watchPosition(
      (position) => {
        this.currentPosition = position;
        console.log('📍 Позиция обновлена:', position.coords);

        // Проверяем точность GPS
        const accuracy = position.coords.accuracy;
        if (accuracy > 100) {
          console.warn('⚠️ Низкая точность GPS:', accuracy, 'метров');
        }

        // Вызываем callback
        if (callback) {
          callback(position);
        }

        // Вызываем общий callback если установлен
        if (this.onPositionUpdate) {
          this.onPositionUpdate(position);
        }
      },
      (error) => {
        console.error('❌ Ошибка отслеживания GPS:', error);
        this.handleGeolocationError(error);
      },
      options
    );

    this.isTracking = true;
    console.log('🎯 Отслеживание GPS началось');
    return true;
  }

  /**
   * Остановить отслеживание позиции
   */
  stopTracking() {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
      this.isTracking = false;
      console.log('🛑 Отслеживание GPS остановлено');
    }
  }

  /**
   * Получить текущую позицию
   * @returns {Object|null} Объект с координатами или null
   */
  getCurrentPosition() {
    if (!this.currentPosition) return null;

    const coords = this.currentPosition.coords;
    return {
      lat: coords.latitude,
      lng: coords.longitude,
      accuracy: coords.accuracy,
      timestamp: this.currentPosition.timestamp
    };
  }

  /**
   * Проверка качества GPS сигнала
   * @returns {string} Качество сигнала: excellent, good, fair, poor
   */
  getGPSQuality() {
    if (!this.currentPosition) return 'unknown';

    const accuracy = this.currentPosition.coords.accuracy;
    
    if (accuracy <= 5) return 'excellent';
    if (accuracy <= 15) return 'good';
    if (accuracy <= 50) return 'fair';
    return 'poor';
  }

  /**
   * Обработка ошибок геолокации
   * @param {GeolocationPositionError} error Ошибка геолокации
   */
  handleGeolocationError(error) {
    let message = 'Неизвестная ошибка GPS';
    
    switch(error.code) {
      case error.PERMISSION_DENIED:
        message = 'Доступ к местоположению запрещен';
        break;
      case error.POSITION_UNAVAILABLE:
        message = 'Местоположение недоступно';
        break;
      case error.TIMEOUT:
        message = 'Таймаут получения местоположения';
        break;
    }
    
    console.error('GPS Error:', message, error);
    
    // Можно добавить показ уведомления пользователю
    this.showGPSError(message);
  }

  /**
   * Показ ошибки GPS пользователю
   * @param {string} message Сообщение об ошибке
   */
  showGPSError(message) {
    // Создаем временное уведомление
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #ff4444;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 10000;
      font-family: Inter, sans-serif;
    `;
    notification.textContent = `🚫 ${message}`;
    
    document.body.appendChild(notification);
    
    // Убираем уведомление через 5 секунд
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  }

  /**
   * Проверка, находится ли пользователь в заданном радиусе от точки
   * @param {number} targetLat Широта целевой точки
   * @param {number} targetLng Долгота целевой точки  
   * @param {number} radiusMeters Радиус в метрах
   * @returns {boolean} Находится ли в радиусе
   */
  isWithinRadius(targetLat, targetLng, radiusMeters) {
    if (!this.currentPosition) return false;

    const userPos = this.getCurrentPosition();
    const distance = this.calculateDistance(
      userPos.lat, userPos.lng,
      targetLat, targetLng
    );

    return distance <= radiusMeters;
  }

  /**
   * Вычисление расстояния между двумя точками (формула гаверсинуса)
   * @param {number} lat1 Широта первой точки
   * @param {number} lng1 Долгота первой точки
   * @param {number} lat2 Широта второй точки
   * @param {number} lng2 Долгота второй точки
   * @returns {number} Расстояние в метрах
   */
  calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371000; // Радиус Земли в метрах
    const dLat = this.toRadians(lat2 - lat1);
    const dLng = this.toRadians(lng2 - lng1);
    
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
              
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    
    return R * c;
  }

  /**
   * Преобразование градусов в радианы
   * @param {number} degrees Градусы
   * @returns {number} Радианы
   */
  toRadians(degrees) {
    return degrees * (Math.PI/180);
  }
}

// Экспортируем класс для использования в других файлах
window.GeolocationManager = GeolocationManager;