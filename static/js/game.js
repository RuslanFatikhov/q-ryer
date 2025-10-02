/**
 * Главный файл курьерского симулятора
 * Инициализация и связывание модулей
 */

// Глобальные экземпляры модулей
let gameState = null;
let mapManager = null;
let orderModal = null;
let shiftManager = null;
let socketManager = null;

/**
 * Инициализация приложения
 */
document.addEventListener("DOMContentLoaded", () => {
  console.log("Инициализация курьерского симулятора");

  if (!checkDependencies()) return;

  initializeModules();
  initializeUI();

  restoreState().catch(err => console.error("Ошибка восстановления:", err));

  console.log("Инициализация завершена");
});

/**
 * Проверка зависимостей
 */
function checkDependencies() {
  if (typeof mapboxgl === "undefined") {
    console.error("Mapbox GL не загружен");
    return false;
  }
  if (typeof GeolocationManager === "undefined") {
    console.error("GeolocationManager не загружен");
    return false;
  }
  if (typeof ShiftManager === "undefined") {
    console.error("ShiftManager не загружен (проверь порядок <script>)");
    return false;
  }
  return true;
}

/**
 * Создание экземпляров модулей
 */
function initializeModules() {
  // Состояние игры
  gameState = new GameState();
  window.gameState = gameState;

  // Менеджер карты
  mapManager = new MapManager();
  window.mapManager = mapManager;
  mapManager.initialize();

  // WebSocket
  socketManager = new SocketManager(gameState, null, mapManager);
  window.socketManager = socketManager;
  socketManager.initialize();

  // Менеджер смен
  shiftManager = new ShiftManager(gameState, socketManager);
  window.shiftManager = shiftManager;

  // Модалка заказов
  orderModal = new OrderModal(gameState, shiftManager);
  window.orderModal = orderModal;

  // Связь сокета с модалкой
  socketManager.orderModal = orderModal;

  // Геолокация
  initializeGeolocation();
}

/**
 * Инициализация геолокации
 */
function initializeGeolocation() {
  const geoManager = new GeolocationManager();
  window.geoManager = geoManager;

  if (!geoManager.isSupported()) {
    shiftManager.updateShiftButton('UNSUPPORTED');
    return;
  }

  // Коллбэки
  geoManager.onPermissionGranted = (pos) => shiftManager.onGPSPermissionGranted(pos);
  geoManager.onPermissionDenied = (err) => shiftManager.onGPSPermissionDenied(err);
  geoManager.onPositionUpdate  = (pos) => shiftManager.onPositionUpdate(pos);

  // ВАЖНО: используем константу состояния, а не строку
  shiftManager.updateShiftButton(shiftManager.SHIFT_STATES.REQUESTING_GPS);
}

/**
 * Настройка UI элементов
 */
function initializeUI() {
  // Кнопка смены
  const startGameButton = document.getElementById("startGame");
  if (startGameButton) {
    startGameButton.addEventListener("click", () => {
      shiftManager.handleShiftButtonClick();
    });
  }

  // Кнопка "мое местоположение"
  const myLocationButton = document.querySelector(".myloc");
  if (myLocationButton) {
    myLocationButton.addEventListener("click", () => {
      mapManager.centerOnUser();
    });
  }

  // Модальные окна
  initializeModals();

  // Кнопка завершения смены в профиле
  const endShiftBtn = document.getElementById("endShiftBtn");
  if (endShiftBtn) {
    endShiftBtn.addEventListener("click", async () => {
      if (!confirm("Завершить смену? Активные заказы будут отменены.")) return;

      try {
        const response = await fetch('/api/stop_shift', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: gameState.userId })
        });

        if (response.ok) {
          window.location.reload();
        } else {
          const error = await response.json().catch(() => ({}));
          alert("Ошибка: " + (error.error || 'Неизвестная ошибка'));
        }
      } catch (e) {
        alert("Ошибка: " + e.message);
      }
    });
  }
}

/**
 * Инициализация модальных окон
 */
function initializeModals() {
  const profileButton = document.getElementById("profileButton");
  if (profileButton) {
    profileButton.addEventListener("click", () => {
      openModal("profileModal");
    });
  }

  document.querySelectorAll(".close").forEach(el => {
    el.addEventListener("click", () => {
      const modalId = el.dataset.close;
      if (modalId) closeModal(modalId);
    });
  });

  window.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
      e.target.style.display = "none";
    }
  });
}

/**
 * Восстановление состояния
 */
async function restoreState() {
  const stateManager = new StateManager(gameState);
  window.stateManager = stateManager;

  const restored = await stateManager.restoreFromServer();

  if (restored) {
    console.log("✅ Состояние восстановлено с сервера");

    if (gameState.currentOrder && window.geoManager) {
      await window.geoManager.requestPermission();
      window.geoManager.startTracking((position) => {
        window.shiftManager?.sendPositionUpdate(position);
      });
    }
  } else {
    console.log("Нет активного состояния для восстановления");
  }
}

/**
 * Утилиты модалок
 */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "flex";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "none";
}

// Экспорт
window.openModal = openModal;
window.closeModal = closeModal;
