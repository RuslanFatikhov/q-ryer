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

  // Добавление маркера пользователя
  addUserMarker(coords) {
    if (!this.map) return;
    
    if (this.userMarker) {
      this.userMarker.remove();
    }
    
    this.userMarker = new mapboxgl.Marker({
      color: '#007cbf',
      scale: 0.8
    })
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

  // Показ заказа на карте
  showOrder(order) {
    if (!this.map) return;
    
    this.clearOrderMarkers();
    
    // Маркер ресторана
    const pickupMarker = new mapboxgl.Marker({
      color: '#00aa44',
      scale: 1.2
    })
    .setLngLat([order.pickup.lng, order.pickup.lat])
    .setPopup(new mapboxgl.Popup({ offset: 25 })
      .setHTML(`<h3>Забрать</h3><p>${order.pickup.name}</p>`))
    .addTo(this.map);
    
    // Маркер здания
    const dropoffMarker = new mapboxgl.Marker({
      color: '#ff4444',
      scale: 1.2
    })
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
