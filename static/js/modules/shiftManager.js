/**
 * Управление сменами и поиском заказов
 */
class ShiftManager {
  constructor(gameState, socketManager) {
    this.gameState = gameState;
    this.socketManager = socketManager;
    this.SHIFT_STATES = {
      REQUESTING_GPS: 'requesting_gps',
      START_SHIFT: 'start_shift',
      END_SHIFT: 'end_shift', 
      SEARCHING: 'searching'
    };
  }

  // Обработчик клика по кнопке смены
  async handleShiftButtonClick() {
    console.log("Клик по кнопке смены");
    
    try {
      if (!window.geoManager?.currentPosition) {
        console.log("Запрашиваем GPS...");
        this.updateShiftButton('REQUESTING_GPS_ACTIVE');
        
        try {
          await window.geoManager.requestPermission();
        } catch (error) {
          console.error("GPS запрос отклонен:", error);
        }
        return;
      }
      
      if (!this.gameState.isOnShift) {
        await this.startShift();
      } else if (this.gameState.isSearching) {
        await this.stopSearching();
      } else {
        await this.endShift();
      }
    } catch (error) {
      console.error("Ошибка при обработке клика:", error);
      
      if (!window.geoManager?.currentPosition) {
        this.updateShiftButton(this.SHIFT_STATES.REQUESTING_GPS);
      } else if (!this.gameState.isOnShift) {
        this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
      }
    }
  }

  // Начало смены
  async startShift() {
    console.log("Начинаем смену");
    
    if (!window.geoManager?.currentPosition) {
      throw new Error("GPS недоступен");
    }

    try {
      const response = await fetch('/api/start_shift', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.gameState.userId
        })
      });

      if (!response.ok) {
        throw new Error('Не удалось начать смену');
      }

      this.gameState.setShiftStatus(true);
      
      window.geoManager.startTracking((position) => {
        this.sendPositionUpdate(position);
      });

      this.socketManager.loginUser(this.gameState.userId);
      
      setTimeout(() => {
        this.startSearching();
      }, 500);
      
    } catch (error) {
      throw new Error('Ошибка сервера: ' + error.message);
    }
  }

  // Остановка поиска заказов
  async stopSearching() {
    console.log("Останавливаем поиск");
    
    this.gameState.setSearchingStatus(false);
    this.updateShiftButton(this.SHIFT_STATES.END_SHIFT);
    
    this.socketManager.stopOrderSearch();
  }

  // Начало поиска заказов
  async startSearching() {
    console.log("Начинаем поиск заказов");
    
    this.gameState.setSearchingStatus(true);
    this.updateShiftButton(this.SHIFT_STATES.SEARCHING);
    
    this.socketManager.startOrderSearch(5);
  }

  // Окончание смены
  async endShift() {
    console.log("Заканчиваем смену");
    
    if (this.gameState.currentOrder) {
      if (!confirm("У вас есть активный заказ. Завершить смену?")) {
        return;
      }
    }

    try {
      const response = await fetch('/api/stop_shift', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.gameState.userId
        })
      });

      if (!response.ok) {
        throw new Error('Не удалось закончить смену');
      }

      this.gameState.setShiftStatus(false);
      this.gameState.setSearchingStatus(false);
      this.gameState.setCurrentOrder(null);
      
      window.geoManager.stopTracking();
      this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
      
    } catch (error) {
      throw new Error('Ошибка завершения смены: ' + error.message);
    }
  }

  // Обновление кнопки смены
  updateShiftButton(state) {
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    
    if (!button || !buttonText) return;
    
    switch (state) {
      case this.SHIFT_STATES.REQUESTING_GPS:
        buttonText.textContent = "Разрешить GPS";
        button.style.backgroundColor = "#ff6600";
        button.disabled = false;
        break;
        
      case 'REQUESTING_GPS_ACTIVE':
        buttonText.textContent = 'Запрашиваем GPS...';
        button.style.backgroundColor = "#ff8800";
        button.disabled = true;
        break;
        
      case this.SHIFT_STATES.START_SHIFT:
        buttonText.textContent = "Начать смену";
        button.style.backgroundColor = "#121212";
        button.disabled = false;
        break;
        
      case this.SHIFT_STATES.END_SHIFT:
        buttonText.textContent = "Завершить смену";
        button.style.backgroundColor = "#ff4444";
        button.disabled = false;
        break;
        
      case this.SHIFT_STATES.SEARCHING:
        buttonText.textContent = 'Ищем заказы...';
        button.style.backgroundColor = "#00aa44";
        button.disabled = false;
        break;
        
      case 'UNSUPPORTED':
        buttonText.textContent = "GPS недоступен";
        button.style.backgroundColor = "#666666";
        button.disabled = true;
        break;
    }
  }

  // Отправка обновления позиции
  sendPositionUpdate(position) {
    this.socketManager.sendPositionUpdate(position);
  }

  // Обработчики GPS событий
  onGPSPermissionGranted(position) {
    console.log("GPS разрешение получено");
    
    if (window.mapManager) {
      window.mapManager.setView(position.coords, 16);
      window.mapManager.addUserMarker(position.coords);
    }
    
    this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
  }

  onGPSPermissionDenied(error) {
    console.error("GPS доступ запрещен:", error);
    this.updateShiftButton(this.SHIFT_STATES.REQUESTING_GPS);
  }

  onPositionUpdate(position) {
    if (window.mapManager) {
      window.mapManager.updateUserMarker(position.coords);
    }
  }
}

window.ShiftManager = ShiftManager;
