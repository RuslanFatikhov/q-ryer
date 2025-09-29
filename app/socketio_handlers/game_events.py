# -*- coding: utf-8 -*-
"""
SocketIO обработчики игровых событий для симулятора курьера.
"""

from flask_socketio import emit, disconnect, join_room, leave_room
from flask import request
import logging
import threading
import time
import random
from app import socketio, db
from app.models import User, Order

logger = logging.getLogger(__name__)
active_users = {}

@socketio.on('connect')
def handle_connect():
    try:
        session_id = request.sid
        logger.info(f"Client connected: {session_id}")
        emit('connection_established', {'status': 'connected', 'session_id': session_id})
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    try:
        session_id = request.sid
        logger.info(f"Client disconnected: {session_id}")
        if session_id in active_users:
            del active_users[session_id]
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}")

@socketio.on('user_login')
def handle_user_login(data):
    try:
        session_id = request.sid
        user_id = data.get('user_id')
        if not user_id:
            emit('error', {'message': 'User ID is required'})
            return
        
        logger.info(f"User {user_id} logged in (session: {session_id})")
        active_users[session_id] = {
            'user_id': user_id,
            'username': f'User_{user_id}',
            'rooms': [f'user_{user_id}']
        }
        join_room(f'user_{user_id}')
        emit('login_success', {'user_id': user_id, 'message': 'Login successful'})
    except Exception as e:
        logger.error(f"Error in user_login handler: {str(e)}")

@socketio.on('start_order_search')
def handle_start_order_search(data):
    try:
        session_id = request.sid
        if session_id not in active_users:
            emit('error', {'message': 'User not authenticated'})
            return
        
        user_data = active_users[session_id]
        user_id = user_data['user_id']
        radius_km = data.get('radius_km', 5)
        
        logger.info(f"User {user_id} started order search (radius: {radius_km}km)")
        
        search_room = f'order_search_{user_id}'
        join_room(search_room)
        user_data['rooms'].append(search_room)
        
        # Запускаем поиск в том же потоке
        simulate_order_search_sync(user_id, radius_km)        
        emit('search_started', {'status': 'searching', 'radius_km': radius_km})
    except Exception as e:
        logger.error(f"Error in start order search: {str(e)}")

def simulate_order_search(user_id, radius_km):
    try:
        search_time = random.randint(5, 15)
        for i in range(search_time):
            time.sleep(1)
            socketio.emit('search_progress', {
                'elapsed': i + 1,
                'total': search_time
            }, room=f'order_search_{user_id}')
        
        if True:  # random.random() > 0.2:
            generate_order_for_user(user_id)
        else:
            socketio.emit('no_orders_found', {
                'message': 'No orders available in your area'
            }, room=f'order_search_{user_id}')
    except Exception as e:
        logger.error(f"Error in order search: {str(e)}")

def generate_order_for_user(user_id):
    try:
        from app.utils.game_helper import get_order_for_user
        from flask import current_app
        
        logger.info(f"Generating order for user {user_id}")
        
        # Запускаем в контексте Flask приложения
        order = get_order_for_user(user_id)
        if order:
            logger.info(f"Order created: {order}")
            logger.info(f"Sending to room: order_search_{user_id}")
            socketio.emit("order_found", {
                "success": True,
                "order": order
            }, room=f"order_search_{user_id}")
            logger.info(f"Order sent to frontend for user {user_id}")
        else:
            logger.info(f"No order generated for user {user_id}")
            socketio.emit("no_orders_found", {
                "message": "No orders available"
            }, room=f"order_search_{user_id}")
    except Exception as e:
        logger.error(f"Error generating order: {str(e)}")
def simulate_order_search_sync(user_id, radius_km):
    """Синхронная версия поиска заказов"""
    try:
        search_time = random.randint(5, 15)
        for i in range(search_time):
            socketio.sleep(1)  # Используем socketio.sleep вместо time.sleep
            socketio.emit('search_progress', {
                'elapsed': i + 1,
                'total': search_time
            }, room=f'order_search_{user_id}')
        
        generate_order_for_user(user_id)
    except Exception as e:
        logger.error(f"Error in sync order search: {str(e)}")
