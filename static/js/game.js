// static/js/game.js

document.addEventListener("DOMContentLoaded", () => {
  if (typeof mapboxgl === "undefined") {
    console.error("❌ Mapbox GL не загружен. Проверь подключение библиотеки.");
    return;
  }

  const map = new mapboxgl.Map({
    container: "map",
    style: "mapbox://styles/mapbox/streets-v11",
    center: [76.8897, 43.2389], // Алматы
    zoom: 12,
  });

  const statusEl = document.getElementById("game-status");

  document.getElementById("start-search").addEventListener("click", () => {
    statusEl.textContent = "Статус: ищем заказ...";
    if (window.__socket) {
      window.__socket.emit("start_order_search", { radius_km: 5 });
    }
  });

  document.getElementById("stop-search").addEventListener("click", () => {
    statusEl.textContent = "Статус: поиск остановлен.";
    if (window.__socket) {
      window.__socket.emit("stop_order_search");
    }
  });

  if (window.__socket) {
    window.__socket.on("search_started", () => {
      statusEl.textContent = "🔍 Поиск заказов начался...";
    });

    window.__socket.on("search_progress", (data) => {
      statusEl.textContent = `⏳ Идёт поиск: ${data.elapsed}/${data.total} сек...`;
    });

    window.__socket.on("order_found", (data) => {
      statusEl.textContent = `✅ Заказ найден: ${data.order.pickup_name} → ${data.order.dropoff_address}`;
      new mapboxgl.Marker({ color: "green" })
        .setLngLat([data.order.pickup_lng, data.order.pickup_lat])
        .addTo(map);
      new mapboxgl.Marker({ color: "red" })
        .setLngLat([data.order.dropoff_lng, data.order.dropoff_lat])
        .addTo(map);
    });

    window.__socket.on("no_orders_found", (data) => {
      statusEl.textContent = `❌ ${data.message}`;
    });
  }
});
