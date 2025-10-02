/**
 * Управление WebSocket соединением и событиями
 */
class SocketManager {
  constructor(gameState, orderModal, mapManager) {
    this.gameState = gameState;
    this.orderModal = orderModal;
    this.mapManager = mapManager;
    this.socket = window.__socket;
  }

  // Инициализация обработчиков событий
  initialize() {
    if (!this.socket) {
      console.warn("Socket.IO не подключен");
      return;
    }

    // Отладка всех событий
    this.socket.onAny((eventName, ...args) => {
      console.log(`SocketIO Event: ${eventName}`, args);
    });

    // Регистрируем обработчики
    this.socket.on("search_started", (data) => this.onSearchStarted(data));
    this.socket.on("search_progress", (data) => this.onSearchProgress(data));
    this.socket.on("order_found", (data) => this.onOrderFound(data));
    this.socket.on("no_orders_found", (data) => this.onNoOrdersFound(data));
  }

  // Вход пользователя в систему
  loginUser(userId) {
    if (this.socket) {
      this.socket.emit('user_login', { user_id: userId });
    }
  }

  // Начало поиска заказов
  startOrderSearch(radiusKm) {
    if (this.socket) {
      this.socket.emit('start_order_search', { radius_km: radiusKm });
    }
  }

  // Остановка поиска заказов
  stopOrderSearch() {
    if (this.socket) {
      this.socket.emit('stop_order_search');
    }
  }

  // Отправка обновления позиции
  sendPositionUpdate(position) {
    if (!this.socket) return;
    
    const coords = position.coords;
    this.socket.emit('update_position', {
      lat: coords.latitude,
      lng: coords.longitude,
      accuracy: coords.accuracy,
      timestamp: position.timestamp
    });
  }

  // Обработчики событий
  onSearchStarted(data) {
    console.log("Поиск заказов начался");
    
    // Игнорируем если уже есть активный заказ
    if (this.gameState.currentOrder) {
      console.log("Игнорируем search_started - уже есть активный заказ");
      return;
    }
    
    if (window.shiftManager) {
      window.shiftManager.updateShiftButton('searching');
    }
  }

  onSearchProgress(data) {
    console.log(`Прогресс поиска: ${data.elapsed}/${data.total}`);
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    if (buttonText) {
      buttonText.textContent = `Поиск... ${data.elapsed}/${data.total}с`;
    }
  }

  onOrderFound(data) {
    console.log("Заказ найден:", data);
    
    if (!data || !data.order) {
      console.error("Некорректные данные заказа:", data);
      return;
    }

    // Сохраняем заказ в состоянии
    this.gameState.setCurrentOrder(data.order);
    this.gameState.setSearchingStatus(false);
    
    // Показываем на карте
    if (this.mapManager) {
      this.mapManager.showOrder(data.order);
    }
    
    // Показываем модалку
    if (this.orderModal) {
      this.orderModal.show(data.order);
    }
  }

  onNoOrdersFound(data) {
    console.log("Заказы не найдены:", data.message);
    this.gameState.setSearchingStatus(false);
    
    if (window.shiftManager) {
      window.shiftManager.updateShiftButton('end_shift');
    }
  }
}

window.SocketManager = SocketManager;
