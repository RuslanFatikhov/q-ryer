with open('static/js/game.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим и заменяем функцию restoreState
old_restore = '''/**
 * Восстановление состояния
 */
function restoreState() {
  const restored = gameState.restore();
  if (restored) {
    console.log("Состояние восстановлено");
  }
}'''

new_restore = '''/**
 * Восстановление состояния
 */
async function restoreState() {
  // Создаем StateManager
  const stateManager = new StateManager(gameState);
  window.stateManager = stateManager;
  
  // Пытаемся восстановить состояние с сервера
  const restored = await stateManager.restoreFromServer();
  
  if (restored) {
    console.log("✅ Состояние восстановлено с сервера");
    
    // Если есть активный заказ, запускаем GPS tracking
    if (gameState.currentOrder && window.geoManager) {
      await window.geoManager.requestPermission();
      window.geoManager.startTracking((position) => {
        if (window.shiftManager) {
          window.shiftManager.sendPositionUpdate(position);
        }
      });
    }
  } else {
    console.log("Нет активного состояния для восстановления");
  }
}'''

content = content.replace(old_restore, new_restore)

# Делаем restoreState async в вызове
content = content.replace('  restoreState();', '  restoreState().catch(err => console.error("Ошибка восстановления:", err));')

with open('static/js/game.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ game.js обновлен для восстановления состояния с сервера")
