with open('static/js/modules/orderModal.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим метод close и добавляем вызов API отмены
old_close = '''  // Закрытие модалки
  close(orderAccepted = false) {
    console.log("Закрываем модалку заказа, принят:", orderAccepted);
    
    if (this.modal) {
      this.modal.style.display = "none";
    }
    
    // Если заказ НЕ был принят - очищаем состояние
    if (!orderAccepted) {
      console.log("Заказ отклонён, очищаем состояние");
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
  }'''

new_close = '''  // Закрытие модалки
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
  }'''

content = content.replace(old_close, new_close)

with open('static/js/modules/orderModal.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ orderModal.js обновлен - теперь отклоненные заказы отменяются на бэкенде")
