/**
 * Индикатор нахождения в зоне pickup/dropoff
 */
class ZoneIndicator {
  constructor() {
    this.indicator = null;
    this.isInPickupZone = false;
    this.isInDropoffZone = false;
  }

  // Создание индикатора
  create() {
    this.indicator = document.createElement('div');
    this.indicator.id = 'zoneIndicator';
    this.indicator.style.cssText = `
      position: fixed;
      top: 70px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0,0,0,0.8);
      color: white;
      padding: 12px 20px;
      border-radius: 20px;
      z-index: 1000;
      font-family: Inter, sans-serif;
      font-size: 14px;
      font-weight: 600;
      display: none;
      align-items: center;
      gap: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    document.body.appendChild(this.indicator);
  }

  // Обновление статуса
  update(zones) {
    if (!zones || !zones.has_active_order) {
      this.hide();
      return;
    }

    const order = window.gameState?.currentOrder;
    if (!order) {
      this.hide();
      return;
    }

    // Определяем текущий этап доставки
    if (!order.pickup_time) {
      // Едем к ресторану
      if (zones.in_pickup_zone && zones.can_pickup) {
        this.show('🎯 В зоне забора! Нажмите кнопку внизу', '#00aa44');
        this.isInPickupZone = true;
      } else {
        const distance = Math.round(zones.distance_to_pickup_meters || 0);
        this.show(`📍 До ресторана: ${distance} м`, '#ff6600');
        this.isInPickupZone = false;
      }
    } else {
      // Едем к клиенту
      if (zones.in_dropoff_zone && zones.can_deliver) {
        this.show('🏠 В зоне доставки! Нажмите кнопку внизу', '#ff4444');
        this.isInDropoffZone = true;
      } else {
        const distance = Math.round(zones.distance_to_dropoff_meters || 0);
        this.show(`📍 До клиента: ${distance} м`, '#9b59b6');
        this.isInDropoffZone = false;
      }
    }
  }

  // Показать индикатор
  show(text, color) {
    if (!this.indicator) return;
    
    this.indicator.textContent = text;
    this.indicator.style.background = color;
    this.indicator.style.display = 'flex';
  }

  // Скрыть индикатор
  hide() {
    if (!this.indicator) return;
    this.indicator.style.display = 'none';
    this.isInPickupZone = false;
    this.isInDropoffZone = false;
  }
}

window.ZoneIndicator = ZoneIndicator;
