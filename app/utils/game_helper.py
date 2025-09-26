# -*- coding: utf-8 -*-
"""
Основная игровая логика для симулятора курьера.
Генерация заказов, проверка зон, завершение доставки.
"""

import logging
from typing import Dict, Optional, Tuple
from flask import current_app
from app.utils.restaurant_helper import get_random_restaurant, is_player_at_restaurant
from app.utils.building_helper import get_random_building_for_delivery, is_player_at_building
from app.utils.economy import calculate_delivery_stats
from app.utils.gps_helper import calculate_distance
from app.models.user import User
from app import db

# Настройка логирования
logger = logging.getLogger(__name__)

def generate_random_order() -> Optional["Dict"]:
    """
    Генерация случайного заказа: ресторан → здание.
    
    Returns:
        dict: Данные нового заказа или None
    """
    try:
        # Получаем случайный ресторан
        restaurant = get_random_restaurant()
        if not restaurant:
            logger.error("No restaurants available")
            return None
        
        # Получаем подходящее здание для доставки
        building = get_random_building_for_delivery(
            restaurant['lat'], 
            restaurant['lng']
        )
        if not building:
            logger.error("No suitable buildings found for delivery")
            return None
        
        # Рассчитываем параметры заказа
        distance_km = calculate_distance(
            restaurant['lat'], restaurant['lng'],
            building['lat'], building['lng']
        )
        
        delivery_stats = calculate_delivery_stats(distance_km)
        
        # Формируем данные заказа
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
        
        logger.info(f"Generated order: {restaurant['name']} → {building['address']}")
        return order_data
        
    except Exception as e:
        logger.error(f"Error generating order: {str(e)}")
        return None

def create_order_for_user(user_id: int, order_data: Dict) -> Optional["Order"]:
    """
    Создание заказа в базе данных для пользователя.
    
    Args:
        user_id (int): ID пользователя
        order_data (dict): Данные заказа
    
    Returns:
        Order: Созданный заказ или None
    """
    from app.models.order import Order  # локальный импорт
    
    try:
        # Проверяем, что у пользователя нет активного заказа
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        active_order = user.get_active_order()
        if active_order:
            logger.warning(f"User {user_id} already has active order {active_order.id}")
            return None
        
        # Создаем заказ с правильными полями
        order = Order(
            user_id=user_id,
            pickup_name=order_data['pickup_name'],
            dropoff_address=order_data['dropoff_address'],
            pickup_lat=order_data['pickup_lat'],
            pickup_lng=order_data['pickup_lng'],
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
        logger.error(f"Error creating order: {str(e)}")
        db.session.rollback()
        return None

def check_player_zones(user_id: int, player_lat: float, player_lng: float) -> Dict:
    """
    Проверка, в каких зонах находится игрок (pickup/dropoff).
    
    Args:
        user_id (int): ID пользователя
        player_lat (float): Широта игрока
        player_lng (float): Долгота игрока
    
    Returns:
        dict: Статус зон игрока
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {
                'has_active_order': False,
                'in_pickup_zone': False,
                'in_dropoff_zone': False
            }
        
        # Получаем радиусы из конфигурации
        config = current_app.config['GAME_CONFIG']
        pickup_radius = config['pickup_radius']
        dropoff_radius = config['dropoff_radius']
        
        # Проверяем зоны
        in_pickup = is_player_at_restaurant(
            player_lat, player_lng,
            active_order.pickup_lat, active_order.pickup_lng,
            pickup_radius
        )
        
        in_dropoff = is_player_at_building(
            player_lat, player_lng,
            active_order.dropoff_lat, active_order.dropoff_lng,
            dropoff_radius
        )
        
        # Расчитываем расстояния
        distance_to_pickup = calculate_distance(
            player_lat, player_lng,
            active_order.pickup_lat, active_order.pickup_lng
        ) * 1000  # в метрах
        
        distance_to_dropoff = calculate_distance(
            player_lat, player_lng,
            active_order.dropoff_lat, active_order.dropoff_lng
        ) * 1000  # в метрах
        
        return {
            'has_active_order': True,
            'order_id': active_order.id,
            'order_status': active_order.status,
            'in_pickup_zone': in_pickup,
            'in_dropoff_zone': in_dropoff,
            'distance_to_pickup_meters': round(distance_to_pickup),
            'distance_to_dropoff_meters': round(distance_to_dropoff),
            'can_pickup': in_pickup and not active_order.pickup_time,
            'can_deliver': in_dropoff and active_order.pickup_time and not active_order.delivery_time
        }
        
    except Exception as e:
        logger.error(f"Error checking player zones: {str(e)}")
        return {'error': 'Zone check failed'}

def pickup_order(user_id: int) -> Dict:
    """
    Забор заказа игроком (когда он в зоне ресторана).
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат операции
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Проверяем, что заказ еще не забран
        if active_order.pickup_time:
            return {'success': False, 'error': 'Order already picked up'}
        
        # Выполняем pickup
        success = active_order.pickup_order()
        if success:
            logger.info(f"User {user_id} picked up order {active_order.id}")
            return {
                'success': True,
                'message': 'Order picked up successfully',
                'order': active_order.to_dict()
            }
        else:
            return {'success': False, 'error': 'Pickup failed'}
        
    except Exception as e:
        logger.error(f"Error in pickup_order: {str(e)}")
        return {'success': False, 'error': 'Pickup error'}

def deliver_order(user_id: int) -> Dict:
    """
    Доставка заказа игроком (когда он в зоне здания).
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат операции с деталями выплаты
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Проверяем, что заказ забран
        if not active_order.pickup_time:
            return {'success': False, 'error': 'Order not picked up yet'}
        
        # Проверяем, что заказ еще не доставлен
        if active_order.delivery_time:
            return {'success': False, 'error': 'Order already delivered'}
        
        # Выполняем доставку
        delivery_result = active_order.deliver_order()
        if delivery_result['success']:
            logger.info(f"User {user_id} delivered order {active_order.id}")
            return {
                'success': True,
                'message': 'Order delivered successfully',
                'delivery_result': delivery_result,
                'new_balance': user.balance,
                'order': active_order.to_dict()
            }
        else:
            return {'success': False, 'error': delivery_result.get('error', 'Delivery failed')}
        
    except Exception as e:
        logger.error(f"Error in deliver_order: {str(e)}")
        return {'success': False, 'error': 'Delivery error'}

def cancel_order(user_id: int, reason: str = 'user_cancelled') -> Dict:
    """
    Отмена заказа игроком.
    
    Args:
        user_id (int): ID пользователя
        reason (str): Причина отмены
    
    Returns:
        dict: Результат операции
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Отменяем заказ
        success = active_order.cancel_order(reason)
        if success:
            logger.info(f"User {user_id} cancelled order {active_order.id}: {reason}")
            return {
                'success': True,
                'message': 'Order cancelled successfully',
                'reason': reason
            }
        else:
            return {'success': False, 'error': 'Cannot cancel order'}
        
    except Exception as e:
        logger.error(f"Error in cancel_order: {str(e)}")
        return {'success': False, 'error': 'Cancellation error'}

def get_order_for_user(user_id: int) -> Optional["Dict"]:
    from app.models.order import Order  # локальный импорт
    """
    Генерация и создание нового заказа для пользователя.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Данные созданного заказа или None
    """
    try:
        # Генерируем заказ
        order_data = generate_random_order()
        if not order_data:
            return None
        
        # Создаем в базе
        order = create_order_for_user(user_id, order_data)
        if not order:
            return None
        
        return order.to_dict()
        
    except Exception as e:
        logger.error(f"Error getting order for user {user_id}: {str(e)}")
        return None

def validate_order_action(user_id: int, action: str) -> Dict:
    """
    Валидация возможности выполнения действия с заказом.
    
    Args:
        user_id (int): ID пользователя
        action (str): Действие (pickup, deliver, cancel)
    
    Returns:
        dict: Результат валидации
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'valid': False, 'error': 'User not found'}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'valid': False, 'error': 'No active order'}
        
        if action == 'pickup':
            if active_order.pickup_time:
                return {'valid': False, 'error': 'Order already picked up'}
            return {'valid': True}
        
        elif action == 'deliver':
            if not active_order.pickup_time:
                return {'valid': False, 'error': 'Order not picked up yet'}
            if active_order.delivery_time:
                return {'valid': False, 'error': 'Order already delivered'}
            return {'valid': True}
        
        elif action == 'cancel':
            if active_order.status in ['completed', 'cancelled']:
                return {'valid': False, 'error': 'Order already completed or cancelled'}
            return {'valid': True}
        
        else:
            return {'valid': False, 'error': 'Unknown action'}
        
    except Exception as e:
        logger.error(f"Error validating order action: {str(e)}")
        return {'valid': False, 'error': 'Validation error'}