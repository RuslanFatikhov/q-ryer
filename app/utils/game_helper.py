# -*- coding: utf-8 -*-
"""
Основная игровая логика для симулятора курьера.
Генерация заказов, проверка зон, завершение доставки.
"""

import logging
from typing import Dict, Optional
from flask import current_app
from app.utils.restaurant_helper import get_random_restaurant, is_player_at_restaurant, get_restaurants_near_location
from app.utils.building_helper import get_random_building_for_delivery, is_player_at_building, get_buildings_near_location
from app.utils.economy import calculate_delivery_stats
from app.utils.gps_helper import calculate_distance
from app.models.user import User
from app import db
import random

# Настройка логирования
logger = logging.getLogger(__name__)


def generate_random_order(user_lat: float = None, user_lng: float = None, 
                         radius_km: float = 5.0) -> Optional[Dict]:
    """
    Генерация случайного заказа: ресторан → здание.
    Учитывает радиус поиска пользователя - оба объекта должны быть в радиусе.
    
    Args:
        user_lat (float): Широта текущей позиции пользователя
        user_lng (float): Долгота текущей позиции пользователя
        radius_km (float): Радиус поиска заказов в километрах (3-25 км)
    
    Returns:
        dict: Данные нового заказа или None, если не удалось сгенерировать
        
    Raises:
        Exception: При критических ошибках генерации
    """
    try:
        # Если позиция пользователя не указана - используем старую логику (любой ресторан)
        if user_lat is None or user_lng is None:
            logger.warning("User position not provided, using fallback order generation")
            restaurant = get_random_restaurant()
            if not restaurant:
                logger.error("No restaurants available for order generation")
                return None
            
            building = get_random_building_for_delivery(
                restaurant['lat'], 
                restaurant['lng']
            )
            if not building:
                logger.error(f"No suitable buildings found for delivery from {restaurant['name']}")
                return None
        else:
            # НОВАЯ ЛОГИКА: Ресторан и здание должны быть в радиусе от пользователя
            logger.info(f"Generating order within {radius_km}km radius from user position ({user_lat}, {user_lng})")
            
            # Получаем рестораны в радиусе от пользователя
            nearby_restaurants = get_restaurants_near_location(user_lat, user_lng, radius_km)
            if not nearby_restaurants:
                logger.warning(f"No restaurants found within {radius_km}km radius")
                return None
            
            # Выбираем случайный ресторан из доступных
            restaurant = random.choice(nearby_restaurants)
            
            # Получаем здания в радиусе от пользователя
            nearby_buildings = get_buildings_near_location(user_lat, user_lng, radius_km)
            if not nearby_buildings:
                logger.warning(f"No buildings found within {radius_km}km radius")
                return None
            
            # Фильтруем здания: минимум 0.5км от ресторана, максимум в пределах радиуса
            suitable_buildings = []
            for building in nearby_buildings:
                distance_to_restaurant = calculate_distance(
                    restaurant['lat'], restaurant['lng'],
                    building['lat'], building['lng']
                )
                # Здание должно быть минимум в 500м от ресторана и в пределах радиуса от пользователя
                if distance_to_restaurant >= 0.5 and building.get('distance_km', 0) <= radius_km:
                    suitable_buildings.append(building)
            
            if not suitable_buildings:
                logger.warning(f"No suitable buildings found (need min 0.5km from restaurant)")
                return None
            
            # Выбираем случайное здание
            building = random.choice(suitable_buildings)
        
        # Рассчитываем расстояние доставки между рестораном и зданием
        distance_km = calculate_distance(
            restaurant['lat'], restaurant['lng'],
            building['lat'], building['lng']
        )
        
        # Получаем экономические параметры заказа (таймер, выплата, бонусы)
        delivery_stats = calculate_delivery_stats(distance_km)
        
        # Формируем полные данные заказа для создания в БД
        order_data = {
            'pickup_name': restaurant['name'],
            'pickup_lat': restaurant['lat'],
            'pickup_lng': restaurant['lng'],
            'dropoff_address': building['address'],
            'dropoff_lat': building['lat'],
            'dropoff_lng': building['lng'],
            'distance_km': distance_km,
            'estimated_minutes': delivery_stats['estimated_minutes'],
            'timer_seconds': delivery_stats['timer_seconds'],
            'base_payout': delivery_stats['base_payout'],
            'potential_payout_with_bonus': delivery_stats['potential_payout_with_bonus']
        }
        
        logger.info(f"Generated order: {restaurant['name']} → {building['address']} ({distance_km:.2f} km)")
        return order_data
        
    except Exception as e:
        logger.error(f"Error generating random order: {str(e)}", exc_info=True)
        return None


def create_order_for_user(user_id: int, order_data: Dict) -> Optional["Order"]:
    """
    Создание заказа в базе данных для конкретного пользователя.
    Проверяет наличие активных заказов перед созданием нового.
    
    Args:
        user_id (int): ID пользователя в системе
        order_data (dict): Данные заказа из generate_random_order()
    
    Returns:
        Order: Объект созданного заказа или None при ошибке
    """
    from app.models.order import Order  # Локальный импорт для избежания циклических зависимостей
    
    try:
        # Проверяем существование пользователя в базе
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found in database")
            return None
        
        # Проверяем, что у пользователя нет других активных заказов
        active_order = user.get_active_order()
        if active_order:
            logger.warning(f"User {user_id} already has active order {active_order.id}")
            return None
        
        # Создаем новый заказ в базе данных
        order = Order(
            user_id=user_id,
            pickup_name=order_data['pickup_name'],
            pickup_lat=order_data['pickup_lat'],
            pickup_lng=order_data['pickup_lng'],
            dropoff_address=order_data['dropoff_address'],
            dropoff_lat=order_data['dropoff_lat'],
            dropoff_lng=order_data['dropoff_lng'],
            distance_km=order_data['distance_km'],
            timer_seconds=order_data['timer_seconds'],
            amount=order_data['base_payout']
        )
        
        db.session.add(order)
        db.session.commit()
        
        logger.info(f"Created order {order.id} for user {user_id}")
        return order
        
    except Exception as e:
        logger.error(f"Error creating order for user {user_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return None


def get_order_for_user(user_id: int) -> Optional[Dict]:
    """
    Генерация и создание нового заказа для пользователя.
    Единая точка входа для получения заказа - сначала генерирует, потом создает в БД.
    Учитывает текущую позицию пользователя и его настройку радиуса поиска.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Данные созданного заказа в формате для фронтенда или None
    """
    try:
        # Получаем информацию о пользователе
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        # Получаем позицию и радиус поиска пользователя
        user_lat = user.last_position_lat
        user_lng = user.last_position_lng
        radius_km = user.search_radius_km  # Используем настройку радиуса пользователя (3-25 км)
        
        # Проверяем наличие позиции пользователя
        if user_lat is None or user_lng is None:
            logger.warning(f"User {user_id} has no GPS position, using fallback generation")
            # Если нет позиции - генерируем заказ без учета радиуса
            order_data = generate_random_order()
        else:
            # Генерируем заказ с учетом позиции и радиуса пользователя
            logger.info(f"Generating order for user {user_id} with radius {radius_km}km")
            order_data = generate_random_order(user_lat, user_lng, radius_km)
        
        if not order_data:
            logger.warning(f"Failed to generate order for user {user_id} - no suitable restaurants/buildings in radius")
            return None
        
        # Создаем заказ в базе данных
        order = create_order_for_user(user_id, order_data)
        if not order:
            logger.warning(f"Failed to create order in database for user {user_id}")
            return None
        
        # Возвращаем заказ в формате словаря для JSON API
        return order.to_dict()
        
    except Exception as e:
        logger.error(f"Error getting order for user {user_id}: {str(e)}", exc_info=True)
        return None


def validate_order_action(user_id: int, action: str) -> Dict:
    """
    Валидация возможности выполнения действия с заказом.
    Проверяет бизнес-правила перед выполнением операций.
    
    Args:
        user_id (int): ID пользователя
        action (str): Действие для валидации (accept, pickup, deliver, cancel)
    
    Returns:
        dict: Результат валидации с флагом valid и описанием ошибки
    """
    try:
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            return {'valid': False, 'error': 'User not found'}
        
        # Получаем активный заказ (если есть)
        active_order = user.get_active_order()
        
        # Проверка по типу действия
        if action in ['pickup', 'deliver', 'cancel']:
            if not active_order:
                return {'valid': False, 'error': 'No active order'}
        
        if action == 'pickup':
            if active_order.pickup_time:
                return {'valid': False, 'error': 'Order already picked up'}
        
        if action == 'deliver':
            if not active_order.pickup_time:
                return {'valid': False, 'error': 'Order not picked up yet'}
            if active_order.delivery_time:
                return {'valid': False, 'error': 'Order already delivered'}
        
        return {'valid': True}
        
    except Exception as e:
        logger.error(f"Error validating action {action} for user {user_id}: {str(e)}")
        return {'valid': False, 'error': 'Validation failed'}


def check_player_zones(user_id: int, player_lat: float, player_lng: float) -> Dict:
    """
    Проверка нахождения игрока в зонах pickup/dropoff активного заказа.
    Используется для определения возможности забора/доставки заказа.
    
    Args:
        user_id (int): ID пользователя
        player_lat (float): Широта текущей позиции игрока
        player_lng (float): Долгота текущей позиции игрока
    
    Returns:
        dict: Статус зон с расстояниями и возможными действиями
    """
    try:
        # Получаем пользователя из базы
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Получаем активный заказ пользователя
        active_order = user.get_active_order()
        if not active_order:
            return {
                'has_active_order': False,
                'in_pickup_zone': False,
                'in_dropoff_zone': False
            }
        
        # Получаем радиусы зон из игровой конфигурации
        config = current_app.config['GAME_CONFIG']
        pickup_radius = config['pickup_radius']  # По умолчанию 30 метров
        dropoff_radius = config['dropoff_radius']  # По умолчанию 30 метров
        
        # Проверяем, находится ли игрок в радиусе ресторана (pickup zone)
        in_pickup = is_player_at_restaurant(
            player_lat, player_lng,
            active_order.pickup_lat, active_order.pickup_lng,
            pickup_radius
        )
        
        # Проверяем, находится ли игрок в радиусе здания доставки (dropoff zone)
        in_dropoff = is_player_at_building(
            player_lat, player_lng,
            active_order.dropoff_lat, active_order.dropoff_lng,
            dropoff_radius
        )
        
        # Рассчитываем точные расстояния до обеих точек для отображения в UI
        distance_to_pickup = calculate_distance(
            player_lat, player_lng,
            active_order.pickup_lat, active_order.pickup_lng
        ) * 1000  # Конвертируем км в метры
        
        distance_to_dropoff = calculate_distance(
            player_lat, player_lng,
            active_order.dropoff_lat, active_order.dropoff_lng
        ) * 1000  # Конвертируем км в метры
        
        # Возвращаем полный статус для принятия решений на фронтенде
        return {
            'has_active_order': True,
            'order_id': active_order.id,
            'order_status': active_order.status,
            'in_pickup_zone': in_pickup,
            'in_dropoff_zone': in_dropoff,
            'distance_to_pickup_meters': round(distance_to_pickup),
            'distance_to_dropoff_meters': round(distance_to_dropoff),
            # Флаги возможности действий
            'can_pickup': in_pickup and not active_order.pickup_time,
            'can_deliver': in_dropoff and active_order.pickup_time and not active_order.delivery_time
        }
        
    except Exception as e:
        logger.error(f"Error checking player zones for user {user_id}: {str(e)}", exc_info=True)
        return {'error': 'Zone check failed'}


def pickup_order(user_id: int) -> Dict:
    """
    Забор заказа игроком из ресторана.
    Отмечает время забора и обновляет статус.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат операции pickup
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Выполняем pickup через метод модели Order
        success = active_order.pickup_order()
        if not success:
            return {'success': False, 'error': 'Failed to pickup order'}
        
        logger.info(f"User {user_id} picked up order {active_order.id}")
        
        return {
            'success': True,
            'message': 'Order picked up successfully',
            'order': active_order.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error in pickup_order for user {user_id}: {str(e)}")
        return {'success': False, 'error': 'Pickup failed'}


def deliver_order(user_id: int) -> Dict:
    """
    Доставка заказа игроком к клиенту.
    Рассчитывает оплату, обновляет баланс, завершает заказ.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат операции delivery с суммой выплаты
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Выполняем доставку через метод модели Order
        result = active_order.deliver_order()
        
        # Проверяем если метод вернул ошибку
        if result and isinstance(result, dict) and not result.get('success', True):
            return result
        
        # Коммитим изменения
        db.session.commit()
        
        # Получаем payout из заказа (установлен методом deliver_order)
        payout = active_order.amount
        
        # Обновляем баланс пользователя
        user.update_balance(payout)
        user.increment_deliveries()
        
        logger.info(f"User {user_id} completed delivery of order {active_order.id}, earned ${payout}")
        
        return {
            'success': True,
            'message': 'Order delivered successfully',
            'payout': round(payout, 2),
            'new_balance': round(user.balance, 2),
            'order': active_order.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error in deliver_order for user {user_id}: {str(e)}")
        db.session.rollback()
        return {'success': False, 'error': 'Delivery failed'}
def cancel_order(user_id: int, reason: str = 'user_cancelled') -> Dict:
    """
    Отмена заказа игроком.
    
    Args:
        user_id (int): ID пользователя
        reason (str): Причина отмены
    
    Returns:
        dict: Результат операции cancel
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Отменяем заказ через метод модели Order
        success = active_order.cancel_order(reason)
        if not success:
            return {'success': False, 'error': 'Failed to cancel order'}
        
        logger.info(f"User {user_id} cancelled order {active_order.id}, reason: {reason}")
        
        return {
            'success': True,
            'message': 'Order cancelled successfully',
            'order': active_order.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error in cancel_order for user {user_id}: {str(e)}")
        return {'success': False, 'error': 'Cancel failed'}
