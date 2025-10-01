# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки логики pickup зоны.
Симулирует нахождение игрока рядом с рестораном.
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Order
from app.utils.game_helper import check_player_zones, get_order_for_user
from app.utils.gps_helper import calculate_distance_meters

def test_pickup_zone():
    """Тестирование логики pickup зоны"""
    
    app = create_app('development')
    
    with app.app_context():
        print("=" * 60)
        print("🧪 ТЕСТ: Проверка нахождения игрока в зоне ресторана")
        print("=" * 60)
        
        # 1. Создаем или получаем тестового пользователя
        user = User.query.get(1)
        if not user:
            user = User.create_user(username="TestUser")
            print(f"✅ Создан тестовый пользователь: {user.username} (ID: {user.id})")
        else:
            print(f"✅ Используем существующего пользователя: {user.username} (ID: {user.id})")
        
        # 2. Генерируем заказ для пользователя
        print("\n📦 Генерируем новый заказ...")
        order_data = get_order_for_user(user.id)
        
        if not order_data:
            print("❌ Не удалось сгенерировать заказ")
            return
        
        print(f"✅ Заказ создан:")
        print(f"   Ресторан: {order_data['pickup']['name']}")
        print(f"   Координаты: ({order_data['pickup']['lat']}, {order_data['pickup']['lng']})")
        print(f"   Адрес доставки: {order_data['dropoff']['address']}")
        print(f"   Дистанция: {order_data['distance_km']} км")
        
        # 3. Получаем заказ из БД
        order = Order.query.get(order_data['id'])
        
        # 4. Тестируем разные позиции игрока
        print("\n" + "=" * 60)
        print("📍 ТЕСТ 1: Игрок далеко от ресторана (100м)")
        print("=" * 60)
        
        # Позиция в 100 метрах от ресторана (примерно 0.001 градуса)
        test_lat_far = order.pickup_lat + 0.001
        test_lng_far = order.pickup_lng + 0.001
        
        distance_far = calculate_distance_meters(
            order.pickup_lat, order.pickup_lng,
            test_lat_far, test_lng_far
        )
        
        print(f"   Позиция игрока: ({test_lat_far}, {test_lng_far})")
        print(f"   Расстояние до ресторана: {distance_far:.1f} м")
        
        zones_far = check_player_zones(user.id, test_lat_far, test_lng_far)
        print(f"   В зоне pickup: {'✅ ДА' if zones_far.get('in_pickup_zone') else '❌ НЕТ'}")
        print(f"   Может забрать заказ: {'✅ ДА' if zones_far.get('can_pickup') else '❌ НЕТ'}")
        
        # 5. Тестируем позицию ВНУТРИ радиуса (20м)
        print("\n" + "=" * 60)
        print("📍 ТЕСТ 2: Игрок близко к ресторану (20м)")
        print("=" * 60)
        
        # Позиция в 20 метрах (примерно 0.0002 градуса)
        test_lat_near = order.pickup_lat + 0.0002
        test_lng_near = order.pickup_lng + 0.0002
        
        distance_near = calculate_distance_meters(
            order.pickup_lat, order.pickup_lng,
            test_lat_near, test_lng_near
        )
        
        print(f"   Позиция игрока: ({test_lat_near}, {test_lng_near})")
        print(f"   Расстояние до ресторана: {distance_near:.1f} м")
        
        zones_near = check_player_zones(user.id, test_lat_near, test_lng_near)
        print(f"   В зоне pickup: {'✅ ДА' if zones_near.get('in_pickup_zone') else '❌ НЕТ'}")
        print(f"   Может забрать заказ: {'✅ ДА' if zones_near.get('can_pickup') else '❌ НЕТ'}")
        
        # 6. Тестируем ТОЧНУЮ позицию ресторана (0м)
        print("\n" + "=" * 60)
        print("📍 ТЕСТ 3: Игрок точно на ресторане (0м)")
        print("=" * 60)
        
        print(f"   Позиция игрока: ({order.pickup_lat}, {order.pickup_lng})")
        print(f"   Расстояние до ресторана: 0.0 м")
        
        zones_exact = check_player_zones(user.id, order.pickup_lat, order.pickup_lng)
        print(f"   В зоне pickup: {'✅ ДА' if zones_exact.get('in_pickup_zone') else '❌ НЕТ'}")
        print(f"   Может забрать заказ: {'✅ ДА' if zones_exact.get('can_pickup') else '❌ НЕТ'}")
        
        # 7. Дополнительная информация
        print("\n" + "=" * 60)
        print("📊 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ")
        print("=" * 60)
        
        from flask import current_app
        config = current_app.config['GAME_CONFIG']
        print(f"   Радиус pickup: {config['pickup_radius']} м")
        print(f"   Радиус dropoff: {config['dropoff_radius']} м")
        print(f"   Статус заказа: {order.status}")
        print(f"   Заказ забран: {'✅ ДА' if order.pickup_time else '❌ НЕТ'}")
        
        print("\n" + "=" * 60)
        print("✅ ТЕСТ ЗАВЕРШЕН")
        print("=" * 60)

if __name__ == '__main__':
    test_pickup_zone()
