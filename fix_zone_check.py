with open('static/js/modules/orderModal.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем место после сохранения заказа в gameState
old_code = '''    // Показываем маркеры
    if (window.mapManager && result.order) {
      window.mapManager.showOrder(result.order);
    }'''

new_code = '''    // Показываем маркеры
    if (window.mapManager && result.order) {
      window.mapManager.showOrder(result.order);
    }
    
    // Запускаем проверку зон для нового заказа
    if (window.shiftManager) {
      window.shiftManager.startZoneChecking();
    }'''

content = content.replace(old_code, new_code)

with open('static/js/modules/orderModal.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ orderModal.js обновлен - проверка зон будет перезапускаться")
