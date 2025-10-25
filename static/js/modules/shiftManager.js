/**
 * Управление сменами и поиском заказов
 */
class ShiftManager {
  constructor(gameState, socketManager) {
    this.gameState = gameState;
    this.socketManager = socketManager;
    this.lastButtonState = null;
    this.zoneCheckInterval = null;

    this.SHIFT_STATES = {
      REQUESTING_GPS: 'requesting_gps',
      START_SHIFT: 'start_shift',
      END_SHIFT: 'end_shift',
      SEARCHING: 'searching',
      TO_PICKUP: 'to_pickup',
      AT_PICKUP: 'at_pickup',
      TO_DROPOFF: 'to_dropoff',
      AT_DROPOFF: 'at_dropoff'
    };
  }

  async handleShiftButtonClick() {
    console.log("Клик по кнопке смены");

    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3")?.textContent;

    console.log("Текст кнопки:", buttonText);

    try {
      if (!window.geoManager?.hasStoredPermission() || !window.geoManager?.currentPosition) {
        console.log("Запрашиваем GPS…");
        this.updateShiftButton('REQUESTING_GPS_ACTIVE');
        try {
          await window.geoManager.requestPermission(true);
          this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
        } catch (error) {
          console.error("GPS запрос отклонен:", error);
          this.updateShiftButton(this.SHIFT_STATES.REQUESTING_GPS);
        }
        return;
      }

      if (!this.gameState.isOnShift) {
        console.log("→ Начинаем смену");
        await this.startShift();
        return;
      }

      if (this.gameState.isSearching) {
        console.log("→ Останавливаем поиск");
        await this.stopSearching();
        return;
      }

      if (this.gameState.currentOrder) {
        if (buttonText === "Забрать заказ") {
          console.log("→ Забираем заказ");
          await this.pickupOrder();
          return;
        }
        if (buttonText === "Доставить заказ") {
          console.log("→ Доставляем заказ");
          await this.deliverOrder();
          return;
        }
        console.log("→ Открываем навигацию к заказу");
        this.openNavigation();
        return;
      }

      console.log("→ Завершаем смену");
      await this.endShift();

    } catch (error) {
      console.error("Ошибка при обработке клика:", error);
      
      if (!window.geoManager?.hasStoredPermission() || !window.geoManager?.currentPosition) {
        this.updateShiftButton(this.SHIFT_STATES.REQUESTING_GPS);
      } else if (!this.gameState.isOnShift) {
        this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
      }
    }
  }

  async startShift() {
    console.log("Начинаем смену");

    if (!window.geoManager?.currentPosition) {
      throw new Error("GPS недоступен");
    }

    try {
      const response = await fetch('/api/start_shift', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: this.gameState.userId })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Не удалось начать смену');
      }

      this.gameState.setShiftStatus(true);
      console.log("✅ Смена начата");

      window.geoManager.startTracking((position) => {
        this.sendPositionUpdate(position);
      });

      this.ensureSocketLogin();
      this.startZoneChecking();

      setTimeout(() => this.startSearching(), 500);

    } catch (error) {
      throw new Error('Ошибка сервера: ' + error.message);
    }
  }

  async startSearching() {
    console.log("Начинаем поиск заказов");
    
    this.ensureSocketLogin();
    
    this.gameState.setSearchingStatus(true);
    this.updateShiftButton(this.SHIFT_STATES.SEARCHING);
    
    setTimeout(() => {
      this.socketManager.startOrderSearch?.(5);
    }, 100);
  }

  async stopSearching() {
    console.log("Останавливаем поиск заказов");
    this.gameState.setSearchingStatus(false);
    this.updateShiftButton(this.SHIFT_STATES.END_SHIFT);
    this.socketManager.stopOrderSearch?.();
  }

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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: this.gameState.userId })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Не удалось закончить смену');
      }

      this.gameState.setShiftStatus(false);
      this.gameState.setSearchingStatus(false);
      this.gameState.setCurrentOrder(null);

      window.geoManager?.stopTracking();
      this.stopZoneChecking();

      if (window.mapManager) {
        window.mapManager.clearOrderMarkers();
      }

      this.updateShiftButton(this.SHIFT_STATES.START_SHIFT);
      console.log("✅ Смена завершена");

    } catch (error) {
      throw new Error('Ошибка завершения смены: ' + error.message);
    }
  }

  async pickupOrder() {
    console.log("Выполняем pickup заказа");
    try {
      const response = await fetch('/api/order/pickup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: this.gameState.userId })
      });

      const result = await response.json();

      if (result.success) {
        console.log("✅ Заказ забран:", result);

        const updatedOrder = result.order || {};
        updatedOrder.pickup_time = updatedOrder.pickup_time || Date.now();
        this.gameState.setCurrentOrder(updatedOrder);

        this.updateShiftButton(this.SHIFT_STATES.TO_DROPOFF);

        alertModal.success("Заказ забран! Теперь доставьте его клиенту.");
      } else {
        alertModal.error((result.error || 'Неизвестная ошибка'));
      }
    } catch (error) {
      console.error("Ошибка pickup:", error);
      alertModal.error("Ошибка забора заказа: " + error.message);
    }
  }

  async deliverOrder() {
  console.log("Выполняем delivery заказа");

  try {
    const response = await fetch('/api/order/deliver', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: this.gameState.userId })
    });

    const result = await response.json();

    if (result.success) {
      console.log("✅ Заказ доставлен:", result);

      const payoutValue =
        typeof result.payout === 'number'
          ? result.payout
          : (result.payout?.total ?? result.payout ?? 0);

      const bonusText =
        result.payout && typeof result.payout === 'object' && result.payout.bonus
          ? ` (+$${Number(result.payout.bonus).toFixed(2)} бонус)`
          : '';

      this.gameState.setCurrentOrder(null);
      
      // Скрываем баннер статуса заказа
      if (window.orderStatusBanner) {
        window.orderStatusBanner.hide();
      }
      
      this.stopZoneChecking();

      if (window.mapManager) {
        window.mapManager.clearOrderMarkers();
      }

      alertModal.showBalance(
        payoutValue,
        result.new_balance,
        bonusText
      );

      const balanceEl = document.getElementById('balanceAmount');
      if (balanceEl && typeof result.new_balance === 'number') {
        balanceEl.textContent = result.new_balance.toFixed(2);
      }

      setTimeout(() => this.startSearching(), 1000);

    } else {
      alertModal.error((result.error || 'Неизвестная ошибка'));
    }
  } catch (error) {
    console.error("Ошибка delivery:", error);
    alertModal.error("Ошибка доставки заказа: " + error.message);
  }
  }

  startZoneChecking() {
    this.stopZoneChecking();
    this.zoneCheckInterval = setInterval(() => this.checkZones(), 2000);
    console.log("✅ Проверка зон запущена");
  }

  stopZoneChecking() {
    if (this.zoneCheckInterval) {
      clearInterval(this.zoneCheckInterval);
      this.zoneCheckInterval = null;
      console.log("🛑 Проверка зон остановлена");
    }
  }

  async checkZones() {
    if (!this.gameState.currentOrder || !window.geoManager?.currentPosition) return;

    const pos = window.geoManager.getCurrentPosition();
    try {
      const response = await fetch('/api/position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: this.gameState.userId,
          lat: pos.lat,
          lng: pos.lng,
          accuracy: pos.accuracy
        })
      });

      if (!response.ok) return;

      const result = await response.json();
      const zones = result.zones || {};
      const order = this.gameState.currentOrder;

      if (!order.pickup_time) {
        if (zones.in_pickup_zone && zones.can_pickup) {
          this.updateShiftButton(this.SHIFT_STATES.AT_PICKUP);
        } else {
          this.updateShiftButton(this.SHIFT_STATES.TO_PICKUP);
        }
      } else {
        if (zones.in_dropoff_zone && zones.can_deliver) {
          this.updateShiftButton(this.SHIFT_STATES.AT_DROPOFF);
        } else {
          this.updateShiftButton(this.SHIFT_STATES.TO_DROPOFF);
        }
      }
    } catch (error) {
      console.error("Ошибка проверки зон:", error);
    }
  }

  openNavigation() {
    const order = this.gameState.currentOrder;
    if (!order) {
      console.error("Нет активного заказа для навигации");
      return;
    }

    let target, targetName;
    if (!order.pickup_time) {
      target = order.pickup;
      targetName = order.pickup?.name || 'Ресторан';
    } else {
      target = order.dropoff;
      targetName = order.dropoff?.address || 'Клиент';
    }

    if (!target?.lat || !target?.lng) {
      console.error("У точки нет координат");
      return;
    }

    const lat = target.lat;
    const lng = target.lng;
    
    console.log("Открываем навигацию к:", targetName);
    
    const url = window.mapServiceSelector 
      ? window.mapServiceSelector.getNavigationUrl(lat, lng)
      : `https://2gis.kz/almaty?m=${lng},${lat}`;
    
    console.log("URL навигации:", url);
    
    window.open(url, '_blank');
  }

  ensureSocketLogin() {
    if (this.socketManager && this.gameState.userId) {
      console.log("🔄 Обеспечиваем логин пользователя в socket");
      this.socketManager.loginUser(this.gameState.userId);
    }
  }

  updateShiftButton(state) {
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    if (!button || !buttonText) return;

    if (this.lastButtonState !== state) {
      console.log("Обновление кнопки →", state);
      this.lastButtonState = state;
    }

    // Обновляем видимость кнопки Report
    this.updateReportButton(state);

    switch (state) {
      case this.SHIFT_STATES.REQUESTING_GPS:
        buttonText.textContent = "Разрешить GPS";
        button.style.backgroundColor = "#ff6600";
        button.disabled = false;
        break;

      case 'REQUESTING_GPS_ACTIVE':
        buttonText.textContent = "Запрашиваем GPS...";
        button.style.backgroundColor = "#ff8800";
        button.disabled = true;
        break;

      case this.SHIFT_STATES.START_SHIFT:
        buttonText.textContent = "Получить заказ";
        button.style.backgroundColor = "#121212";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.END_SHIFT:
        buttonText.textContent = "Завершить смену";
        button.style.backgroundColor = "#ff4444";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.SEARCHING:
        buttonText.textContent = "Ищем заказы...";
        button.className = "action_button gr8";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.TO_PICKUP:
        buttonText.textContent = "К ресторану";
        button.className = "action_button gr7";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.AT_PICKUP:
        buttonText.textContent = "Забрать заказ";
        button.className = "action_button gr8";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.TO_DROPOFF:
        buttonText.textContent = "К клиенту";
        button.className = "action_button gr9";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.AT_DROPOFF:
        buttonText.textContent = "Доставить заказ";
        button.className = "action_button gr8";
        button.disabled = false;
        break;

      case 'UNSUPPORTED':
        buttonText.textContent = "GPS недоступен";
        button.className = "action_button gr1";
        button.disabled = true;
        break;
    }
  }

  updateReportButton(state) {
    const reportButton = document.getElementById('reportButton');
    if (!reportButton) return;

    // Показываем кнопку Report когда пользователь ЕДЕТ (не в зоне)
    // TO_PICKUP - едет к ресторану, TO_DROPOFF - едет к клиенту
    const showReport = state === this.SHIFT_STATES.TO_PICKUP || state === this.SHIFT_STATES.TO_DROPOFF;
    reportButton.style.display = showReport ? 'block' : 'none';
    
    console.log(`Report button: ${showReport ? 'показана' : 'скрыта'} (state: ${state})`);
  }

  sendPositionUpdate(position) {
    this.socketManager.sendPositionUpdate?.(position);
  }

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
