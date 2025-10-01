/**
 * Управление состоянием игры
 */
class GameState {
  constructor() {
    // Проверяем авторизацию
    const savedUserId = localStorage.getItem('courier_user_id');
    if (!savedUserId) {
      // Не авторизован - редирект на главную
      window.location.href = '/';
      return;
    }
    
    this.state = {
      isOnShift: false,
      isSearching: false,
      currentOrder: null,
      userId: parseInt(savedUserId)
    };
    
    // Загружаем имя пользователя
    this.username = localStorage.getItem('courier_username') || 'Игрок';
  }

  // Геттеры
  get isOnShift() { return this.state.isOnShift; }
  get isSearching() { return this.state.isSearching; }
  get currentOrder() { return this.state.currentOrder; }
  get userId() { return this.state.userId; }

  // Сеттеры с автосохранением
  setShiftStatus(status) {
    this.state.isOnShift = status;
    this.save();
  }

  setSearchingStatus(status) {
    this.state.isSearching = status;
    this.save();
  }

  setCurrentOrder(order) {
    this.state.currentOrder = order;
    this.save();
  }

  // Сохранение в localStorage
  save() {
    const stateToSave = {
      ...this.state,
      lastSaved: Date.now()
    };
    localStorage.setItem('courierGameState', JSON.stringify(stateToSave));
  }

  // Восстановление из localStorage
  restore() {
    try {
      const saved = localStorage.getItem('courierGameState');
      if (!saved) return false;
      
      const state = JSON.parse(saved);
      const timeDiff = Date.now() - state.lastSaved;
      
      // Если прошло больше 4 часов - сбрасываем
      if (timeDiff > 4 * 60 * 60 * 1000) {
        localStorage.removeItem('courierGameState');
        return false;
      }
      
      this.state = { ...state };
      delete this.state.lastSaved;
      
      // Сбрасываем смену и поиск при загрузке
      this.state.isOnShift = false;
      this.state.isSearching = false;
      
      console.log("Состояние восстановлено (смена сброшена)");
      
      return true;
    } catch (error) {
      console.error("Ошибка восстановления состояния:", error);
      return false;
    }
  }

  // Сброс состояния
  reset() {
    this.state = {
      isOnShift: false,
      isSearching: false,
      currentOrder: null,
      userId: this.userId
    };
    this.save();
  }
  
  // Выход из аккаунта
  logout() {
    localStorage.removeItem('courier_user_id');
    localStorage.removeItem('courier_username');
    localStorage.removeItem('courierGameState');
    window.location.href = '/';
  }
}

// Экспорт
window.GameState = GameState;
