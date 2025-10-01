/**
 * Управление картой и маркерами
 */
class MapManager {
  constructor() {
    this.map = null;
    this.userMarker = null;
    this.orderMarkers = [];
    this.zoneCircles = []; // Круги для визуализации зон
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
      
      // Добавляем источники для кругов зон
      this.map.addSource('pickup-zone', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: []
        }
      });
      
      this.map.addSource('dropoff-zone', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: []
        }
      });
      
      // Добавляем слои для отображения зон
      this.map.addLayer({
        id: 'pickup-zone-fill',
        type: 'fill',
        source: 'pickup-zone',
        paint: {
          'fill-color': '#00aa44',
          'fill-opacity': 0.15
        }
      });
      
      this.map.addLayer({
        id: 'pickup-zone-outline',
        type: 'line',
        source: 'pickup-zone',
        paint: {
          'line-color': '#00aa44',
          'line-width': 2,
          'line-dasharray': [2, 2]
        }
      });
      
      this.map.addLayer({
        id: 'dropoff-zone-fill',
        type: 'fill',
        source: 'dropoff-zone',
        paint: {
          'fill-color': '#ff4444',
          'fill-opacity': 0.15
        }
      });
      
      this.map.addLayer({
        id: 'dropoff-zone-outline',
        type: 'line',
        source: 'dropoff-zone',
        paint: {
          'line-color': '#ff4444',
          'line-width': 2,
          'line-dasharray': [2, 2]
        }
      });
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

  // Показ заказа на карте с зонами
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
    
    // Показываем зоны
    this.showZones(order);
    
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

  // Отображение зон pickup и dropoff
  showZones(order) {
    if (!this.map || !this.map.isStyleLoaded()) return;
    
    const radiusMeters = 30; // Радиус зоны в метрах
    const radiusDegrees = radiusMeters / 111000; // Примерное преобразование в градусы
    
    // Создаем круг для pickup зоны
    const pickupCircle = this.createCircle(
      [order.pickup.lng, order.pickup.lat],
      radiusDegrees,
      64
    );
    
    // Создаем круг для dropoff зоны
    const dropoffCircle = this.createCircle(
      [order.dropoff.lng, order.dropoff.lat],
      radiusDegrees,
      64
    );
    
    // Обновляем источники данных
    this.map.getSource('pickup-zone').setData({
      type: 'FeatureCollection',
      features: [pickupCircle]
    });
    
    this.map.getSource('dropoff-zone').setData({
      type: 'FeatureCollection',
      features: [dropoffCircle]
    });
  }

  // Создание геометрии круга
  createCircle(center, radiusDegrees, points) {
    const coordinates = [];
    
    for (let i = 0; i < points; i++) {
      const angle = (i / points) * 2 * Math.PI;
      const dx = radiusDegrees * Math.cos(angle);
      const dy = radiusDegrees * Math.sin(angle);
      
      coordinates.push([
        center[0] + dx / Math.cos(center[1] * Math.PI / 180),
        center[1] + dy
      ]);
    }
    
    // Замыкаем круг
    coordinates.push(coordinates[0]);
    
    return {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [coordinates]
      }
    };
  }

  // Очистка зон
  clearZones() {
    if (!this.map || !this.map.isStyleLoaded()) return;
    
    this.map.getSource('pickup-zone')?.setData({
      type: 'FeatureCollection',
      features: []
    });
    
    this.map.getSource('dropoff-zone')?.setData({
      type: 'FeatureCollection',
      features: []
    });
  }

  // Очистка маркеров заказов
  clearOrderMarkers() {
    this.orderMarkers.forEach(marker => marker.remove());
    this.orderMarkers = [];
    this.clearZones();
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
