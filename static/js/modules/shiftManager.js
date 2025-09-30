/**
 * Управление сменами и поиском заказов
 */
class ShiftManager {
  constructor(gameState, socketManager) {
    this.gameState = gameState;
    this.socketManager = socketManager;
    
    // Флаг для отслеживания, что смена началась в ЭТОЙ сессии браузера
    // (а не восстановлена из localStorage)
    this._shiftStartedInThisSession = false;
    
    this.SHIFT_STATES = {
      REQUESTING_GPS: 'requesting_gps',
      START_SHIFT: 'start_shift',
      END_SHIFT: 'end_shift', 
      SEARCHING: 'searching',
      TO_PICKUP: 'to_pickup',
      TO_DROPOFF: 'to_dropoff'
    };
  }

  // Обработчик клика по кнопке смены
  async handleShiftButtonClick() {
    console.log("Клик по кнопке смены");
    
    console.log("Состояние:", {
      hasGPS: !!window.geoManager?.currentPosition,
      isOnShift: this.gameState.isOnShift,
      isSearching: this.gameState.isSearching,
      hasOrder: !!this.gameState.currentOrder
    });
    
    try {
      // 1. Если нет GPS - запрашиваем
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
      
      // 2. ВАЖНО: Если смена восстановлена из localStorage, но GPS только что получили
      // то нужно сбросить флаг смены, чтобы пользователь начал заново
      if (this.gameState.isOnShift && !this._shiftStartedInThisSession) {
        console.log("⚠️ Смена восстановлена из localStorage, но не начата в этой сессии - сбрасываем");
        this.gameState.setShiftStatus(false);
        this.gameState.setSearchingStatus(false);
        // Оставляем заказ для восстановления после перезапуска смены
        this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
        return;
      }
      
      // 3. Если смена не начата - начинаем
      if (!this.gameState.isOnShift) {
        console.log("→ Начинаем смену");
        await this.startShift();
        return;
      }
      
      // 4. Если идет поиск - останавливаем
      if (this.gameState.isSearching) {
        console.log("→ Останавливаем поиск");
        await this.stopSearching();
        return;
      }
      
      // 5. Если есть активный заказ - открываем навигацию
      if (this.gameState.currentOrder) {
        console.log("→ Открываем навигацию к заказу");
        this.openNavigation();
        return;
      }
      
      // 6. Иначе - завершаем смену
      console.log("→ Завершаем смену");
      await this.endShift();
      
    } catch (error) {
      console.error("Ошибка при обработке клика:", error);
      
      // Восстанавливаем правильное состояние кнопки
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
        const error = await response.json();
        throw new Error(error.error || 'Не удалось начать смену');
      }

      // ВАЖНО: Устанавливаем флаг, что смена началась в этой сессии
      this._shiftStartedInThisSession = true;
      
      this.gameState.setShiftStatus(true);
      console.log("✅ Смена начата");
      
      // Запускаем отслеживание GPS
      window.geoManager.startTracking((position) => {
        this.sendPositionUpdate(position);
      });

      // Логинимся в WebSocket
      this.socketManager.loginUser(this.gameState.userId);
      
      // Небольшая задержка перед началом поиска
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
        const error = await response.json();
        throw new Error(error.error || 'Не удалось закончить смену');
      }

      // Сбрасываем флаг смены в этой сессии
      this._shiftStartedInThisSession = false;
      
      this.gameState.setShiftStatus(false);
      this.gameState.setSearchingStatus(false);
      this.gameState.setCurrentOrder(null);
      
      window.geoManager.stopTracking();
      
      if (window.mapManager) {
        window.mapManager.clearOrderMarkers();
      }
      
      this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
      
      console.log("✅ Смена завершена");
      
    } catch (error) {
      throw new Error('Ошибка завершения смены: ' + error.message);
    }
  }

  // Открыть навигацию к точке
  openNavigation() {
    const order = this.gameState.currentOrder;
    if (!order) {
      console.error("Нет активного заказа для навигации");
      return;
    }
    
    // Определяем куда идти
    let target, targetName;
    if (!order.pickup_time) {
      // Идём к ресторану
      target = order.pickup;
      targetName = order.pickup.name;
    } else {
      // Идём к клиенту
      target = order.dropoff;
      targetName = order.dropoff.address;
    }
    
    const lat = target.lat;
    const lng = target.lng;
    
    console.log("Открываем навигацию к:", targetName);
    
    // Открываем 2GIS с маршрутом
    const url = `https://2gis.kz/almaty/directions/points/${lng},${lat}`;
    window.open(url, '_blank');
  }

  // Обновление кнопки смены
  updateShiftButton(state) {
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    
    if (!button || !buttonText) return;
    
    console.log("Обновление кнопки →", state);
    
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
        
      case this.SHIFT_STATES.TO_PICKUP:
      case 'to_pickup':
        buttonText.textContent = 'К ресторану';
        button.style.backgroundColor = "#007cbf";
        button.disabled = false;
        break;
        
      case this.SHIFT_STATES.TO_DROPOFF:
      case 'to_dropoff':
        buttonText.textContent = 'К клиенту';
        button.style.backgroundColor = "#9b59b6";
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