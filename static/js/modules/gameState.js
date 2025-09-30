/**
 * Управление состоянием игры
 * Отвечает за хранение и восстановление игрового состояния из localStorage
 */
class GameState {
  constructor() {
    // Начальное состояние игры
    this.state = {
      isOnShift: false,       // Статус смены: начата или нет
      isSearching: false,     // Статус поиска заказов
      currentOrder: null,     // Текущий активный заказ
      userId: 1               // ID пользователя (гостевой по умолчанию)
    };
  }

  // ========== ГЕТТЕРЫ ==========
  // Предоставляют доступ к внутреннему состоянию
  
  /** @returns {boolean} Статус смены */
  get isOnShift() { 
    return this.state.isOnShift; 
  }
  
  /** @returns {boolean} Статус поиска заказов */
  get isSearching() { 
    return this.state.isSearching; 
  }
  
  /** @returns {Object|null} Текущий активный заказ */
  get currentOrder() { 
    return this.state.currentOrder; 
  }
  
  /** @returns {number} ID текущего пользователя */
  get userId() { 
    return this.state.userId; 
  }

  // ========== СЕТТЕРЫ С АВТОСОХРАНЕНИЕМ ==========
  // Каждое изменение состояния автоматически сохраняется в localStorage
  
  /**
   * Установка статуса смены
   * @param {boolean} status - true если смена начата, false если завершена
   */
  setShiftStatus(status) {
    console.log(`🔄 Смена ${status ? 'начата' : 'завершена'}`);
    this.state.isOnShift = status;
    this.save();
  }

  /**
   * Установка статуса поиска заказов
   * @param {boolean} status - true если поиск активен, false если остановлен
   */
  setSearchingStatus(status) {
    console.log(`🔍 Поиск заказов ${status ? 'запущен' : 'остановлен'}`);
    this.state.isSearching = status;
    this.save();
  }

  /**
   * Установка текущего заказа
   * @param {Object|null} order - Объект заказа или null для очистки
   */
  setCurrentOrder(order) {
    if (order) {
      console.log(`📦 Заказ установлен: ${order.id} (${order.pickup?.name || order.pickup_name})`);
    } else {
      console.log('📦 Заказ очищен');
    }
    this.state.currentOrder = order;
    this.save();
  }

  /**
   * Установка ID пользователя
   * @param {number} userId - ID пользователя
   */
  setUserId(userId) {
    console.log(`👤 User ID установлен: ${userId}`);
    this.state.userId = userId;
    this.save();
  }

  // ========== СОХРАНЕНИЕ В LOCALSTORAGE ==========
  
  /**
   * Сохранение текущего состояния в localStorage
   * Добавляет timestamp для проверки свежести данных
   */
  save() {
    try {
      // Добавляем временную метку для валидации при восстановлении
      const stateToSave = {
        ...this.state,
        lastSaved: Date.now()
      };
      
      localStorage.setItem('courierGameState', JSON.stringify(stateToSave));
      console.log('💾 Состояние сохранено в localStorage');
    } catch (error) {
      console.error('❌ Ошибка сохранения состояния:', error);
    }
  }

  // ========== ВОССТАНОВЛЕНИЕ ИЗ LOCALSTORAGE ==========
  
  /**
   * Восстановление состояния игры из localStorage
   * ВАЖНО: Полностью восстанавливает все поля, включая смену и заказ
   * 
   * @returns {boolean} true если состояние успешно восстановлено
   */
  restore() {
    try {
      const saved = localStorage.getItem('courierGameState');
      
      // Если нет сохраненных данных
      if (!saved) {
        console.log('ℹ️ Нет сохраненного состояния');
        return false;
      }
      
      const state = JSON.parse(saved);
      
      // Проверяем давность сохранения (максимум 4 часа)
      const timeDiff = Date.now() - state.lastSaved;
      const maxAge = 4 * 60 * 60 * 1000; // 4 часа в миллисекундах
      
      if (timeDiff > maxAge) {
        console.log('⏰ Сохраненное состояние устарело (>4 часов), сбрасываем');
        localStorage.removeItem('courierGameState');
        return false;
      }
      
      // Восстанавливаем ПОЛНОЕ состояние (включая смену и заказ)
      this.state = {
        isOnShift: state.isOnShift || false,
        isSearching: state.isSearching || false,
        currentOrder: state.currentOrder || null,
        userId: state.userId || 1
      };
      
      // Логируем восстановленное состояние
      console.log('✅ Состояние восстановлено из localStorage:', {
        isOnShift: this.state.isOnShift,
        isSearching: this.state.isSearching,
        hasOrder: !!this.state.currentOrder,
        orderId: this.state.currentOrder?.id,
        userId: this.state.userId,
        savedAgo: Math.round(timeDiff / 1000) + 's'
      });
      
      return true;
    } catch (error) {
      console.error('❌ Ошибка восстановления состояния:', error);
      // При ошибке парсинга очищаем поврежденные данные
      localStorage.removeItem('courierGameState');
      return false;
    }
  }

  // ========== СБРОС СОСТОЯНИЯ ==========
  
  /**
   * Полный сброс состояния игры к начальным значениям
   * Используется при logout или критических ошибках
   */
  reset() {
    console.log('🔄 Полный сброс состояния игры');
    
    this.state = {
      isOnShift: false,
      isSearching: false,
      currentOrder: null,
      userId: 1
    };
    
    this.save();
  }

  // ========== УТИЛИТЫ ==========
  
  /**
   * Получение полного состояния для отладки
   * @returns {Object} Копия текущего состояния
   */
  getFullState() {
    return { ...this.state };
  }

  /**
   * Проверка наличия активного заказа
   * @returns {boolean} true если есть активный заказ
   */
  hasActiveOrder() {
    return this.state.currentOrder !== null;
  }

  /**
   * Валидация состояния игры
   * @returns {Object} Объект с результатами валидации
   */
  validate() {
    const issues = [];
    
    // Проверка: если есть заказ, должна быть начата смена
    if (this.state.currentOrder && !this.state.isOnShift) {
      issues.push('Заказ существует, но смена не начата');
    }
    
    // Проверка: если идет поиск, должна быть начата смена
    if (this.state.isSearching && !this.state.isOnShift) {
      issues.push('Поиск активен, но смена не начата');
    }
    
    // Проверка: не должно быть одновременно заказа и поиска
    if (this.state.currentOrder && this.state.isSearching) {
      issues.push('Одновременно есть заказ и активный поиск');
    }
    
    return {
      valid: issues.length === 0,
      issues: issues
    };
  }
}

// Экспортируем класс в глобальную область видимости
window.GameState = GameState;