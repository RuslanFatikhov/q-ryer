with open('static/js/modules/socketManager.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем onSearchStarted - игнорируем если есть активный заказ
old_method = '''  onSearchStarted(data) {
    console.log("Поиск заказов начался");
    if (window.shiftManager) {
      window.shiftManager.updateShiftButton('searching');
    }
  }'''

new_method = '''  onSearchStarted(data) {
    console.log("Поиск заказов начался");
    
    // Игнорируем если уже есть активный заказ
    if (this.gameState.currentOrder) {
      console.log("Игнорируем search_started - уже есть активный заказ");
      return;
    }
    
    if (window.shiftManager) {
      window.shiftManager.updateShiftButton('searching');
    }
  }'''

content = content.replace(old_method, new_method)

with open('static/js/modules/socketManager.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ onSearchStarted исправлен - игнорирует событие если есть активный заказ")
