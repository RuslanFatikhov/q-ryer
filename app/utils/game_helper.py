# -*- coding: utf-8 -*-
"""
Основная игровая логика для симулятора курьера.
Генерация заказов, проверка зон, завершение доставки.
"""

import logging
from typing import Dict, Optional
from flask import current_app
from app.utils.restaurant_helper import get_random_restaurant, is_player_at_restaurant
from app.utils.building_helper import get_random_building_for_delivery, is_player_at_building
from app.utils.economy import calculate_delivery_stats
from app.utils.gps_helper import calculate_distance
from app.models.user import User
from app import db

# Настройка логирования
logger = logging.getLogger(__name__)


def generate_random_order() -> Optional[Dict]:
    """
    Генерация случайного заказа: ресторан → здание.
    
    Returns:
        dict: Данные нового заказа или None, если не удалось сгенерировать
        
    Raises:
        Exception: При критических ошибках генерации
    """
    try:
        # Получаем случайный ресторан из базы данных
        restaurant = get_random_restaurant()
        if not restaurant:
            logger.error("No restaurants available for order generation")
            return None
        
        # Получаем подходящее здание для доставки в радиусе от ресторана
        building = get_random_building_for_delivery(
            restaurant['lat'], 
            restaurant['lng']
        )
        if not building:
            logger.error(f"No suitable buildings found for delivery from {restaurant['name']}")
            return None
        
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
        # Один пользователь = один активный заказ (бизнес-логика)
        active_order = user.get_active_order()
        if active_order:
            logger.warning(f"User {user_id} already has active order {active_order.id}, cannot create new")
            return None
        
        # Создаем новый заказ со всеми необходимыми полями
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
        
        # Сохраняем в базу данных
        db.session.add(order)
        db.session.commit()
        
        logger.info(f"Created order {order.id} for user {user_id}: {order.pickup_name} → {order.dropoff_address}")
        return order
        
    except Exception as e:
        logger.error(f"Error creating order for user {user_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return None


def check_player_zones(user_id: int, player_lat: float, player_lng: float) -> Dict:
    """
    Проверка, в каких игровых зонах находится игрок (pickup/dropoff).
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
    Вызывается когда игрок находится в зоне pickup и нажимает "Забрать заказ".
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат операции с обновленными данными заказа
    """
    try:
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Проверяем, что заказ еще не забран (защита от дублирования)
        if active_order.pickup_time:
            return {'success': False, 'error': 'Order already picked up'}
        
        # Выполняем pickup - устанавливаем время забора и запускаем таймер доставки
        success = active_order.pickup_order()
        if success:
            logger.info(f"User {user_id} picked up order {active_order.id} from {active_order.pickup_name}")
            return {
                'success': True,
                'message': 'Order picked up successfully',
                'order': active_order.to_dict()
            }
        else:
            return {'success': False, 'error': 'Pickup failed - order may be expired or invalid'}
        
    except Exception as e:
        logger.error(f"Error in pickup_order for user {user_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': 'Pickup error occurred'}


def deliver_order(user_id: int) -> Dict:
    """
    Доставка заказа игроком клиенту.
    Вызывается когда игрок в зоне dropoff и нажимает "Доставить заказ".
    Начисляет деньги и бонусы за своевременность.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Результат с деталями выплаты, бонусами и обновленным балансом
    """
    try:
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order'}
        
        # Проверяем, что заказ был забран (есть pickup_time)
        if not active_order.pickup_time:
            return {'success': False, 'error': 'Order not picked up yet'}
        
        # Проверяем, что заказ еще не доставлен (защита от дублирования)
        if active_order.delivery_time:
            return {'success': False, 'error': 'Order already delivered'}
        
        # Выполняем доставку - рассчитываем выплату, проверяем бонус за время
        delivery_result = active_order.deliver_order()
        if delivery_result['success']:
            logger.info(
                f"User {user_id} delivered order {active_order.id}. "
                f"Payout: ${delivery_result['payout']['total']}, "
                f"On time: {delivery_result['on_time']}"
            )
            return {
                'success': True,
                'message': 'Order delivered successfully',
                'delivery_result': delivery_result,
                'new_balance': round(user.balance, 2),
                'order': active_order.to_dict()
            }
        else:
            return {'success': False, 'error': delivery_result.get('error', 'Delivery failed')}
        
    except Exception as e:
        logger.error(f"Error in deliver_order for user {user_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': 'Delivery error occurred'}


def cancel_order(user_id: int, reason: str = 'user_cancelled') -> Dict:
    """
    Отмена заказа игроком.
    Может быть вызвана пользователем или автоматически при истечении времени.
    
    Args:
        user_id (int): ID пользователя
        reason (str): Причина отмены (user_cancelled, expired, shift_ended и т.д.)
    
    Returns:
        dict: Результат операции отмены
    """
    try:
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        if not active_order:
            return {'success': False, 'error': 'No active order to cancel'}
        
        # Отменяем заказ с указанием причины
        success = active_order.cancel_order(reason)
        if success:
            logger.info(f"User {user_id} cancelled order {active_order.id}. Reason: {reason}")
            return {
                'success': True,
                'message': 'Order cancelled successfully',
                'reason': reason
            }
        else:
            return {'success': False, 'error': 'Cannot cancel order - it may already be completed'}
        
    except Exception as e:
        logger.error(f"Error in cancel_order for user {user_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': 'Cancellation error occurred'}


def get_order_for_user(user_id: int) -> Optional[Dict]:
    """
    Генерация и создание нового заказа для пользователя.
    Единая точка входа для получения заказа - сначала генерирует, потом создает в БД.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Данные созданного заказа в формате для фронтенда или None
    """
    try:
        # Генерируем случайный заказ
        order_data = generate_random_order()
        if not order_data:
            logger.warning(f"Failed to generate order for user {user_id} - no suitable restaurants/buildings")
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
        
        # Валидация для принятия нового заказа
        if action == 'accept':
            if active_order:
                return {
                    'valid': False, 
                    'error': 'User already has an active order',
                    'active_order_id': active_order.id
                }
            return {'valid': True}
        
        # Для остальных действий требуется наличие активного заказа
        if not active_order:
            return {'valid': False, 'error': 'No active order'}
        
        # Валидация для забора заказа из ресторана
        if action == 'pickup':
            if active_order.pickup_time:
                return {'valid': False, 'error': 'Order already picked up'}
            if active_order.is_expired():
                return {'valid': False, 'error': 'Order has expired'}
            return {'valid': True}
        
        # Валидация для доставки заказа клиенту
        elif action == 'deliver':
            if not active_order.pickup_time:
                return {'valid': False, 'error': 'Order not picked up yet'}
            if active_order.delivery_time:
                return {'valid': False, 'error': 'Order already delivered'}
            return {'valid': True}
        
        # Валидация для отмены заказа
        elif action == 'cancel':
            if active_order.status in ['completed', 'cancelled']:
                return {
                    'valid': False, 
                    'error': f'Order already {active_order.status}'
                }
            return {'valid': True}
        
        # Неизвестное действие
        else:
            return {'valid': False, 'error': f'Unknown action: {action}'}
        
    except Exception as e:
        logger.error(f"Error validating order action '{action}' for user {user_id}: {str(e)}", exc_info=True)
        return {'valid': False, 'error': 'Validation error occurred'}