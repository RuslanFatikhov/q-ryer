/**
 * Управление картой и маркерами
 */
class MapManager {
  constructor() {
    this.map = null;
    this.userMarker = null;
    this.orderMarkers = [];
  }

  // Инициализация карты
  initialize() {
    this.map = new mapboxgl.Map({
      container: "map",
      style: "mapbox://styles/mapbox/streets-v11",
      center: [76.8897, 43.2389],
      zoom: 12,
      attributionControl: false
    });

    this.map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    
    this.map.on('load', () => {
      console.log("Карта загружена");
    });

    return this.map;
  }

  // Создание кастомного HTML элемента для маркера
  createCustomMarkerElement(iconPath, color, size = 40) {
    const el = document.createElement('div');
    el.style.width = `${size}px`;
    el.style.height = `${size}px`;
    el.style.backgroundImage = `url(${iconPath})`;
    el.style.backgroundSize = 'contain';
    el.style.backgroundRepeat = 'no-repeat';
    el.style.backgroundPosition = 'center';
    el.style.cursor = 'pointer';
    
    // Добавляем тень для лучшей видимости
    el.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))';
    
    return el;
  }

  // Добавление маркера пользователя с кастомной иконкой
  addUserMarker(coords) {
    if (!this.map) return;
    
    if (this.userMarker) {
      this.userMarker.remove();
    }
    
    // Создаем кастомный маркер игрока с изображением
    const el = document.createElement('div');
    const img = document.createElement('img');
    img.src = '/static/img/cursor/cursor.png';
    img.style.width = '40px';
    img.style.height = '40px';
    img.style.objectFit = 'contain';
    el.appendChild(img);














    
    this.userMarker = new mapboxgl.Marker({element: el})
      .setLngLat([coords.longitude, coords.latitude])
      .addTo(this.map);
  }

  // Обновление позиции пользователя
  updateUserMarker(coords) {
    if (this.userMarker) {
      this.userMarker.setLngLat([coords.longitude, coords.latitude]);
    }
  }

  // Центрирование на пользователе
  centerOnUser() {
    if (!window.geoManager?.currentPosition || !this.map) return;
    
    const pos = window.geoManager.getCurrentPosition();
    this.map.easeTo({
      center: [pos.lng, pos.lat],
      zoom: 16,
      duration: 1000
    });
  }

  // Показ заказа на карте с кастомными маркерами
  showOrder(order) {
    if (!this.map) return;
    
    this.clearOrderMarkers();
    
    // Кастомный маркер для ресторана (зеленая сумка)
    const pickupEl = this.createCustomMarkerElement('/static/img/icon/bag_white.svg', '#00aa44', 50);
    pickupEl.style.backgroundColor = '#00aa44';
    pickupEl.style.borderRadius = '50%';
    pickupEl.style.padding = '10px';
    
    const pickupMarker = new mapboxgl.Marker({element: pickupEl})
      .setLngLat([order.pickup.lng, order.pickup.lat])
      .setPopup(new mapboxgl.Popup({ offset: 25 })
        .setHTML(`<h3>Забрать</h3><p>${order.pickup.name}</p>`))
      .addTo(this.map);
    
    // Кастомный маркер для здания (красный дом)
    const dropoffEl = this.createCustomMarkerElement('/static/img/icon/home_white.svg', '#ff4444', 50);
    dropoffEl.style.backgroundColor = '#ff4444';
    dropoffEl.style.borderRadius = '50%';
    dropoffEl.style.padding = '10px';
    
    const dropoffMarker = new mapboxgl.Marker({element: dropoffEl})
      .setLngLat([order.dropoff.lng, order.dropoff.lat])
      .setPopup(new mapboxgl.Popup({ offset: 25 })
        .setHTML(`<h3>Доставить</h3><p>${order.dropoff.address}</p>`))
      .addTo(this.map);
    
    this.orderMarkers = [pickupMarker, dropoffMarker];
    
    // Центрируем карту на маршруте
    const bounds = new mapboxgl.LngLatBounds();
    bounds.extend([order.pickup.lng, order.pickup.lat]);
    bounds.extend([order.dropoff.lng, order.dropoff.lat]);
    
    const userPos = window.geoManager?.getCurrentPosition();
    if (userPos) {
      bounds.extend([userPos.lng, userPos.lat]);
    }
    
    this.map.fitBounds(bounds, { padding: 80 });
  }

  // Очистка маркеров заказов
  clearOrderMarkers() {
    this.orderMarkers.forEach(marker => marker.remove());
    this.orderMarkers = [];
  }

  // Установка центра и зума
  setView(coords, zoom = 16) {
    if (this.map) {
      this.map.setCenter([coords.longitude, coords.latitude]);
      this.map.setZoom(zoom);
    }
  }
}

window.MapManager = MapManager;
