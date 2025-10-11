from app.utils.city_helper import detect_city_by_location
# -*- coding: utf-8 -*-
"""
Игровая логика для симулятора курьера.
Функции для работы с заказами: генерация, принятие, забор, доставка.
"""

import logging
from typing import Dict, Optional

from app import db
from app.models.user import User
from app.utils.economy import calculate_payout, calculate_timer
from app.utils.gps_helper import calculate_distance
from app.utils.restaurant_helper import get_restaurants_near_location
from app.utils.building_helper import get_random_building_for_delivery, load_buildings_data, get_random_building_within_game_radius

logger = logging.getLogger(__name__)


def generate_random_order(user_lat: float, user_lng: float, radius_km: int = 5, city_id: Optional[str] = None) -> Optional[Dict]:
    from app.utils.city_helper import detect_city_by_location
    if city_id is None:
        city_id = detect_city_by_location(user_lat, user_lng) or 'almaty'
    """
    Генерация случайного заказа на основе местоположения игрока.
    Выбирает ресторан и здание для доставки в указанном радиусе.
    
    Args:
        user_lat (float): Широта игрока
        user_lng (float): Долгота игрока
        radius_km (int): Радиус поиска в км
        city_id (str): ID города для генерации заказа
        user_lat (float): Широта игрока
        user_lng (float): Долгота игрока
        radius_km (int): Радиус поиска в км
    
    Returns:
        Optional[Dict]: Данные заказа или None если не удалось создать
    """
    try:
        # Получаем рестораны рядом с игроком
        nearby_restaurants = get_restaurants_near_location(user_lat, user_lng, radius_km, city_id=city_id)
        
        if not nearby_restaurants:
            logger.warning(f"No restaurants found within {radius_km} km radius")
            return None
        
        # Берем ближайший ресторан
        pickup_restaurant = nearby_restaurants[0]
        
        # Получаем случайное здание для доставки с проверкой радиуса от игрока И от ресторана
        dropoff_building = get_random_building_within_game_radius(
            player_lat=user_lat, 
            player_lng=user_lng,
            pickup_lat=pickup_restaurant["lat"], 
            pickup_lng=pickup_restaurant["lng"],
            player_radius_km=radius_km,
            min_distance_from_pickup_km=0.5,
            max_distance_from_pickup_km=5.0,
            city_id=city_id
        )
        
        
        if not dropoff_building:
            logger.warning("No suitable building found within player radius")
            return None
        
        # Получаем расстояние доставки
        delivery_distance = dropoff_building.get("delivery_distance_km",
            calculate_distance(
                pickup_restaurant["lat"], pickup_restaurant["lng"],
                dropoff_building["lat"], dropoff_building["lng"]
            ))
        
        # Расчет параметров заказа
        payout = calculate_payout(delivery_distance)
        timer_seconds = calculate_timer(delivery_distance)
        
        order_data = {
            'pickup': {
                'name': pickup_restaurant['name'],
                'lat': pickup_restaurant['lat'],
                'lng': pickup_restaurant['lng']
            },
            'dropoff': {
                'address': dropoff_building['address'],
                'lat': dropoff_building['lat'],
                'lng': dropoff_building['lng']
            },
            'distance_km': round(delivery_distance, 2),
            'amount': round(payout, 2),
            'timer_seconds': timer_seconds,
            'estimated_minutes': timer_seconds // 60
        }
        
        logger.info(
            f"Generated order: {pickup_restaurant['name']} → {dropoff_building['address']}, "
            f"distance: {delivery_distance:.2f} km, payout: ${payout:.2f}"
        )
        
        return order_data
        
    except Exception as e:
        logger.error(f"Error generating order: {str(e)}", exc_info=True)
        return None


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
    Доставка заказа игроком к клиенту.
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
        # ВАЖНО: метод deliver_order() в модели Order УЖЕ обновляет баланс и счетчик доставок
        delivery_result = active_order.deliver_order()
        
        if delivery_result['success']:
            # Получаем обновленный баланс пользователя (уже обновлен в deliver_order)
            db.session.refresh(user)
            
            logger.info(
                f"User {user_id} delivered order {active_order.id}. "
                f"Payout: ${delivery_result['payout']['total']}, "
                f"On time: {delivery_result['on_time']}"
            )
            
            return {
                'success': True,
                'message': 'Order delivered successfully',
                'delivery_result': delivery_result,
                'payout': delivery_result['payout']['total'],
                'new_balance': round(user.balance, 2),
                'order': active_order.to_dict()
            }
        else:
            return {'success': False, 'error': delivery_result.get('error', 'Delivery failed')}
        
    except Exception as e:
        logger.error(f"Error in deliver_order for user {user_id}: {str(e)}", exc_info=True)
        db.session.rollback()
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
    Единая точка входа: проверяем активный заказ, определяем город по координатам,
    генерируем заказ и сохраняем в БД.
    """
    from app.models.order import Order

    try:
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None

        # Если активный заказ уже есть — просто вернуть его
        existing_order = user.get_active_order()
        if existing_order:
            logger.warning(f"User {user_id} already has an active order")
            return existing_order.to_dict()
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}", exc_info=True)
        return None

    # Координаты игрока (последние известные или поля пользователя)
    _ulat = (
        getattr(user, 'last_position_lat', None)
        or getattr(user, 'lat', None)
        or getattr(user, 'latitude', None)
    )
    _ulng = (
        getattr(user, 'last_position_lng', None)
        or getattr(user, 'lng', None)
        or getattr(user, 'longitude', None)
    )

    # Определяем city_id по координатам, fallback — город из БД, затем 'almaty'
    city_id = (detect_city_by_location(_ulat, _ulng) if (_ulat is not None and _ulng is not None) else None)               or getattr(user, 'city_id', None)               or 'almaty'
    logger.info(f"User {user_id} city_id resolved: {city_id}")

    # Генерируем заказ в найденном городе (важно: прокидываем city_id)
    order_data = generate_random_order(
        _ulat, _ulng,
        radius_km=user.search_radius_km,
        city_id=city_id
    )
    if not order_data:
        logger.warning(f"No orders available for user {user_id}")
        return None

    # Создаём заказ в БД
    new_order = Order(
        user_id=user_id,
        pickup_lat=order_data['pickup']['lat'],
        pickup_lng=order_data['pickup']['lng'],
        pickup_name=order_data['pickup']['name'],
        dropoff_lat=order_data['dropoff']['lat'],
        dropoff_lng=order_data['dropoff']['lng'],
        dropoff_address=order_data['dropoff']['address'],
        distance_km=order_data['distance_km'],
        amount=order_data['amount'],
        timer_seconds=order_data['timer_seconds'],
        status='pending'
    )
    db.session.add(new_order)
    db.session.commit()
    logger.info(f"Created order {new_order.id} for user {user_id} in city {city_id}")
    return new_order.to_dict()

def check_player_zones(user_id: int, lat: float, lng: float) -> Dict:
    """
    Проверка, находится ли игрок в зонах pickup или dropoff.
    
    Args:
        user_id (int): ID пользователя
        lat (float): Широта игрока
        lng (float): Долгота игрока
    
    Returns:
        dict: Статус нахождения в зонах
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'has_active_order': False}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'has_active_order': False}
        
        from app.config import Config
        config = Config.GAME_CONFIG
        pickup_radius = config.get('pickup_radius', 30)
        dropoff_radius = config.get('dropoff_radius', 30)
        
        # Проверяем расстояние до pickup
        distance_to_pickup = calculate_distance(
            lat, lng,
            active_order.pickup_lat, active_order.pickup_lng
        ) * 1000  # переводим в метры
        
        # Проверяем расстояние до dropoff
        distance_to_dropoff = calculate_distance(
            lat, lng,
            active_order.dropoff_lat, active_order.dropoff_lng
        ) * 1000  # переводим в метры
        
        in_pickup_zone = distance_to_pickup <= pickup_radius
        in_dropoff_zone = distance_to_dropoff <= dropoff_radius
        
        # Можно ли забрать заказ (в зоне pickup и еще не забран)
        can_pickup = in_pickup_zone and not active_order.pickup_time
        
        # Можно ли доставить (в зоне dropoff и уже забран)
        can_deliver = in_dropoff_zone and active_order.pickup_time is not None
        
        return {
            'has_active_order': True,
            'order_id': active_order.id,
            'in_pickup_zone': in_pickup_zone,
            'in_dropoff_zone': in_dropoff_zone,
            'can_pickup': can_pickup,
            'can_deliver': can_deliver,
            'distance_to_pickup_meters': round(distance_to_pickup, 1),
            'distance_to_dropoff_meters': round(distance_to_dropoff, 1)
        }
        
    except Exception as e:
        logger.error(f"Error checking player zones: {str(e)}", exc_info=True)
        return {'has_active_order': False, 'error': str(e)}


def validate_order_action(user_id: int, action: str) -> Dict:
    """
    Валидация возможности выполнения действия с заказом.
    
    Args:
        user_id (int): ID пользователя
        action (str): Действие (pickup, deliver, cancel)
    
    Returns:
        dict: Результат валидации с флагом valid
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'valid': False, 'error': 'User not found'}
        
        active_order = user.get_active_order()
        if not active_order:
            return {'valid': False, 'error': 'No active order'}
        
        if action == 'pickup':
            # Проверяем, что заказ еще не забран
            if active_order.pickup_time:
                return {'valid': False, 'error': 'Order already picked up'}
            
            # Проверяем, что заказ не истек
            if active_order.is_expired():
                return {'valid': False, 'error': 'Order has expired'}
            
            return {'valid': True}
        
        elif action == 'deliver':
            # Проверяем, что заказ был забран
            if not active_order.pickup_time:
                return {'valid': False, 'error': 'Order not picked up yet'}
            
            # Проверяем, что заказ еще не доставлен
            if active_order.delivery_time:
                return {'valid': False, 'error': 'Order already delivered'}
            
            return {'valid': True}
        
        elif action == 'cancel':
            # Проверяем, что заказ еще не завершен
            if active_order.status == 'completed':
                return {'valid': False, 'error': 'Cannot cancel completed order'}
            
            return {'valid': True}
        
        else:
            return {'valid': False, 'error': f'Unknown action: {action}'}
        
    except Exception as e:
        logger.error(f"Error validating order action: {str(e)}", exc_info=True)
        return {'valid': False, 'error': 'Validation error'}