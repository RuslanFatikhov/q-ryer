// static/js/socket.js

// Создаем глобальное подключение Socket.IO
window.__socket = io();

// Логируем соединение
window.__socket.on("connect", () => {
  console.log("✅ Socket.IO connected:", window.__socket.id);
});

window.__socket.on("disconnect", () => {
  console.log("❌ Socket.IO disconnected");
});
