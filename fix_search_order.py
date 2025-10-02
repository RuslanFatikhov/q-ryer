with open('app/socketio_handlers/game_events.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем и меняем порядок
old_order = '''        # Запускаем симуляцию поиска (синхронная версия с socketio.sleep)
        simulate_order_search_sync(user_id, radius_km)
        
        # Подтверждаем начало поиска
        emit('search_started', {
            'status': 'searching', 
            'radius_km': radius_km
        })'''

new_order = '''        # Подтверждаем начало поиска ПЕРЕД симуляцией
        emit('search_started', {
            'status': 'searching', 
            'radius_km': radius_km
        })
        
        # Запускаем симуляцию поиска (синхронная версия с socketio.sleep)
        simulate_order_search_sync(user_id, radius_km)'''

content = content.replace(old_order, new_order)

with open('app/socketio_handlers/game_events.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Порядок событий исправлен: search_started теперь отправляется ДО симуляции")
