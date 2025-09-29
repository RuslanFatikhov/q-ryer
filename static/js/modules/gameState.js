/**
 * Управление состоянием игры
 */
class GameState {
  constructor() {
    this.state = {
      isOnShift: false,
      isSearching: false,
      currentOrder: null,
      userId: 1
    };
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
      userId: 1
    };
    this.save();
  }
}

// Экспорт
window.GameState = GameState;
