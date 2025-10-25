/**
 * Debug утилиты для тестирования игры
 * ⚠️ Только для development!
 */

class DebugPanel {
  constructor() {
    this.panel = null;
    this.isVisible = false;
  }

  // Создание debug панели
  create() {
    this.panel = document.createElement('div');
    this.panel.id = 'debugPanel';
    this.panel.innerHTML = `
      <div>
        <h4 style="margin: 0 0 12px 0; color: #ff6600;">🛠️ DEBUG PANEL</h4>
        
        <div style="margin-bottom: 12px;">
          <strong>Состояние:</strong>
          <div>GPS: <span id="debugGPS">❌</span></div>
          <div>Смена: <span id="debugShift">❌</span></div>
          <div>Заказ: <span id="debugOrder">Нет</span></div>
        </div>
        
        <div style="margin-bottom: 12px;">
          <strong>Позиция:</strong>
          <div id="debugPosition">—</div>
        </div>
        
        <div style="margin-bottom: 12px;">
          <strong>Зоны:</strong>
          <div>Pickup: <span id="debugPickupZone">❌</span></div>
          <div>Dropoff: <span id="debugDropoffZone">❌</span></div>
        </div>
        
        <div style="display: flex; gap: 8px; flex-direction: column;">
          <button id="debugTeleportPickup" style="
            padding: 8px;
            background: #00aa44;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
          ">📍 Телепорт к ресторану</button>
          
          <button id="debugTeleportDropoff" style="
            padding: 8px;
            background: #9b59b6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
          ">🏠 Телепорт к клиенту</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.panel);
    this.attachEventListeners();
    this.startUpdating();
  }

  // Подключение обработчиков
  attachEventListeners() {
    // Телепорт к ресторану
    document.getElementById('debugTeleportPickup').addEventListener('click', async () => {
      await this.teleportToPickup();
    });
    
    // Телепорт к клиенту
    document.getElementById('debugTeleportDropoff').addEventListener('click', async () => {
      await this.teleportToDropoff();
    });
  }

  // Показать/скрыть панель
  toggle() {
    this.isVisible = !this.isVisible;
    const panel = this.panel.querySelector('div');
    panel.style.display = this.isVisible ? 'block' : 'none';
  }

  // Обновление информации
  startUpdating() {
    setInterval(() => {
      this.updateInfo();
    }, 1000);
  }

  updateInfo() {
    // GPS статус
    const gpsEl = document.getElementById('debugGPS');
    if (gpsEl) {
      gpsEl.textContent = window.geoManager?.currentPosition ? '✅' : '❌';
    }
    
    // Статус смены
    const shiftEl = document.getElementById('debugShift');
    if (shiftEl && window.gameState) {
      shiftEl.textContent = window.gameState.isOnShift ? '✅ Активна' : '❌ Не начата';
    }
    
    // Заказ
    const orderEl = document.getElementById('debugOrder');
    if (orderEl && window.gameState) {
      const order = window.gameState.currentOrder;
      if (order) {
        orderEl.textContent = `#${order.id} (${order.status})`;
      } else {
        orderEl.textContent = 'Нет';
      }
    }
    
    // Позиция
    const posEl = document.getElementById('debugPosition');
    if (posEl && window.geoManager?.currentPosition) {
      const pos = window.geoManager.getCurrentPosition();
      posEl.textContent = `${pos.lat.toFixed(6)}, ${pos.lng.toFixed(6)}`;
    }
  }

  // Телепорт к ресторану
  async teleportToPickup() {
    try {
      const response = await fetch('/api/debug/teleport_to_pickup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: window.gameState.userId})
      });
      
      const result = await response.json();
      
      if (result.success) {
        console.log('✅ Телепортация к ресторану:', result);
        
        const pos = result.position;
        
        // 1. Обновляем позицию в geoManager
        if (window.geoManager) {
          window.geoManager.currentPosition = {
            coords: {
              latitude: pos.lat,
              longitude: pos.lng,
              accuracy: 5
            },
            timestamp: Date.now()
          };
        }
        
        // 2. Обновляем маркер игрока на карте
        if (window.mapManager) {
          window.mapManager.updateUserMarker({
            latitude: pos.lat,
            longitude: pos.lng
          });
          
          // 3. Центрируем карту
          window.mapManager.setView({
            longitude: pos.lng,
            latitude: pos.lat
          }, 18);
        }
        
        // 4. Обновляем зоны в UI
        this.updateZones(result.zones);
        
        alertModal.success(`Телепортировано к ресторану\n\nВ зоне pickup: ${result.zones.in_pickup_zone ? 'ДА ✅' : 'НЕТ ❌'}`);
      } else {
        alert('❌ Ошибка: ' + result.error);
      }
    } catch (e) {
      alert('❌ Ошибка телепортации: ' + e.message);
    }
  }

  // Телепорт к клиенту
  async teleportToDropoff() {
    try {
      const response = await fetch('/api/debug/teleport_to_dropoff', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: window.gameState.userId})
      });
      
      const result = await response.json();
      
      if (result.success) {
        console.log('✅ Телепортация к клиенту:', result);
        
        const pos = result.position;
        
        // 1. Обновляем позицию в geoManager
        if (window.geoManager) {
          window.geoManager.currentPosition = {
            coords: {
              latitude: pos.lat,
              longitude: pos.lng,
              accuracy: 5
            },
            timestamp: Date.now()
          };
        }
        
        // 2. Обновляем маркер игрока на карте
        if (window.mapManager) {
          window.mapManager.updateUserMarker({
            latitude: pos.lat,
            longitude: pos.lng
          });
          
          // 3. Центрируем карту
          window.mapManager.setView({
            longitude: pos.lng,
            latitude: pos.lat
          }, 18);
        }
        
        // 4. Обновляем зоны в UI
        this.updateZones(result.zones);
        
        alert(`✅ Телепортировано к клиенту\n\nВ зоне dropoff: ${result.zones.in_dropoff_zone ? 'ДА ✅' : 'НЕТ ❌'}`);
      } else {
        alert('❌ Ошибка: ' + result.error);
      }
    } catch (e) {
      alert('❌ Ошибка телепортации: ' + e.message);
    }
  }

  // Обновление информации о зонах
  updateZones(zones) {
    const pickupEl = document.getElementById('debugPickupZone');
    const dropoffEl = document.getElementById('debugDropoffZone');
    
    if (pickupEl) {
      pickupEl.textContent = zones.in_pickup_zone ? '✅ ДА' : '❌ НЕТ';
    }
    
    if (dropoffEl) {
      dropoffEl.textContent = zones.in_dropoff_zone ? '✅ ДА' : '❌ НЕТ';
    }
  }
}

// Создаем глобальный экземпляр
window.debugPanel = new DebugPanel();

// Автоматически создаем панель при загрузке в development режиме
if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  document.addEventListener('DOMContentLoaded', () => {
    window.debugPanel.create();
  });
  
  // Хоткей для показа/скрытия панели: Ctrl+Shift+D
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
      window.debugPanel.toggle();
    }
  });
  
  console.log('🛠️ Debug панель доступна. Нажмите Ctrl+Shift+D для открытия');
}

/**
 * Установить фейковую GPS позицию в центр выбранного города
 */

/**
 * Установить фейковую GPS позицию в центр выбранного города
 */
async function setFakeLocationToCity() {
    const cityId = localStorage.getItem('selectedCity') || 'almaty';
    console.log('🔍 Устанавливаем GPS для города:', cityId);
    
    try {
        // Получаем координаты города
        const response = await fetch(`/api/cities/${cityId}`);
        const data = await response.json();
        console.log('📍 Данные города:', data);
        
        if (data.success) {
            const city = data.city;
            const fakeLat = city.center.lat;
            const fakeLng = city.center.lng;
            
            console.log('📍 Координаты:', { lat: fakeLat, lng: fakeLng });
            
            // Устанавливаем фейковую позицию
            if (window.geoManager) {
                window.geoManager.currentPosition = {
                    coords: {
                        latitude: fakeLat,
                        longitude: fakeLng,
                        accuracy: 10
                    },
                    timestamp: Date.now()
                };
                
                console.log('✅ geoManager обновлен:', window.geoManager.currentPosition);
                
                // Обновляем маркер на карте через updateUserMarker
                if (window.mapManager) {
                    console.log('📍 Обновляем маркер игрока');
                    window.mapManager.updateUserMarker({
                        latitude: fakeLat,
                        longitude: fakeLng
                    });
                    window.mapManager.map.flyTo({ center: [fakeLng, fakeLat], zoom: 14 });
                }
                
                console.log(`✅ Фейковая GPS установлена на ${city.name}: [${fakeLat}, ${fakeLng}]`);
                alert(`GPS установлен на ${city.name}`);
            } else {
                console.error('❌ geoManager не найден');
            }
        }
    } catch (error) {
        console.error('❌ Ошибка установки фейковой GPS:', error);
    }
}

// Делаем функцию глобально доступной
window.setFakeLocationToCity = setFakeLocationToCity;

console.log('🛠️ Debug: Используйте setFakeLocationToCity() для установки GPS в центр выбранного города');
