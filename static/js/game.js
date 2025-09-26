// static/js/game.js

/**
 * Основной модуль курьерского симулятора
 * Управляет картой, состоянием игры и взаимодействием с пользователем
 */

// Глобальные переменные
let map = null;
let geoManager = null;
let gameState = {
  isOnShift: false,
  isSearching: false,
  currentOrder: null,
  userId: 1 // TODO: получать из авторизации
};

// Делаем переменные доступными глобально для отладки
window.gameState = gameState;
window.geoManager = null; // Будет установлена после инициализации

// Состояния кнопки смены
const SHIFT_STATES = {
  REQUESTING_GPS: 'requesting_gps',
  START_SHIFT: 'start_shift',
  END_SHIFT: 'end_shift', 
  SEARCHING: 'searching'
};

/**
 * Инициализация приложения после загрузки DOM
 */
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Инициализация курьерского симулятора");
  
  // Проверяем наличие Mapbox
  if (typeof mapboxgl === "undefined") {
    console.error("❌ Mapbox GL не загружен. Проверь подключение библиотеки.");
    showError("Ошибка загрузки карты");
    return;
  }

  // Проверяем наличие GeolocationManager
  if (typeof GeolocationManager === "undefined") {
    console.error("❌ GeolocationManager не загружен");
    showError("Ошибка модуля геолокации");
    return;
  }

  // Инициализируем компоненты
  initializeMap();
  initializeGeolocation();
  initializeUI();
  initializeSocketEvents();
  
  console.log("✅ Инициализация завершена");
});

/**
 * Инициализация карты Mapbox
 */
function initializeMap() {
  console.log("🗺️ Инициализация карты");
  
  map = new mapboxgl.Map({
    container: "map",
    style: "mapbox://styles/mapbox/streets-v11",
    center: [76.8897, 43.2389], // Алматы
    zoom: 12,
    attributionControl: false // Убираем attribution для чистоты
  });

  // Добавляем контролы
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');
  
  map.on('load', () => {
    console.log("✅ Карта загружена");
  });

  map.on('error', (e) => {
    console.error("❌ Ошибка карты:", e);
    showError("Ошибка загрузки карты");
  });
}

/**
 * Инициализация геолокации
 */
function initializeGeolocation() {
  console.log("📍 Инициализация геолокации");
  
  geoManager = new GeolocationManager();
  
  // Делаем доступным глобально для отладки
  window.geoManager = geoManager;
  
  // Проверяем поддержку
  if (!geoManager.isSupported()) {
    showError("Геолокация не поддерживается вашим браузером");
    updateShiftButton('UNSUPPORTED');
    return;
  }

  // Устанавливаем callbacks
  geoManager.onPermissionGranted = onGPSPermissionGranted;
  geoManager.onPermissionDenied = onGPSPermissionDenied;
  geoManager.onPositionUpdate = onPositionUpdate;

  // Показываем кнопку запроса GPS
  updateShiftButton(SHIFT_STATES.REQUESTING_GPS);
  console.log("✅ Геолокация готова к запросу разрешения");
}

/**
 * Инициализация UI элементов
 */
function initializeUI() {
  console.log("🖱️ Инициализация UI");
  
  // Обработчик кнопки смены
  const startGameButton = document.getElementById("startGame");
  if (startGameButton) {
    startGameButton.addEventListener("click", handleShiftButtonClick);
  }

  // Обработчики модалок
  initializeModals();
  
  // Кнопка центрирования на пользователе
  const myLocationButton = document.querySelector(".myloc");
  if (myLocationButton) {
    myLocationButton.addEventListener("click", centerOnUser);
  }
}

/**
 * Инициализация SocketIO событий
 */
function initializeSocketEvents() {
  console.log("🔌 Инициализация Socket.IO событий");
  
  if (!window.__socket) {
    console.warn("⚠️ Socket.IO не подключен");
    return;
  }

  // События поиска заказов
  window.__socket.on("search_started", onSearchStarted);
  window.__socket.on("search_progress", onSearchProgress);  
  window.__socket.on("order_found", onOrderFound);
  window.__socket.on("no_orders_found", onNoOrdersFound);
  window.__socket.on("search_error", onSearchError);
}

/**
 * Обработчик клика по кнопке смены
 */
async function handleShiftButtonClick() {
  console.log("🔄 Клик по кнопке смены, текущее состояние:", gameState.isOnShift);
  
  const button = document.getElementById("startGame");
  
  try {
    // Если нужно запросить GPS
    if (!geoManager.currentPosition) {
      console.log("📍 Запрашиваем доступ к GPS...");
      updateShiftButton('REQUESTING_GPS_ACTIVE');
      
      try {
        await geoManager.requestPermission();
        // onGPSPermissionGranted сработает автоматически
      } catch (error) {
        console.error("❌ GPS запрос отклонен:", error);
        // onGPSPermissionDenied сработает автоматически
      }
      return;
    }
    
    // Если GPS есть, обрабатываем состояния смены
    if (!gameState.isOnShift) {
      // Начинаем смену
      await startShift();
    } else if (gameState.isSearching) {
      // Останавливаем поиск
      await stopSearching();
    } else {
      // Заканчиваем смену
      await endShift();
    }
  } catch (error) {
    console.error("❌ Ошибка при обработке клика:", error);
    showError("Произошла ошибка: " + error.message);
    
    // Восстанавливаем корректное состояние кнопки
    if (!geoManager.currentPosition) {
      updateShiftButton(SHIFT_STATES.REQUESTING_GPS);
    } else if (!gameState.isOnShift) {
      updateShiftButton(SHIFT_STATES.START_SHIFT);
    }
  }
}

/**
 * Начало смены
 */
async function startShift() {
  console.log("▶️ Начинаем смену");
  
  // Проверяем что GPS доступен
  if (!geoManager.currentPosition) {
    throw new Error("GPS недоступен. Разрешите доступ к местоположению.");
  }

  // Отправляем запрос на сервер
  try {
    console.log("📡 Отправляем запрос на /api/start_shift для пользователя", gameState.userId);
    
    const response = await fetch('/api/start_shift', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: gameState.userId
      })
    });

    console.log("📡 Ответ сервера:", response.status, response.statusText);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
        console.error("❌ Ошибка API:", errorData);
      } catch (e) {
        console.error("❌ Не удалось парсить JSON ошибки:", e);
        errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
      }
      throw new Error(errorData.error || 'Не удалось начать смену');
    }

    const result = await response.json();
    console.log("✅ Смена началась:", result);

    // Обновляем состояние
    gameState.isOnShift = true;
    saveGameState();    
    // Начинаем отслеживание позиции
    geoManager.startTracking((position) => {
      sendPositionUpdate(position);
    });

    // Поиск заказов запустится после регистрации пользователя
    
    // Уведомляем SocketIO ПЕРЕД началом поиска
    if (window.__socket) {
      window.__socket.emit('user_login', { user_id: gameState.userId });
      
      // Ждем небольшую задержку чтобы пользователь зарегистрировался
      setTimeout(() => {
        startSearching();
      }, 500);
    } else {
      // Если нет SocketIO, все равно запускаем поиск
      startSearching();
    }

    showSuccess("Смена началась! Ищем заказы...");
    
  } catch (error) {
    console.error("❌ Полная ошибка startShift:", error);
    throw new Error('Ошибка сервера: ' + error.message);
  }
}

/**
 * Остановка поиска заказов
 */
async function stopSearching() {
  console.log("⏹️ Останавливаем поиск");
  
  gameState.isSearching = false;
    saveGameState();  updateShiftButton(SHIFT_STATES.END_SHIFT);
  
  // Уведомляем сервер
  if (window.__socket) {
    window.__socket.emit('stop_order_search');
  }
}

/**
 * Начало поиска заказов
 */
async function startSearching() {
  console.log("🔍 Начинаем поиск заказов");
  
  gameState.isSearching = true;
    saveGameState();  updateShiftButton(SHIFT_STATES.SEARCHING);
  
  // Уведомляем сервер
  if (window.__socket) {
    window.__socket.emit('start_order_search', { 
      radius_km: 5 
    });
  }
}

/**
 * Окончание смены
 */
async function endShift() {
  console.log("⏹️ Заканчиваем смену");
  
  // Проверяем, нет ли активного заказа
  if (gameState.currentOrder) {
    if (!confirm("У вас есть активный заказ. Вы уверены что хотите закончить смену?")) {
      return;
    }
  }

  try {
    // Отправляем запрос на сервер
    const response = await fetch('/api/stop_shift', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: gameState.userId
      })
    });

    if (!response.ok) {
      throw new Error('Не удалось закончить смену');
    }

    // Обновляем состояние
    gameState.isOnShift = false;
    saveGameState();    gameState.isSearching = false;
    saveGameState();    gameState.currentOrder = null;
    
    // Останавливаем отслеживание
    geoManager.stopTracking();
    
    // Обновляем UI
    updateShiftButton(SHIFT_STATES.START_SHIFT);
    
    console.log("✅ Смена завершена");
    showSuccess("Смена завершена");
    
  } catch (error) {
    throw new Error('Ошибка завершения смены: ' + error.message);
  }
}

/**
 * Обновление кнопки смены в зависимости от состояния
 */
function updateShiftButton(state) {
  const button = document.getElementById("startGame");
  const buttonText = button.querySelector("h3");
  
  if (!button || !buttonText) return;
  
  switch (state) {
    case SHIFT_STATES.REQUESTING_GPS:
      buttonText.textContent = "Разрешить GPS";
      button.style.backgroundColor = "#ff6600";
      button.disabled = false;
      break;
      
    case 'REQUESTING_GPS_ACTIVE':
      buttonText.innerHTML = 'Запрашиваем GPS... <span class="loading-indicator"></span>';
      button.style.backgroundColor = "#ff8800";
      button.disabled = true;
      break;
      
    case SHIFT_STATES.START_SHIFT:
      buttonText.textContent = "Начать смену";
      button.style.backgroundColor = "#121212";
      button.disabled = false;
      break;
      
    case SHIFT_STATES.END_SHIFT:
      buttonText.textContent = "Завершить смену";
      button.style.backgroundColor = "#ff4444";
      button.disabled = false;
      break;
      
    case SHIFT_STATES.SEARCHING:
      buttonText.innerHTML = 'Ищем заказы... <span class="loading-indicator"></span>';
      button.style.backgroundColor = "#00aa44";
      button.disabled = false;
      break;
      
    case 'UNSUPPORTED':
      buttonText.textContent = "GPS недоступен";
      button.style.backgroundColor = "#666666";
      button.disabled = true;
      break;
      
    default:
      console.warn("⚠️ Неизвестное состояние кнопки:", state);
  }
}

/**
 * Callback при получении разрешения GPS
 */
function onGPSPermissionGranted(position) {
  console.log("✅ GPS разрешение получено");
  
  // Центрируем карту на пользователе
  if (map) {
    map.setCenter([position.coords.longitude, position.coords.latitude]);
    map.setZoom(16);
    
    // Добавляем маркер пользователя
    addUserMarker(position.coords);
  }
  
  // Обновляем кнопку
  updateShiftButton(SHIFT_STATES.START_SHIFT);
  
  showSuccess("GPS подключен успешно");
}

/**
 * Callback при отказе в доступе к GPS
 */
function onGPSPermissionDenied(error) {
  console.error("❌ GPS доступ запрещен:", error);
  
  let message = "Для работы приложения нужен доступ к местоположению";
  
  if (error.code === error.PERMISSION_DENIED) {
    message += ". Обновите страницу и разрешите доступ к геолокации.";
  }
  
  showError(message);
  
  // Кнопка остается в состоянии запроса GPS
  updateShiftButton(SHIFT_STATES.REQUESTING_GPS);
}

/**
 * Callback при обновлении позиции
 */
function onPositionUpdate(position) {
  // Обновляем маркер пользователя на карте
  updateUserMarker(position.coords);
  
  // Проверяем качество GPS
  const quality = geoManager.getGPSQuality();
  if (quality === 'poor') {
    console.warn("⚠️ Низкое качество GPS сигнала");
  }
}

/**
/**
 * Добавление маркера пользователя на карту
 */
function addUserMarker(coords) {
  if (!map) return;

  // Ensure userMarker is declared on window
  if (!('userMarker' in window)) {
    window.userMarker = undefined;
  }
  
  // Удаляем предыдущий маркер если есть
  if (window.userMarker) {
    window.userMarker.remove();
  }
  
  // Создаем новый маркер
  window.userMarker = new mapboxgl.Marker({
    color: '#007cbf',
    scale: 0.8
/**
 * Обновление позиции маркера пользователя
 */
function updateUserMarker(coords) {
  // Ensure userMarker is declared on window
  if (!('userMarker' in window)) {
    window.userMarker = undefined;
  }
  if (window.userMarker) {
    window.userMarker.setLngLat([coords.longitude, coords.latitude]);
  }
}
  if (window.userMarker) {
    window.userMarker.setLngLat([coords.longitude, coords.latitude]);
  }
}

/**
 * Центрирование карты на пользователе
 */
function centerOnUser() {
  if (!geoManager.currentPosition || !map) return;
  
  const pos = geoManager.getCurrentPosition();
  map.easeTo({
    center: [pos.lng, pos.lat],
    zoom: 16,
    duration: 1000
  });
}

/**
 * Отправка обновления позиции на сервер
 */
function sendPositionUpdate(position) {
  if (!window.__socket) return;
  
  const coords = position.coords;
  window.__socket.emit('update_position', {
    lat: coords.latitude,
function onSearchStarted() {
  console.log("🔍 Поиск заказов начался");
  updateShiftButton(SHIFT_STATES.SEARCHING);
}
}

// === SocketIO Event Handlers ===

function onSearchStarted(data) {
  console.log("🔍 Поиск заказов начался");
  updateShiftButton(SHIFT_STATES.SEARCHING);
}

function onSearchProgress(data) {
  console.log(`⏳ Прогресс поиска: ${data.elapsed}/${data.total}`);
  
  const button = document.getElementById("startGame");
  const buttonText = button.querySelector("h3");
  if (buttonText) {
    buttonText.textContent = `Поиск... ${data.elapsed}/${data.total}с`;
  }
}

function onOrderFound(data) {
  console.log("✅ Заказ найден:", data.order);
  
  gameState.currentOrder = data.order;
  gameState.isSearching = false;
    saveGameState();  
  // Показываем заказ на карте
  showOrderOnMap(data.order);
  
  // Показываем модальное окно с заказом
  showOrderModal(data.order);
}

function onNoOrdersFound(data) {
  console.log("❌ Заказы не найдены:", data.message);
  
  gameState.isSearching = false;
    saveGameState();  updateShiftButton(SHIFT_STATES.END_SHIFT);
  
  showWarning("Заказов нет в вашем районе. Попробуйте позже.");
}

function onSearchError(data) {
  console.error("❌ Ошибка поиска:", data.message);
  
  gameState.isSearching = false;
    saveGameState();  updateShiftButton(SHIFT_STATES.END_SHIFT);
  
  showError("Ошибка при поиске заказов: " + data.message);
}

// === UI Helper Functions ===

/**
 * Показ заказа на карте
 */
function showOrderOnMap(order) {
  if (!map) return;
  
  // Удаляем предыдущие маркеры заказов
  clearOrderMarkers();
  
  // Добавляем маркер ресторана (pickup)
  const pickupMarker = new mapboxgl.Marker({
    color: '#00aa44', // Зеленый для pickup
    scale: 1.2
  })
  .setLngLat([order.pickup.lng, order.pickup.lat])
  .setPopup(new mapboxgl.Popup({ offset: 25 })
    .setHTML(`<h3>📦 Забрать</h3><p>${order.pickup?.name || "Ресторан"}</p>`))
  .addTo(map);
  
  // Добавляем маркер здания (dropoff)
  const dropoffMarker = new mapboxgl.Marker({
    color: '#ff4444', // Красный для dropoff
    scale: 1.2
  })
  .setLngLat([order.dropoff.lng, order.dropoff.lat])
  .setPopup(new mapboxgl.Popup({ offset: 25 })
    .setHTML(`<h3>🏠 Доставить</h3><p>${order.dropoff?.address || "Адрес"}</p>`))
  .addTo(map);
  
  // Сохраняем маркеры для последующего удаления
  window.orderMarkers = [pickupMarker, dropoffMarker];
  
  // Центрируем карту на маршруте
  const bounds = new mapboxgl.LngLatBounds();
  bounds.extend([order.pickup.lng, order.pickup.lat]);
  bounds.extend([order.dropoff.lng, order.dropoff.lat]);
  
  // Добавляем текущую позицию пользователя если есть
  const userPos = geoManager.getCurrentPosition();
  if (userPos) {
    bounds.extend([userPos.lng, userPos.lat]);
  }
  
  map.fitBounds(bounds, { padding: 80 });
}

/**
 * Очистка маркеров заказов
 */
function clearOrderMarkers() {
  if (window.orderMarkers) {
    window.orderMarkers.forEach(marker => marker.remove());
    window.orderMarkers = [];
  }
}

/**
 * Показ модального окна с заказом
 */
function showOrderModal(order) {
  // Создаем модальное окно для заказа если его нет
  let orderModal = document.getElementById('orderModal');
  if (!orderModal) {
    orderModal = createOrderModal();
  }
  
  // Заполняем данными заказа
  updateOrderModal(order);
  
  // Показываем модалку
  orderModal.style.display = 'flex';
}

/**
 * Создание модального окна заказа
 */
function createOrderModal() {
  const modal = document.createElement('div');
  modal.id = 'orderModal';
  modal.className = 'modal';
  
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal_header">
        <h3 class="black100">Новый заказ</h3>
        <span class="icon_button graybg close" onclick="closeOrderModal()">
          <img src="/static/img/icon/cross.svg" alt="Close" class="icon">
        </span>
      </div>
      
      <div style="padding: 16px; flex: 1; overflow-y: auto;">
        <!-- Информация о заказе -->
        <div style="margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <img src="/static/img/icon/bag.svg" alt="Pickup" style="width: 20px; height: 20px;">
            <h4 class="black100">Забрать из</h4>
          </div>
          <p id="orderPickupName" style="margin-left: 28px; color: #666;"></p>
        </div>
        
        <div style="margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <img src="/static/img/icon/home.svg" alt="Dropoff" style="width: 20px; height: 20px;">
            <h4 class="black100">Доставить по адресу</h4>
          </div>
          <p id="orderDropoffAddress" style="margin-left: 28px; color: #666;"></p>
        </div>
        
        <!-- Детали заказа -->
        <div style="background: #f8f9fa; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="display: flex; align-items: center; gap: 6px;">
              <img src="/static/img/icon/distance.svg" alt="Distance" style="width: 16px; height: 16px;">
              Расстояние
            </span>
            <span id="orderDistance" style="font-weight: 600;"></span>
          </div>
          
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="display: flex; align-items: center; gap: 6px;">
              <img src="/static/img/icon/time.svg" alt="Time" style="width: 16px; height: 16px;">
              Время
            </span>
            <span id="orderTime" style="font-weight: 600;"></span>
          </div>
          
          <div style="display: flex; justify-content: space-between;">
            <span style="font-weight: 600;">Оплата</span>
            <span id="orderAmount" style="font-weight: 700; color: #00aa44;"></span>
          </div>
        </div>
        
        <!-- Кнопки действий -->
        <div style="display: flex; gap: 12px;">
          <button onclick="closeOrderModal()" style="flex: 1; padding: 14px; border: 2px solid #ddd; border-radius: 12px; background: white; color: #666; font-weight: 600;">
            Отклонить
          </button>
          <button onclick="acceptOrder()" style="flex: 2; padding: 14px; border: none; border-radius: 12px; background: #00aa44; color: white; font-weight: 600;">
            Принять заказ
          </button>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  return modal;
}

/**
 * Обновление модального окна заказа данными
 */
function updateOrderModal(order) {
  // Используем вложенные поля pickup.name и dropoff.address
  const pickupName = order.pickup?.name || order.pickup_name || 'Неизвестный ресторан';
  const dropoffAddress = order.dropoff?.address || order.dropoff_address || 'Неизвестный адрес';
  
  document.getElementById('orderPickupName').textContent = pickupName;
  document.getElementById('orderDropoffAddress').textContent = dropoffAddress;
  document.getElementById('orderDistance').textContent = `${order.distance_km} км`;
  document.getElementById('orderTime').textContent = `~${Math.ceil(order.timer_seconds / 60)} мин`;
  document.getElementById('orderAmount').textContent = `$${order.amount}`;
  
  console.log('📦 Order modal updated:', { pickupName, dropoffAddress });
}

/**
 * Закрытие модального окна заказа
 */
function closeOrderModal() {
  const modal = document.getElementById('orderModal');
  if (modal) {
    modal.style.display = 'none';
  }
  
  // Очищаем маркеры заказа
  clearOrderMarkers();
  
  // Возвращаемся к поиску заказов
  if (gameState.isOnShift && !gameState.currentOrder) {
    startSearching();
  }
}

/**
 * Принятие заказа
 */
async function acceptOrder() {
  if (!gameState.currentOrder) {
    console.error("❌ Нет текущего заказа для принятия");
    return;
  }
  
  try {
    console.log("✅ Принимаем заказ:", gameState.currentOrder.id);
    
    // Отправляем запрос на сервер
    const response = await fetch('/api/order/accept', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: gameState.userId,
        order_id: gameState.currentOrder.id
      })
    });
    
    if (!response.ok) {
      throw new Error('Не удалось принять заказ');
    }
    
    const result = await response.json();
    console.log("✅ Заказ принят:", result);
    
    // Закрываем модалку
    closeOrderModal();
    
    // Обновляем кнопку
    const button = document.getElementById("startGame");
    const buttonText = button.querySelector("h3");
    if (buttonText) {
      buttonText.textContent = "К ресторану";
      button.style.backgroundColor = "#007cbf";
    }
    
    showSuccess("Заказ принят! Направляйтесь к ресторану");
    
  } catch (error) {
    console.error("❌ Ошибка принятия заказа:", error);
    showError("Ошибка: " + error.message);
  }
}

// === Modal System ===

/**
 * Инициализация модальных окон
 */
function initializeModals() {
  // Обработчик кнопки профиля
  const profileButton = document.getElementById("profileButton");
  if (profileButton) {
    profileButton.addEventListener("click", () => {
      openModal("profileModal");
    });
  }

  // Обработчики кнопок настроек
  document.querySelectorAll("#gameSettingsButton").forEach(btn => {
    btn.addEventListener("click", () => {
      openModal("settingsModal");
    });
  });

  // Закрытие по крестику
  document.querySelectorAll(".close").forEach(el => {
    el.addEventListener("click", () => {
      const modalId = el.dataset.close;
      if (modalId) {
        closeModal(modalId);
      }
    });
  });

  // Закрытие по клику вне окна
  window.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
      e.target.style.display = "none";
    }
  });
}

/**
 * Открытие модального окна
 */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = "flex";
  }
}

/**
 * Закрытие модального окна
 */
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = "none";
  }
}

// === Notification System ===

/**
 * Показ сообщения об успехе
 */
function showSuccess(message) {
  showNotification(message, 'success');
}

/**
 * Показ предупреждения
 */
function showWarning(message) {
  showNotification(message, 'warning');
}

/**
 * Показ ошибки
 */
function showError(message) {
  showNotification(message, 'error');
}

/**
 * Общая функция показа уведомлений
 */
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  
  // Стили в зависимости от типа
  const styles = {
    info: { bg: '#007cbf', icon: 'ℹ️' },
    success: { bg: '#00aa44', icon: '✅' },
    warning: { bg: '#ff8800', icon: '⚠️' },
    error: { bg: '#ff4444', icon: '❌' }
  };
  
  const style = styles[type] || styles.info;
  
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: ${style.bg};
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    z-index: 10000;
    font-family: Inter, sans-serif;
    font-weight: 500;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    max-width: calc(100vw - 40px);
  `;
  
  notification.textContent = `${style.icon} ${message}`;
  document.body.appendChild(notification);
  
  // Анимация появления
  notification.style.opacity = '0';
  notification.style.transform = 'translateX(-50%) translateY(-20px)';
  
  requestAnimationFrame(() => {
    notification.style.transition = 'all 0.3s ease';
    notification.style.opacity = '1';
    notification.style.transform = 'translateX(-50%) translateY(0)';
  });
  
  // Убираем уведомление через 4 секунды
  setTimeout(() => {
    notification.style.opacity = '0';
    notification.style.transform = 'translateX(-50%) translateY(-20px)';
    
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 4000);
}

// === Global Functions (доступны из window) ===

// Делаем функции доступными глобально для использования в HTML
window.openModal = openModal;
window.closeModal = closeModal;
window.closeOrderModal = closeOrderModal;
window.acceptOrder = acceptOrder;
// === Функции сохранения состояния ===

/**
 * Сохранение состояния игры в localStorage
 */
function saveGameState() {
  const stateToSave = {
    isOnShift: gameState.isOnShift,
    isSearching: gameState.isSearching,
    userId: gameState.userId,
    currentOrder: gameState.currentOrder,
    lastSaved: Date.now()
  };
  
  localStorage.setItem('courierGameState', JSON.stringify(stateToSave));
  console.log("💾 Game state saved");
}

/**
 * Восстановление состояния игры из localStorage  
 */
function restoreGameState() {
  try {
    const savedState = localStorage.getItem('courierGameState');
    if (!savedState) return false;
    
    const state = JSON.parse(savedState);
    const timeDiff = Date.now() - state.lastSaved;
    
    // Если прошло больше 4 часов - сбрасываем состояние
    if (timeDiff > 4 * 60 * 60 * 1000) {
      localStorage.removeItem('courierGameState');
      return false;
    }
    
    // Восстанавливаем состояние
    gameState.isOnShift = state.isOnShift;
    gameState.isSearching = state.isSearching;  
    gameState.currentOrder = state.currentOrder;
    gameState.userId = state.userId || 1;
    
    console.log("�� Game state restored:", state);
    
    // Обновляем UI согласно состоянию
    if (gameState.isOnShift) {
      if (gameState.isSearching) {
        updateShiftButton(SHIFT_STATES.SEARCHING);
      } else if (gameState.currentOrder) {
        const button = document.getElementById("startGame");
        const buttonText = button.querySelector("h3");
        if (buttonText) {
          buttonText.textContent = "К ресторану";
          button.style.backgroundColor = "#007cbf";
        }
      } else {
        updateShiftButton(SHIFT_STATES.END_SHIFT);
      }
      
      // Переподключаемся к SocketIO
      if (window.__socket && geoManager.currentPosition) {
        window.__socket.emit('user_login', { user_id: gameState.userId });
        
        // Если был активный поиск - возобновляем
        if (gameState.isSearching) {
          setTimeout(() => {
            startSearching();
          }, 1000);
        }
      }
    }
    
    return true;
  } catch (error) {
    console.error("❌ Error restoring game state:", error);
    localStorage.removeItem('courierGameState');
    return false;
  }
}

// Вызываем восстановление состояния при инициализации
document.addEventListener("DOMContentLoaded", () => {
  // ... существующий код инициализации ...
  
  // Восстанавливаем состояние после инициализации компонентов
  setTimeout(() => {
    const restored = restoreGameState();
    if (restored) {
      console.log("✅ Previous session restored");
    }
  }, 1000);
});

// Сохраняем состояние при изменениях
function updateGameState() {
  saveGameState();
}

// === Отладочные обработчики событий ===

// Слушаем все SocketIO события для отладки
if (window.__socket) {
  window.__socket.onAny((eventName, ...args) => {
    console.log(`🔌 SocketIO Event: ${eventName}`, args);
  });
  
  // Специальный обработчик для order_found
  window.__socket.on('order_found', (data) => {
    console.log('🎯 order_found event received!', data);
    if (data && data.order) {
      console.log('📦 Order data:', data.order);
      console.log('🏪 Pickup:', data.order.pickup);
      console.log('🏠 Dropoff:', data.order.dropoff);
    }
  });
}

// Основной обработчик события order_found
if (typeof onOrderFound === 'undefined') {
  function onOrderFound(data) {
    console.log("✅ Заказ найден:", data.order);
    
    gameState.currentOrder = data.order;
    gameState.isSearching = false;
    
    // Показываем заказ на карте
    showOrderOnMap(data.order);
    
    // Показываем модальное окно с заказом
    showOrderModal(data.order);
    
    saveGameState();
  }
  
  // Регистрируем обработчик если SocketIO доступен
  if (window.__socket) {
    window.__socket.on('order_found', onOrderFound);
  }
}
