// ============================================
// Модуль модальных окон для замены alert()
// Универсальная система уведомлений
// ============================================

class AlertModal {
  constructor() {
    this.modal = null;
    this.init();
  }

  // Инициализация модального окна
  init() {
    // Создаем элемент модального окна, если его еще нет
    if (!document.getElementById('alertModal')) {
      this.createModal();
    }
    this.modal = document.getElementById('alertModal');
  }

  // Создание HTML структуры модального окна
  createModal() {
    const modalHTML = `
      <div id="alertModal">
        <div class="vstack gap16 alert-modal-content">

          <!--Icon-->
          <div class="alert-modal-icon" id="alertModalIcon">
            <!-- Иконка будет добавлена динамически -->
          </div>
          <h2 class="black100 tac" id="alertModalTitle" style="margin-bottom:12px"></h2>
          <p class="black100 tac" id="alertModalMessage"></p>
          <div class="alert-modal-buttons">
            <button class="action_button" id="alertModalBtn">
              <h3 class="white100">ОК</h3></button>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
  }

  // Показать модальное окно
  show(message, title = 'Уведомление', type = 'info') {
    const modal = document.getElementById('alertModal');
    const titleEl = document.getElementById('alertModalTitle');
    const messageEl = document.getElementById('alertModalMessage');
    const iconEl = document.getElementById('alertModalIcon');
    const btn = document.getElementById('alertModalBtn');

    // Устанавливаем заголовок и сообщение
    titleEl.textContent = title;
    messageEl.textContent = message;

    // Устанавливаем иконку в зависимости от типа
    iconEl.innerHTML = this.getIcon(type);
    
    // Устанавливаем класс для стилизации
    modal.className = 'alert-modal active alert-modal-' + type;

    // Показываем модальное окно
    modal.style.display = 'flex';

    // Обработчик закрытия
    const closeModal = () => {
      modal.classList.remove('active');
      setTimeout(() => {
        modal.style.display = 'none';
        messageEl.innerHTML = ''; // Очищаем HTML
      }, 300);
    };

    // Закрытие по кнопке OK
    btn.onclick = closeModal;

    // Закрытие по клику вне модального окна
    modal.onclick = (e) => {
      if (e.target === modal) {
        closeModal();
      }
    };

    // Закрытие по Escape
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  // Получить SVG иконку в зависимости от типа
  // Получить иконку в зависимости от типа
  getIcon(type) {
    const icons = {
      success: `<img src="/static/img/icon/success.png" alt="Success" class="alert_modal_icon">`,
      error: `<img src="/static/img/icon/error.png" alt="Error" class="alert_modal_icon">`,
      warning: `<img src="/static/img/icon/warning.png" alt="Warning" class="alert_modal_icon">`,
      info: `<img src="/static/img/icon/info.png" alt="Info" class="alert_modal_icon">`
    };
    return icons[type] || icons.info;
  }

  // Специальный метод для показа баланса с иконками
  showBalance(payout, newBalance, bonusText = "", title = "Заказ доставлен") {
    const modal = document.getElementById("alertModal");
    const titleEl = document.getElementById("alertModalTitle");
    const messageEl = document.getElementById("alertModalMessage");
    const iconEl = document.getElementById("alertModalIcon");
    const btn = document.getElementById("alertModalBtn");

    // Устанавливаем заголовок
    titleEl.textContent = title;

    // Создаем HTML с иконками монет
    messageEl.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 12px; width: 100%;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <p class="black100" style="margin: 0;">Выплата:</p>
          <span style="display: flex; align-items: center; gap: 4px;">
            <img src="/static/img/icon/qoin.png" alt="qoin" style="width: 20px; height: 20px;">
            <p class="black100" style="margin: 0;">${Number(payout).toFixed(2)}${bonusText}</p>
          </span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 8px; background: var(--bg2); border-radius: 8px;">
          <h4 class="black100 fw700" style="margin: 0;">Баланс:</h4>
          <span style="display: flex; align-items: center; gap: 4px;">
            <img src="/static/img/icon/qoin.png" alt="qoin" style="width: 20px; height: 20px;">
            <h4 class="black100 fw700" style="margin: 0;">${Number(newBalance).toFixed(2)}</h4>
          </span>
        </div>
      </div>
    `;

    // Устанавливаем иконку успеха
    iconEl.innerHTML = this.getIcon("success");

    // Устанавливаем класс для стилизации
    modal.className = "alert-modal active alert-modal-success";

    // Показываем модальное окно
    modal.style.display = "flex";

    // Обработчик закрытия
    const closeModal = () => {
      modal.classList.remove("active");
      setTimeout(() => {
        modal.style.display = "none";
        // Очищаем innerHTML обратно
        messageEl.innerHTML = "";
      }, 300);
    };

    // Закрытие по кнопке OK
    btn.onclick = closeModal;

    // Закрытие по клику вне модального окна
    modal.onclick = (e) => {
      if (e.target === modal) {
        closeModal();
      }
    };

    // Закрытие по Escape
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        closeModal();
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);
  }
  // Методы для быстрого вызова разных типов уведомлений
  success(message, title = 'Успех') {
    this.show(message, title, 'success');
  }

  error(message, title = 'Ошибка') {
    this.show(message, title, 'error');
  }

  warning(message, title = 'Внимание') {
    this.show(message, title, 'warning');
  }

  info(message, title = 'Информация') {
    this.show(message, title, 'info');
  }
}

// Создаем глобальный экземпляр
window.alertModal = new AlertModal();

// Экспортируем для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = alertModal;
}
