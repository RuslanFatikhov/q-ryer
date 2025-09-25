# -*- coding: utf-8 -*-
"""
SocketIO обработчики игровых событий для симулятора курьера.
Обрабатывает события в реальном времени: подключения, обновления позиции, статусы заказов.
"""

from flask_socketio import emit, disconnect, join_room, leave_room
from flask import request
import logging
from app import socketio, db
from app.models import User, Order
from app.utils.gps_helper import is_within_radius, calculate_distance_meters

# Настройка логирования
logger = logging.getLogger(__name__)

# Словарь активных пользователей {session_id: user_data}
active_users = {}

@socketio.on('connect')
def handle_connect():
    """
    Обработчик подключения клиента к WebSocket.
    """
    try:
        session_id = request.sid
        logger.info(f"Client connected: {session_id}")
        
        # Отправляем подтверждение подключения
        emit('connection_established', {
            'status': 'connected',
            'session_id': session_id,
            'message': 'Successfully connected to courier simulator'
        })
        
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}")
        emit('error', {'message': 'Connection error'})

@socketio.on('disconnect')
def handle_disconnect():
    """
    Обработчик отключения клиента от WebSocket.
    """
    try:
        session_id = request.sid
        logger.info(f"Client disconnected: {session_id}")
        
        # Убираем пользователя из активных
        if session_id in active_users:
            user_data = active_users[session_id]
            user_id = user_data.get('user_id')
            
            if user_id:
                # Обновляем статус пользователя в базе
                user = User.query.get(user_id)
                if user:
                    user.set_online_status(False)
                    logger.info(f"User {user.username} set offline")
            
            # Покидаем комнаты
            if 'rooms' in user_data:
                for room in user_data['rooms']:
                    leave_room(room)
            
            del active_users[session_id]
        
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}")

@socketio.on('user_login')
def handle_user_login(data):
    """
    Обработчик входа пользователя в систему.
    
    Args:
        data (dict): Данные пользователя {'user_id': int}
    """
    try:
        session_id = request.sid
        user_id = data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User ID is required'})
            return
        
        # Получаем пользователя из базы
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
        
        # Сохраняем информацию о пользователе
        active_users[session_id] = {
            'user_id': user_id,
            'username': user.username,
            'rooms': [f'user_{user_id}'],
            'last_position': None,
            'active_order_id': None
        }
        
        # Устанавливаем статус онлайн
        user.set_online_status(True)
        
        # Присоединяемся к персональной комнате
        join_room(f'user_{user_id}')
        
        logger.info(f"User {user.username} logged in (session: {session_id})")
        
        # Отправляем подтверждение
        emit('login_success', {
            'user': user.to_dict(),
            'active_order': user.get_active_order().to_dict() if user.get_active_order() else None
        })
        
    except Exception as e:
        logger.error(f"Error in user_login handler: {str(e)}")
        emit('error', {'message': 'Login error'})

@socketio.on('update_position')
def handle_position_update(data):
    """
    Обработчик обновления позиции пользователя.
    
    Args:
        data (dict): Позиция {'lat': float, 'lng': float, 'accuracy': float}
    """
    try:
        session_id = request.sid
        
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        lat = data.get('lat')
        lng = data.get('lng')
        accuracy = data.get('accuracy', 999)
        
        if not lat or not lng:
            emit('error', {'message': 'Invalid coordinates'})
            return
        
        # Проверяем точность GPS
        if accuracy > 100:  # Слишком неточно
            emit('gps_warning', {
                'message': 'GPS точность низкая',
                'accuracy': accuracy,
                'recommendation': 'Попробуйте выйти на открытую местность'
            })
        
        # Обновляем позицию в базе данных
        user = User.query.get(user_id)
        if user:
            user.update_position(lat, lng)
        
        # Сохраняем позицию в памяти
        user_data['last_position'] = {
            'lat': lat,
            'lng': lng,
            'accuracy': accuracy,
            'timestamp': db.func.now()
        }
        
        # Проверяем активные заказы
        active_order = user.get_active_order()
        if active_order:
            check_order_zones(user_id, lat, lng, active_order)
        
        # Подтверждаем обновление позиции
        emit('position_updated', {
            'lat': lat,
            'lng': lng,
            'accuracy': accuracy
        })
        
    except Exception as e:
        logger.error(f"Error in position update handler: {str(e)}")
        emit('error', {'message': 'Position update error'})

@socketio.on('start_order_search')
def handle_start_order_search(data):
    """
    Обработчик начала поиска заказов.
    
    Args:
        data (dict): Параметры поиска {'radius_km': float}
    """
    try:
        session_id = request.sid
        
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        # Проверяем, что у пользователя нет активного заказа
        user = User.query.get(user_id)
        if user.get_active_order():
            emit('error', {'message': 'You already have an active order'})
            return
        
        # Проверяем последнюю позицию
        if not user_data.get('last_position'):
            emit('error', {'message': 'Position not available'})
            return
        
        last_pos = user_data['last_position']
        radius_km = data.get('radius_km', 5)
        
        logger.info(f"User {user_id} started order search (radius: {radius_km}km)")
        
        # Присоединяемся к комнате поиска заказов
        search_room = f'order_search_{user_id}'
        join_room(search_room)
        user_data['rooms'].append(search_room)
        
        # Запускаем поиск заказов
        start_order_search_process(user_id, last_pos['lat'], last_pos['lng'], radius_km)
        
        emit('search_started', {
            'status': 'searching',
            'radius_km': radius_km,
            'position': last_pos
        })
        
    except Exception as e:
        logger.error(f"Error in start order search handler: {str(e)}")
        emit('error', {'message': 'Order search error'})

@socketio.on('stop_order_search')
def handle_stop_order_search():
    """
    Обработчик остановки поиска заказов.
    """
    try:
        session_id = request.sid
        
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        # Покидаем комнату поиска
        search_room = f'order_search_{user_id}'
        leave_room(search_room)
        if search_room in user_data['rooms']:
            user_data['rooms'].remove(search_room)
        
        logger.info(f"User {user_id} stopped order search")
        
        emit('search_stopped', {'status': 'idle'})
        
    except Exception as e:
        logger.error(f"Error in stop order search handler: {str(e)}")
        emit('error', {'message': 'Stop search error'})

@socketio.on('order_action')
def handle_order_action(data):
    """
    Обработчик действий с заказом (принять, забрать, доставить, отменить).
    
    Args:
        data (dict): Действие {'action': str, 'order_id': int, 'reason': str}
    """
    try:
        session_id = request.sid
        
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        action = data.get('action')
        order_id = data.get('order_id')
        
        if not action or not order_id:
            emit('error', {'message': 'Action and order_id are required'})
            return
        
        order = Order.query.get(order_id)
        if not order:
            emit('error', {'message': 'Order not found'})
            return
        
        # Обрабатываем различные действия
        result = process_order_action(user_id, order, action, data)
        
        if result['success']:
            emit('order_action_success', result)
            
            # Уведомляем других участников если нужно
            broadcast_order_update(order)
        else:
            emit('order_action_error', result)
        
    except Exception as e:
        logger.error(f"Error in order action handler: {str(e)}")
        emit('error', {'message': 'Order action error'})

def check_order_zones(user_id: int, lat: float, lng: float, order):
    """
    Проверка нахождения пользователя в зонах pickup/dropoff.
    
    Args:
        user_id (int): ID пользователя
        lat (float): Широта пользователя
        lng (float): Долгота пользователя
        order: Активный заказ
    """
    try:
        from flask import current_app
        config = current_app.config['GAME_CONFIG']
        
        pickup_radius = config['pickup_radius']
        dropoff_radius = config['dropoff_radius']
        
        # Проверяем зону pickup
        in_pickup = is_within_radius(
            order.pickup_lat, order.pickup_lng,
            lat, lng, pickup_radius
        )
        
        # Проверяем зону dropoff  
        in_dropoff = is_within_radius(
            order.dropoff_lat, order.dropoff_lng,
            lat, lng, dropoff_radius
        )
        
        # Отправляем обновление зон
        socketio.emit('zone_status_update', {
            'order_id': order.id,
            'in_pickup_zone': in_pickup,
            'in_dropoff_zone': in_dropoff,
            'pickup_distance': calculate_distance_meters(
                lat, lng, order.pickup_lat, order.pickup_lng
            ),
            'dropoff_distance': calculate_distance_meters(
                lat, lng, order.dropoff_lat, order.dropoff_lng
            )
        }, room=f'user_{user_id}')
        
    except Exception as e:
        logger.error(f"Error checking order zones: {str(e)}")

def start_order_search_process(user_id: int, lat: float, lng: float, radius_km: float):
    """
    Запуск процесса поиска заказов для пользователя.
    
    Args:
        user_id (int): ID пользователя
        lat (float): Широта пользователя
        lng (float): Долгота пользователя
        radius_km (float): Радиус поиска
    """
    import threading
    import time
    import random
    
    def search_orders():
        try:
            # Имитируем поиск заказов (5-30 секунд)
            search_time = random.randint(5, 30)
            
            for i in range(search_time):
                time.sleep(1)
                
                # Проверяем, что пользователь все еще ищет
                if f'order_search_{user_id}' not in [room for session_data in active_users.values() 
                                                   for room in session_data.get('rooms', [])]:
                    return
                
                # Отправляем прогресс поиска
                socketio.emit('search_progress', {
                    'elapsed': i + 1,
                    'total': search_time
                }, room=f'order_search_{user_id}')
            
            # Генерируем заказ или сообщаем об отсутствии
            if random.random() > 0.3:  # 70% шанс найти заказ
                generate_order_for_user(user_id, lat, lng)
            else:
                socketio.emit('no_orders_found', {
                    'message': 'No orders available in your area',
                    'retry_suggested': True
                }, room=f'order_search_{user_id}')
            
        except Exception as e:
            logger.error(f"Error in order search process: {str(e)}")
            socketio.emit('search_error', {
                'message': 'Error during order search'
            }, room=f'order_search_{user_id}')
    
    # Запускаем поиск в отдельном потоке
    search_thread = threading.Thread(target=search_orders)
    search_thread.daemon = True
    search_thread.start()


def generate_order_for_user(user_id: int, user_lat: float, user_lng: float):
    """
    Генерация заказа для пользователя.
    
    Args:
        user_id (int): ID пользователя
        user_lat (float): Широта пользователя
        user_lng (float): Долгота пользователя
    """
    try:
        from app.utils.game_helper import get_order_for_user
        
        # Генерируем заказ
        order = get_order_for_user(user_id)
        
        if order:
            # Отправляем заказ пользователю
            socketio.emit('order_found', {
                'success': True,
                'order': order
            }, room=f'order_search_{user_id}')
        else:
            # Заказов нет
            socketio.emit('no_orders_found', {
                'message': 'No orders available in your area',
                'retry_suggested': True
            }, room=f'order_search_{user_id}')
        
    except Exception as e:
        logger.error(f"Error generating order: {str(e)}")
        socketio.emit('search_error', {
            'message': 'Error during order generation'
        }, room=f'order_search_{user_id}')

def process_order_action(user_id: int, order, action: str, data: dict) -> dict:
    """
    Обработка действий с заказом.
    
    Args:
        user_id (int): ID пользователя
        order: Объект заказа
        action (str): Действие
        data (dict): Дополнительные данные
    
    Returns:
        dict: Результат действия
    """
    try:
        from app.utils.game_helper import pickup_order, deliver_order, cancel_order
        
        if action == 'pickup':
            return pickup_order(user_id)
            
        elif action == 'deliver':
            return deliver_order(user_id)
            
        elif action == 'cancel':
            reason = data.get('reason', 'user_cancelled')
            return cancel_order(user_id, reason)
            
        else:
            return {'success': False, 'error': 'Unknown action'}
    
    except Exception as e:
        logger.error(f"Error processing order action: {str(e)}")
        return {'success': False, 'error': 'Action processing failed'}

def broadcast_order_update(order):
    """
    Рассылка обновления заказа заинтересованным участникам.
    
    Args:
        order: Объект заказа
    """
    try:
        if order.user_id:
            # Отправляем обновление пользователю
            socketio.emit('order_update', {
                'order': order.to_dict()
            }, room=f'user_{order.user_id}')
    
    except Exception as e:
        logger.error(f"Error broadcasting order update: {str(e)}")