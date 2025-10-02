# -*- coding: utf-8 -*-
"""
SocketIO обработчики игровых событий для симулятора курьера.
Обрабатывает real-time коммуникацию между сервером и клиентом.
"""

from flask_socketio import emit, disconnect, join_room, leave_room
from flask import request
import logging
import random
from app import socketio, db
from app.models import User, Order

# Настройка логирования для отслеживания событий WebSocket
logger = logging.getLogger(__name__)

# Глобальный словарь активных пользователей {session_id: user_data}
# Используется для быстрого доступа к информации о подключенных пользователях
active_users = {}


@socketio.on('connect')
def handle_connect():
    """
    Обработчик подключения клиента к WebSocket.
    Вызывается автоматически при установке соединения.
    """
    try:
        session_id = request.sid
        logger.info(f"🔌 Client connected: {session_id}")
        
        # Отправляем подтверждение подключения клиенту
        emit('connection_established', {
            'status': 'connected', 
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}", exc_info=True)


@socketio.on('disconnect')
def handle_disconnect():
    """
    Обработчик отключения клиента от WebSocket.
    Очищает данные пользователя из памяти.
    """
    try:
        session_id = request.sid
        logger.info(f"🔌 Client disconnected: {session_id}")
        
        # Удаляем пользователя из списка активных при отключении
        if session_id in active_users:
            user_data = active_users[session_id]
            logger.info(f"Removed user {user_data.get('user_id')} from active users")
            del active_users[session_id]
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}", exc_info=True)


@socketio.on('user_login')
def handle_user_login(data):
    """
    Обработчик логина пользователя через WebSocket.
    Регистрирует пользователя в системе real-time коммуникации.
    
    Args:
        data (dict): Данные с user_id от клиента
    """
    try:
        session_id = request.sid
        user_id = data.get('user_id')
        
        # Валидация входных данных
        if not user_id:
            emit('error', {'message': 'User ID is required'})
            return
        
        logger.info(f"👤 User {user_id} logged in via WebSocket (session: {session_id})")
        
        # Сохраняем данные пользователя в памяти для быстрого доступа
        active_users[session_id] = {
            'user_id': user_id,
            'username': f'User_{user_id}',
            'rooms': [f'user_{user_id}']
        }
        
        # Добавляем пользователя в персональную комнату для таргетированных сообщений
        join_room(f'user_{user_id}')
        
        # Подтверждаем успешный логин
        emit('login_success', {
            'user_id': user_id, 
            'message': 'Login successful'
        })
    except Exception as e:
        logger.error(f"Error in user_login handler: {str(e)}", exc_info=True)
        emit('error', {'message': 'Login failed'})


@socketio.on('start_order_search')
def handle_start_order_search(data):
    """
    Обработчик начала поиска заказов.
    Запускает процесс симуляции поиска и генерации заказа.
    
    Args:
        data (dict): Параметры поиска (radius_km)
    """
    try:
        session_id = request.sid
        
        # Проверяем, что пользователь аутентифицирован
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        radius_km = data.get('radius_km', 5)  # По умолчанию 5 км радиус поиска
        
        logger.info(f"🔍 User {user_id} started order search (radius: {radius_km}km)")
        
        # Создаем комнату для поиска заказов для отправки прогресса
        search_room = f'order_search_{user_id}'
        join_room(search_room)
        user_data['rooms'].append(search_room)
        
        # Подтверждаем начало поиска ПЕРЕД симуляцией
        emit('search_started', {
            'status': 'searching', 
            'radius_km': radius_km
        })
        
        # Запускаем симуляцию поиска (синхронная версия с socketio.sleep)
        simulate_order_search_sync(user_id, radius_km)
        
    except Exception as e:
        logger.error(f"Error in start order search: {str(e)}", exc_info=True)
        emit('error', {'message': 'Failed to start order search'})


def simulate_order_search_sync(user_id: int, radius_km: float):
    """
    Синхронная симуляция поиска заказов с прогресс-баром.
    Использует socketio.sleep для совместимости с eventlet/gevent.
    
    Args:
        user_id (int): ID пользователя
        radius_km (float): Радиус поиска заказов
    """
    try:
        # Случайное время поиска от 5 до 15 секунд (имитация реального поиска)
        search_time = random.randint(5, 15)
        
        # Отправляем прогресс поиска каждую секунду
        for i in range(search_time):
            socketio.sleep(1)  # Используем socketio.sleep вместо time.sleep
            
            # Отправляем обновление прогресса в комнату пользователя
            socketio.emit('search_progress', {
                'elapsed': i + 1,
                'total': search_time,
                'percentage': round(((i + 1) / search_time) * 100)
            }, room=f'order_search_{user_id}')
        
        # После завершения поиска генерируем заказ
        generate_order_for_user(user_id)
        
    except Exception as e:
        logger.error(f"Error in sync order search for user {user_id}: {str(e)}", exc_info=True)
        socketio.emit('error', {
            'message': 'Order search failed'
        }, room=f'order_search_{user_id}')


def generate_order_for_user(user_id: int):
    """
    Генерация и отправка заказа пользователю через WebSocket.
    Вызывается после завершения симуляции поиска.
    
    Args:
        user_id (int): ID пользователя для генерации заказа
    """
    try:
        from app.utils.game_helper import get_order_for_user
        
        logger.info(f"📦 Generating order for user {user_id}")
        
        # Генерируем новый заказ через игровую логику
        order = get_order_for_user(user_id)
        
        if order:
            logger.info(f"✅ Order {order.get('id')} created for user {user_id}")
            logger.debug(f"Order details: {order.get('pickup_name')} → {order.get('dropoff_address')}")
            
            # Отправляем заказ в комнату пользователя
            socketio.emit("order_found", {
                "success": True,
                "order": order
            }, room=f"order_search_{user_id}")
            
            logger.info(f"📤 Order sent to frontend for user {user_id}")
        else:
            # Если не удалось сгенерировать заказ (нет доступных ресторанов/зданий)
            logger.warning(f"❌ No order generated for user {user_id}")
            socketio.emit("no_orders_found", {
                "message": "No orders available in your area. Try again later."
            }, room=f"order_search_{user_id}")
            
    except Exception as e:
        logger.error(f"Error generating order for user {user_id}: {str(e)}", exc_info=True)
        socketio.emit("error", {
            "message": "Failed to generate order"
        }, room=f"order_search_{user_id}")


@socketio.on('stop_order_search')
def handle_stop_order_search():
    """
    Обработчик остановки поиска заказов пользователем.
    Позволяет пользователю отменить поиск до его завершения.
    """
    try:
        session_id = request.sid
        
        # Проверяем аутентификацию
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        logger.info(f"🛑 User {user_id} stopped order search")
        
        # Выходим из комнаты поиска
        search_room = f'order_search_{user_id}'
        leave_room(search_room)
        
        # Удаляем комнату из списка комнат пользователя
        if search_room in user_data['rooms']:
            user_data['rooms'].remove(search_room)
        
        # Подтверждаем остановку поиска
        emit('search_stopped', {
            'status': 'stopped',
            'message': 'Order search cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error stopping order search: {str(e)}", exc_info=True)
        emit('error', {'message': 'Failed to stop order search'})


@socketio.on('update_position')
def handle_position_update(data):
    """
    Обработчик обновления позиции игрока в реальном времени.
    Принимает GPS координаты и обновляет состояние на сервере.
    
    Args:
        data (dict): Координаты игрока (lat, lng, accuracy, timestamp)
    """
    try:
        session_id = request.sid
        
        # Проверяем аутентификацию
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        
        # Извлекаем данные позиции
        lat = data.get('lat')
        lng = data.get('lng')
        accuracy = data.get('accuracy', 999)
        
        # Валидация координат
        if lat is None or lng is None:
            emit('error', {'message': 'Invalid position data'})
            return
        
        # Обновляем позицию пользователя в базе данных
        user = User.query.get(user_id)
        if user:
            user.update_position(lat, lng)
        
        # Проверяем зоны заказа (pickup/dropoff) если есть активный заказ
        from app.utils.game_helper import check_player_zones
        zones_status = check_player_zones(user_id, lat, lng)
        
        # Отправляем обратно статус зон для UI
        emit('position_updated', {
            'success': True,
            'zones': zones_status,
            'accuracy': accuracy
        })
        
        logger.debug(f"📍 Position updated for user {user_id}: ({lat:.6f}, {lng:.6f})")
        
    except Exception as e:
        logger.error(f"Error updating position: {str(e)}", exc_info=True)
        emit('error', {'message': 'Failed to update position'})