/**
 * Модуль управления баннером статуса заказа
 * Показывает "Заберите заказ" или "Довезите заказ" в зависимости от этапа доставки
 */
class OrderStatusBanner {
  constructor() {
    this.block = null;
    this.iconImg = null;
    this.titleElement = null;
    this.textElement = null;
  }

  /**
   * Инициализация - находим элементы DOM
   */
  initialize() {
    this.block = document.getElementById('orderStatusBlock');
    
    if (!this.block) {
      console.error('❌ orderStatusBlock не найден в DOM');
      return false;
    }

    // Находим элементы для изменения
    this.iconImg = this.block.querySelector('.order-status-icon img');
    this.titleElement = this.block.querySelector('.order-status-header h2');
    this.textElement = this.block.querySelector('.order-status-text');

    console.log('✅ OrderStatusBanner инициализирован');
    return true;
  }

  /**
   * Обновление баннера в зависимости от состояния заказа
   * @param {Object} order - Объект заказа из gameState
   */
  update(order) {
    if (!this.block) return;

    // Если нет заказа - скрываем баннер
    if (!order) {
      this.hide();
      return;
    }

    // Проверяем, забран ли заказ
    if (!order.pickup_time) {
      // Заказ НЕ забран - показываем "Заберите заказ"
      this.showPickupBanner();
    } else {
      // Заказ забран - показываем "Довезите заказ"
      this.showDeliveryBanner();
    }
  }

  /**
   * Показать баннер "Заберите заказ"
   */
  showPickupBanner() {
    if (!this.block) return;

    // Обновляем иконку (сумка)
    if (this.iconImg) {
      this.iconImg.src = '/static/img/icon/bag_white.svg';
      this.iconImg.alt = 'Bag';
    }

    // Обновляем заголовок
    if (this.titleElement) {
      this.titleElement.textContent = 'Заберите заказ';
    }

    // Обновляем текст
    if (this.textElement) {
      this.textElement.textContent = 'Направляйтесь в зону получения';
    }

    // Показываем блок
    this.show();
    
    console.log('📦 Баннер: Заберите заказ');
  }

  /**
   * Показать баннер "Довезите заказ"
   */
  showDeliveryBanner() {
    if (!this.block) return;

    // Обновляем иконку (дом или доставка)
    if (this.iconImg) {
      // Можно использовать другую иконку для доставки
      this.iconImg.src = '/static/img/icon/bag_white.svg';
      this.iconImg.alt = 'Delivery';
    }

    // Обновляем заголовок
    if (this.titleElement) {
      this.titleElement.textContent = 'Довезите заказ';
    }

    // Обновляем текст
    if (this.textElement) {
      this.textElement.textContent = 'Направляйтесь к клиенту';
    }

    // Показываем блок
    this.show();
    
    console.log('🚗 Баннер: Довезите заказ');
  }

  /**
   * Показать баннер
   */
  show() {
    if (this.block) {
      this.block.style.display = 'block';
    }
  }

  /**
   * Скрыть баннер
   */
  hide() {
    if (this.block) {
      this.block.style.display = 'none';
    }
    console.log('🔒 Баннер скрыт');
  }
}

// Экспортируем класс
window.OrderStatusBanner = OrderStatusBanner;
