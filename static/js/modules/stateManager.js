/**
 * Менеджер синхронизации состояния с сервером
 */
class StateManager {
  constructor(gameState) {
    this.gameState = gameState;
  }

  // Восстановление полного состояния с сервера
  async restoreFromServer() {
    try {
      console.log("Загрузка состояния с сервера...");
      
      const response = await fetch(`/api/status?user_id=${this.gameState.userId}`);
      
      if (!response.ok) {
        console.log("Не удалось загрузить состояние");
        return false;
      }
      
      const data = await response.json();
      
      // Обновляем баланс в UI
      const balanceEl = document.getElementById('balanceAmount');
      if (balanceEl && data.user) {
        balanceEl.textContent = data.user.balance.toFixed(2);
      }
      
      // Если есть активный заказ - восстанавливаем его
      if (data.active_order) {
        console.log("Найден активный заказ:", data.active_order);
        
        // Сохраняем заказ в состояние
        this.gameState.setCurrentOrder(data.active_order);
        this.gameState.setShiftStatus(true);
        
        // Показываем на карте
        if (window.mapManager) {
          window.mapManager.showOrder(data.active_order);
        }
        
        // Запускаем проверку зон
        if (window.shiftManager) {
          window.shiftManager.startZoneChecking();
          
          // Определяем состояние кнопки
          if (data.active_order.pickup_time) {
            window.shiftManager.updateShiftButton('to_dropoff');
          } else {
            window.shiftManager.updateShiftButton('to_pickup');
          }
        }
        
        console.log("Активный заказ восстановлен");
        return true;
      }
      
      console.log("Активных заказов нет");
      return false;
      
    } catch (error) {
      console.error("Ошибка загрузки состояния:", error);
      return false;
    }
  }
}

window.StateManager = StateManager;
