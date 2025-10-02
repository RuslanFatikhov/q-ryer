/**
 * Управление сменами и поиском заказов
 */
class ShiftManager {
  constructor(gameState, socketManager) {
    this.gameState = gameState;
    this.socketManager = socketManager;
    this.lastButtonState = null;      // Последнее состояние кнопки (для логов)
    this.zoneCheckInterval = null;    // Интервал проверки зон

    this.SHIFT_STATES = {
      REQUESTING_GPS: 'requesting_gps',
      START_SHIFT: 'start_shift',
      END_SHIFT: 'end_shift',
      SEARCHING: 'searching',
      TO_PICKUP: 'to_pickup',
      AT_PICKUP: 'at_pickup',      // В зоне ресторана
      TO_DROPOFF: 'to_dropoff',
      AT_DROPOFF: 'at_dropoff'     // В зоне клиента
    };
  }

  // Обработчик клика по кнопке смены
  async handleShiftButtonClick() {
    console.log("Клик по кнопке смены");

    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3")?.textContent;

    console.log("Текст кнопки:", buttonText);

    try {
      // 1) Нет GPS — запрашиваем
      if (!window.geoManager?.currentPosition) {
        console.log("Запрашиваем GPS…");
        this.updateShiftButton('REQUESTING_GPS_ACTIVE');
        try {
          await window.geoManager.requestPermission();
        } catch (error) {
          console.error("GPS запрос отклонен:", error);
        }
        return;
      }

      // 2) Смена не начата — начинаем
      if (!this.gameState.isOnShift) {
        console.log("→ Начинаем смену");
        await this.startShift();
        return;
      }

      // 3) Идёт поиск — останавливаем поиск
      if (this.gameState.isSearching) {
        console.log("→ Останавливаем поиск");
        await this.stopSearching();
        return;
      }

      // 4) Есть активный заказ
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
        // Иначе — открыть навигацию
        console.log("→ Открываем навигацию к заказу");
        this.openNavigation();
        return;
      }

      // 5) Иначе — завершаем смену
      console.log("→ Завершаем смену");
      await this.endShift();

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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: this.gameState.userId })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Не удалось начать смену');
      }

      this.gameState.setShiftStatus(true);
      console.log("✅ Смена начата");

      // Геотрекинг
      window.geoManager.startTracking((position) => {
        this.sendPositionUpdate(position);
      });

      // Логин в сокет
      this.socketManager.loginUser?.(this.gameState.userId);

      // Запуск проверки зон
      this.startZoneChecking();

      // Чуть позже — старт поиска
      setTimeout(() => this.startSearching(), 500);

    } catch (error) {
      throw new Error('Ошибка сервера: ' + error.message);
    }
  }

  // Начало поиска заказов
  async startSearching() {
    console.log("Начинаем поиск заказов");
    this.gameState.setSearchingStatus(true);
    this.updateShiftButton(this.SHIFT_STATES.SEARCHING);
    this.socketManager.startOrderSearch?.(5);
  }

  // Остановка поиска заказов
  async stopSearching() {
    console.log("Останавливаем поиск заказов");
    this.gameState.setSearchingStatus(false);
    // Возвращаем текст к логичному состоянию — «Завершить смену»
    this.updateShiftButton(this.SHIFT_STATES.END_SHIFT);
    this.socketManager.stopOrderSearch?.();
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

  // Забор заказа в ресторане
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

        // Обновляем заказ в состоянии
        const updatedOrder = result.order || {};
        updatedOrder.pickup_time = updatedOrder.pickup_time || Date.now();
        this.gameState.setCurrentOrder(updatedOrder);

        // К клиенту
        this.updateShiftButton(this.SHIFT_STATES.TO_DROPOFF);

        alert("✅ Заказ забран! Теперь доставьте его клиенту.");
      } else {
        alert("❌ Ошибка: " + (result.error || 'Неизвестная ошибка'));
      }
    } catch (error) {
      console.error("Ошибка pickup:", error);
      alert("❌ Ошибка забора заказа: " + error.message);
    }
  }

  // Доставка заказа клиенту — ИСПРАВЛЕНО (один alert, нет лишних строк)
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

        // payout может приходить числом или объектом { total, bonus }
        const payoutValue =
          typeof result.payout === 'number'
            ? result.payout
            : (result.payout?.total ?? result.payout ?? 0);

        const bonusText =
          result.payout && typeof result.payout === 'object' && result.payout.bonus
            ? ` (+$${Number(result.payout.bonus).toFixed(2)} бонус)`
            : '';

        // Сброс текущего заказа
        this.gameState.setCurrentOrder(null);

        // Остановить проверку зон
        this.stopZoneChecking();

        // Очистить маркеры
        if (window.mapManager) {
          window.mapManager.clearOrderMarkers();
        }

        // ЕДИНСТВЕННОЕ сообщение
        alert(
          `✅ Заказ доставлен!\n\n` +
          `💰 Выплата: $${Number(payoutValue).toFixed(2)}${bonusText}\n` +
          `📦 Новый баланс: $${Number(result.new_balance).toFixed(2)}`
        );

        // Обновить баланс в UI
        const balanceEl = document.getElementById('balanceAmount');
        if (balanceEl && typeof result.new_balance === 'number') {
          balanceEl.textContent = result.new_balance.toFixed(2);
        }

        // Сразу возобновить поиск нового заказа
        setTimeout(() => this.startSearching(), 1000);

      } else {
        alert("❌ Ошибка: " + (result.error || 'Неизвестная ошибка'));
      }
    } catch (error) {
      console.error("Ошибка delivery:", error);
      alert("❌ Ошибка доставки заказа: " + error.message);
    }
  }

  // Запуск периодической проверки зон
  startZoneChecking() {
    this.stopZoneChecking();
    this.zoneCheckInterval = setInterval(() => this.checkZones(), 2000);
    console.log("✅ Проверка зон запущена");
  }

  // Остановка проверки зон
  stopZoneChecking() {
    if (this.zoneCheckInterval) {
      clearInterval(this.zoneCheckInterval);
      this.zoneCheckInterval = null;
      console.log("🛑 Проверка зон остановлена");
    }
  }

  // Проверка зон и обновление кнопки
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
        // Едем к ресторану
        if (zones.in_pickup_zone && zones.can_pickup) {
          this.updateShiftButton(this.SHIFT_STATES.AT_PICKUP);
        } else {
          this.updateShiftButton(this.SHIFT_STATES.TO_PICKUP);
        }
      } else {
        // Едем к клиенту
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

  // Открыть навигацию к текущей точке
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
    const url = `https://2gis.kz/almaty/directions/points/${lng},${lat}`;
    window.open(url, '_blank');
  }

  // Обновление кнопки смены
  updateShiftButton(state) {
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    if (!button || !buttonText) return;

    // Логируем только при изменении
    if (this.lastButtonState !== state) {
      console.log("Обновление кнопки →", state);
      this.lastButtonState = state;
    }

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
        buttonText.textContent = "Ищем заказы...";
        button.style.backgroundColor = "#00aa44";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.TO_PICKUP:
        buttonText.textContent = "К ресторану";
        button.style.backgroundColor = "#007cbf";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.AT_PICKUP:
        buttonText.textContent = "Забрать заказ";
        button.style.backgroundColor = "#00aa44";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.TO_DROPOFF:
        buttonText.textContent = "К клиенту";
        button.style.backgroundColor = "#9b59b6";
        button.disabled = false;
        break;

      case this.SHIFT_STATES.AT_DROPOFF:
        buttonText.textContent = "Доставить заказ";
        button.style.backgroundColor = "#ff4444";
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
    this.socketManager.sendPositionUpdate?.(position);
  }

  // Обработчики GPS
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
