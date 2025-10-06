// Модуль выбора картографического сервиса
class MapServiceSelector {
  constructor() {
    this.storageKey = 'selectedMapService';
    this.defaultService = '2gis';
    this.init();
  }

  init() {
    console.log("🗺️ MapServiceSelector инициализирован");
    
    const savedService = this.getSelectedService();
    
    const radio = document.getElementById(`service-${savedService}`);
    if (radio) {
      radio.checked = true;
      radio.parentElement.classList.add('selected');
    }
    
    this.updateServiceNameDisplay(savedService);
    this.attachRadioListeners();
  }

  attachRadioListeners() {
    const options = document.querySelectorAll('.service-option');
    
    options.forEach(option => {
      option.addEventListener('click', () => {
        const radio = option.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          
          options.forEach(opt => opt.classList.remove('selected'));
          option.classList.add('selected');
        }
      });
    });
  }

  openModal() {
    const modal = document.getElementById('mapServiceModal');
    if (modal) {
      modal.style.display = 'flex';
      console.log("🗺️ Открыто окно выбора сервиса");
    }
  }

  closeModal() {
    const modal = document.getElementById('mapServiceModal');
    if (modal) {
      modal.style.display = 'none';
      console.log("🗺️ Закрыто окно выбора сервиса");
    }
  }

  saveSelection() {
    const selected = document.querySelector('input[name="mapService"]:checked');
    
    if (selected) {
      const service = selected.value;
      localStorage.setItem(this.storageKey, service);
      console.log(`✅ Сохранен сервис: ${service}`);
      
      this.updateServiceNameDisplay(service);
      this.closeModal();
    }
  }

  updateServiceNameDisplay(service) {
    const nameElement = document.getElementById('selectedMapServiceName');
    if (!nameElement) return;
    
    const services = {
      '2gis': {
        name: '2GIS',
        icon: '/static/img/map_icons/2gis.png'
      },
      'yandex': {
        name: 'Яндекс Карты',
        icon: '/static/img/map_icons/yandex.png'
      },
      'organic': {
        name: 'Organic Maps',
        icon: '/static/img/map_icons/organic.png'
      }
    };
    
    const selected = services[service] || services['2gis'];
    
    nameElement.innerHTML = `<img src="${selected.icon}" alt="${selected.name}" class="cell_icon"><h3 class="black100">${selected.name}</h3>`;
  }

  getSelectedService() {
    return localStorage.getItem(this.storageKey) || this.defaultService;
  }

  /**
   * Получить URL для навигации в зависимости от выбранного сервиса
   * @param {number} lat - Широта
   * @param {number} lng - Долгота
   * @returns {string} URL для открытия карты
   */
  getNavigationUrl(lat, lng) {
    const service = this.getSelectedService();
    
    switch(service) {
      case '2gis':
        // 2GIS: используем построение маршрута "до точки"
        // Формат: /directions/points/%current_location%/lng,lat
        return `https://2gis.kz/almaty/directions/points/%7C${lng},${lat}`;
      
      case 'yandex':
        // Яндекс Карты: rtext (маршрут) - от текущей позиции до точки
        return `https://yandex.ru/maps/?rtext=~${lat},${lng}&rtt=auto`;
      
      case 'organic':
        // Organic Maps: geo: URI scheme
        return `geo:${lat},${lng}?z=18`;
      
      default:
        return `https://2gis.kz/almaty/directions/points/%7C${lng},${lat}`;
    }
  }
}

window.mapServiceSelector = null;

document.addEventListener('DOMContentLoaded', () => {
  window.mapServiceSelector = new MapServiceSelector();
});
