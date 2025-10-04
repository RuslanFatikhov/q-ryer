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
  async close(orderAccepted = false) {
    console.log("Закрываем модалку заказа, принят:", orderAccepted);
    
    if (this.modal) {
      this.modal.style.display = "none";
    }
    
    // Если заказ НЕ был принят - отменяем на бэкенде
    if (!orderAccepted) {
      console.log("Заказ отклонён, отменяем на бэкенде");
      
      // Отменяем заказ через API
      if (this.gameState.currentOrder) {
        try {
          await fetch('/api/order/cancel', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              user_id: this.gameState.userId,
              reason: 'user_declined'
            })
          });
          console.log("Заказ отменён на бэкенде");
        } catch (error) {
          console.error("Ошибка отмены заказа:", error);
        }
      }
      
      // Очищаем состояние
      this.gameState.setCurrentOrder(null);
      
      if (window.mapManager) {
        window.mapManager.clearOrderMarkers();
      }
      
      // Запускаем поиск заново если смена активна
      if (this.gameState.isOnShift) {
        this.shiftManager.startSearching();
      }
    } else {
      console.log("Заказ принят, маркеры остаются");
    }
  }

  // Принятие заказа
  async acceptOrder() {
    if (!this.gameState.currentOrder) {
      console.error("Нет текущего заказа");
      return;
    }
    
    try {
      const orderId = this.gameState.currentOrder.id;
      const userId = this.gameState.userId;
      
      console.log("Принимаем заказ:", {
        order_id: orderId,
        user_id: userId
      });
      
      const response = await fetch('/api/order/accept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          order_id: orderId
        })
      });
      
      // Читаем ответ как JSON
      const result = await response.json();
      
      if (!response.ok) {
        console.error("Ошибка от сервера:", result);
        throw new Error(result.error || 'Не удалось принять заказ');
      }
      
      console.log("Заказ принят успешно:", result);
    console.log("Заказ принят успешно:", result);
    
    // КРИТИЧНО: Сохраняем заказ в gameState
    if (result.order) {
      result.order.status = 'active';
      this.gameState.setCurrentOrder(result.order);
      console.log("✅ Заказ сохранён в gameState:", result.order.id);
    }
    
    // Показываем маркеры
    if (window.mapManager && result.order) {
      window.mapManager.showOrder(result.order);
    }
    
    // Запускаем проверку зон для нового заказа
    if (window.shiftManager) {
      window.shiftManager.startZoneChecking();
    }
    

        // Показываем блок статуса заказа после принятия
        const orderStatusBlock = document.getElementById("orderStatusBlock");
        if (orderStatusBlock) {
          // Небольшая задержка для плавности после закрытия модалки
          setTimeout(() => {
            orderStatusBlock.style.display = "block";
          }, 300);
        }
    // Обновляем кнопку
    const button = document.getElementById("startGame");
    const buttonText = button?.querySelector("h3");
    if (buttonText) {
      buttonText.textContent = "К ресторану";
      button.style.backgroundColor = "#007cbf";
    }
    
    // Закрываем модалку
    this.close(true);

    } catch (error) {
      console.error("Ошибка принятия заказа:", error);
      alert("Ошибка: " + error.message);
    }
  }
}

window.OrderModal = OrderModal;
