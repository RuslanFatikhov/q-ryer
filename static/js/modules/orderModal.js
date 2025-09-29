/**
 * Управление модальными окнами заказов
 */
class OrderModal {
  constructor(gameState, shiftManager) {
    this.gameState = gameState;
    this.shiftManager = shiftManager;
    this.modal = null;
  }

  // Показ модалки с заказом
  show(order) {
    console.log("Показываем модалку заказа:", order);
    
    // Используем существующую модалку из HTML
    this.modal = document.getElementById("orderModal");
    
    if (!this.modal) {
      console.error("Модалка orderModal не найдена в HTML");
      return;
    }
    
    this.updateContent(order);
    this.addEventListeners();
    this.modal.style.display = "flex";
  }

  // Добавление обработчиков к существующей модалке
  addEventListeners() {
    if (!this.modal) return;
    
    const closeBtn = this.modal.querySelector(".close");
    const declineBtn = this.modal.querySelector(".decline-btn");
    const acceptBtn = this.modal.querySelector(".accept-btn");
    
    if (closeBtn) closeBtn.onclick = () => this.close();
    if (declineBtn) declineBtn.onclick = () => this.close();
    if (acceptBtn) acceptBtn.onclick = () => this.acceptOrder();
  }

  // Обновление содержимого модалки
  updateContent(order) {
    const pickupName = order.pickup?.name || order.pickup_name || 'Неизвестный ресторан';
    const dropoffAddress = order.dropoff?.address || order.dropoff_address || 'Неизвестный адрес';
    
    const elements = {
      orderPickupName: pickupName,
      orderDropoffAddress: dropoffAddress,
      orderDistance: `${order.distance_km} км`,
      orderTime: `~${Math.ceil(order.timer_seconds / 60)} мин`,
      orderPayout: `$${order.amount}`
    };
    
    Object.entries(elements).forEach(([id, text]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = text;
    });
  }

  // Закрытие модалки
  close() {
    if (this.modal) {
      this.modal.style.display = "none";
    }
    
    // Очищаем текущий заказ при отклонении
    this.gameState.setCurrentOrder(null);
    
    if (window.mapManager) {
      window.mapManager.clearOrderMarkers();
    }
    
    // Запускаем поиск заново если смена активна
    if (this.gameState.isOnShift) {
      this.shiftManager.startSearching();
    }
  }

  // Принятие заказа
  async acceptOrder() {
    if (!this.gameState.currentOrder) {
      console.error("Нет текущего заказа");
      return;
    }
    
    try {
      console.log("Принимаем заказ:", this.gameState.currentOrder.id);
      
      const response = await fetch('/api/order/accept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.gameState.userId,
          order_id: this.gameState.currentOrder.id
        })
      });
      
      if (!response.ok) {
        throw new Error('Не удалось принять заказ');
      }
      
      console.log("Заказ принят успешно");
      this.close();
      
      const button = document.getElementById("startGame");
      const buttonText = button?.querySelector("h3");
      if (buttonText) {
        buttonText.textContent = "К ресторану";
        button.style.backgroundColor = "#007cbf";
      }
      
    } catch (error) {
      console.error("Ошибка принятия заказа:", error);
      alert("Ошибка: " + error.message);
    }
  }
}

window.OrderModal = OrderModal;
