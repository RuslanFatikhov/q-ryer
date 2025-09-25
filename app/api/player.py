# -*- coding: utf-8 -*-
"""
API endpoints для игроков симулятора курьера.
Обрабатывает заказы, позицию игрока и игровые действия.
"""

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import User, Order
from app.utils.game_helper import (
    get_order_for_user, check_player_zones, pickup_order, 
    deliver_order, cancel_order, validate_order_action
)
import logging

# Создаем blueprint
player_bp = Blueprint('player', __name__)

# Настройка логирования
logger = logging.getLogger(__name__)

@player_bp.route('/start_shift', methods=['POST'])
def start_shift():
    """
    Начать смену игрока.
    Устанавливает статус онлайн и подготавливает к получению заказов.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Устанавливаем статус онлайн
        user.set_online_status(True)
        
        # Проверяем, есть ли активный заказ
        active_order = user.get_active_order()
        
        logger.info(f"User {user.username} started shift")
        
        return jsonify({
            'success': True,
            'message': 'Shift started successfully',
            'user': user.to_dict(),
            'active_order': active_order.to_dict() if active_order else None
        })
        
    except Exception as e:
        logger.error(f"Error starting shift: {str(e)}")
        return jsonify({'error': 'Failed to start shift'}), 500

@player_bp.route('/stop_shift', methods=['POST'])
def stop_shift():
    """
    Завершить смену игрока.
    Устанавливает статус офлайн.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем, нет ли активного заказа
        active_order = user.get_active_order()
        if active_order:
            return jsonify({
                'error': 'Cannot end shift with active order',
                'active_order': active_order.to_dict()
            }), 400
        
        # Устанавливаем статус офлайн
        user.set_online_status(False)
        
        logger.info(f"User {user.username} ended shift")
        
        return jsonify({
            'success': True,
            'message': 'Shift ended successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error ending shift: {str(e)}")
        return jsonify({'error': 'Failed to end shift'}), 500

@player_bp.route('/order/new', methods=['GET'])
def get_new_order():
    """
    Получить новый заказ для игрока.
    Генерирует случайный заказ от ресторана к зданию.
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем, что пользователь онлайн
        if not user.is_online:
            return jsonify({'error': 'User is not online'}), 400
        
        # Проверяем, что нет активного заказа
        active_order = user.get_active_order()
        if active_order:
            return jsonify({
                'error': 'User already has active order',
                'active_order': active_order.to_dict()
            }), 400
        
        # Генерируем новый заказ
        order = get_order_for_user(int(user_id))
        if not order:
            return jsonify({
                'success': False,
                'message': 'No orders available in your area'
            })
        
        logger.info(f"Generated new order {order['id']} for user {user_id}")
        
        return jsonify({
            'success': True,
            'order': order
        })
        
    except Exception as e:
        logger.error(f"Error getting new order: {str(e)}")
        return jsonify({'error': 'Failed to get order'}), 500

@player_bp.route('/order/accept', methods=['POST'])
def accept_order():
    """
    Принять заказ игроком.
    Заказ уже создан, просто меняем статус.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        order_id = data.get('order_id')
        
        if not user_id or not order_id:
            return jsonify({'error': 'user_id and order_id are required'}), 400
        
        # Проверяем валидность действия
        validation = validate_order_action(user_id, 'accept')
        if not validation.get('valid', False):
            return jsonify({'error': validation.get('error')}), 400
        
        order = Order.query.get(order_id)
        if not order or order.user_id != user_id:
            return jsonify({'error': 'Order not found or not assigned to user'}), 404
        
        # Заказ уже создан и назначен пользователю при генерации
        logger.info(f"User {user_id} accepted order {order_id}")
        
        return jsonify({
            'success': True,
            'message': 'Order accepted successfully',
            'order': order.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error accepting order: {str(e)}")
        return jsonify({'error': 'Failed to accept order'}), 500

@player_bp.route('/order/pickup', methods=['POST'])
def pickup_order_endpoint():
    """
    Забрать заказ в ресторане.
    Игрок должен быть в зоне pickup.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Проверяем валидность действия
        validation = validate_order_action(user_id, 'pickup')
        if not validation.get('valid', False):
            return jsonify({'error': validation.get('error')}), 400
        
        # Выполняем pickup
        result = pickup_order(user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error')}), 400
        
    except Exception as e:
        logger.error(f"Error in pickup endpoint: {str(e)}")
        return jsonify({'error': 'Failed to pickup order'}), 500

@player_bp.route('/order/deliver', methods=['POST'])
def deliver_order_endpoint():
    """
    Доставить заказ в здание.
    Игрок должен быть в зоне dropoff.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Проверяем валидность действия
        validation = validate_order_action(user_id, 'deliver')
        if not validation.get('valid', False):
            return jsonify({'error': validation.get('error')}), 400
        
        # Выполняем доставку
        result = deliver_order(user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error')}), 400
        
    except Exception as e:
        logger.error(f"Error in deliver endpoint: {str(e)}")
        return jsonify({'error': 'Failed to deliver order'}), 500

@player_bp.route('/order/cancel', methods=['POST'])
def cancel_order_endpoint():
    """
    Отменить заказ.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason', 'user_cancelled')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Проверяем валидность действия
        validation = validate_order_action(user_id, 'cancel')
        if not validation.get('valid', False):
            return jsonify({'error': validation.get('error')}), 400
        
        # Отменяем заказ
        result = cancel_order(user_id, reason)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error')}), 400
        
    except Exception as e:
        logger.error(f"Error in cancel endpoint: {str(e)}")
        return jsonify({'error': 'Failed to cancel order'}), 500

@player_bp.route('/position', methods=['POST'])
def update_position():
    """
    Обновить позицию игрока.
    Проверяет зоны pickup/dropoff.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        lat = data.get('lat')
        lng = data.get('lng')
        accuracy = data.get('accuracy', 999)
        
        if not user_id or lat is None or lng is None:
            return jsonify({'error': 'user_id, lat, and lng are required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем точность GPS
        max_accuracy = current_app.config['GAME_CONFIG']['max_gps_accuracy']
        if accuracy > max_accuracy:
            return jsonify({
                'warning': 'GPS accuracy is too low',
                'accuracy': accuracy,
                'max_allowed': max_accuracy,
                'recommendation': 'Move to an open area for better GPS signal'
            }), 202  # Accepted but with warning
        
        # Обновляем позицию пользователя
        user.update_position(lat, lng)
        
        # Проверяем зоны заказа
        zones_status = check_player_zones(user_id, lat, lng)
        
        logger.info(f"Updated position for user {user_id}: ({lat}, {lng}) accuracy: {accuracy}m")
        
        return jsonify({
            'success': True,
            'position': {'lat': lat, 'lng': lng, 'accuracy': accuracy},
            'zones': zones_status
        })
        
    except Exception as e:
        logger.error(f"Error updating position: {str(e)}")
        return jsonify({'error': 'Failed to update position'}), 500

@player_bp.route('/status', methods=['GET'])
def get_player_status():
    """
    Получить текущий статус игрока.
    Включает активный заказ, позицию, баланс.
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Получаем активный заказ
        active_order = user.get_active_order()
        
        # Получаем статистику
        stats = user.get_statistics()
        
        return jsonify({
            'user': user.to_dict(),
            'active_order': active_order.to_dict() if active_order else None,
            'statistics': stats,
            'position': {
                'lat': user.last_position_lat,
                'lng': user.last_position_lng
            } if user.last_position_lat and user.last_position_lng else None
        })
        
    except Exception as e:
        logger.error(f"Error getting player status: {str(e)}")
        return jsonify({'error': 'Failed to get status'}), 500

@player_bp.route('/config', methods=['GET'])
def get_game_config():
    """
    Получить игровую конфигурацию.
    Радиусы, таймеры, настройки экономики.
    """
    try:
        config = current_app.config['GAME_CONFIG']
        
        # Возвращаем только нужные клиенту настройки
        client_config = {
            'pickup_radius': config['pickup_radius'],
            'dropoff_radius': config['dropoff_radius'],
            'max_gps_accuracy': config['max_gps_accuracy'],
            'base_payment': config['base_payment'],
            'distance_rate': config['distance_rate'],
            'on_time_bonus': config['on_time_bonus']
        }
        
        return jsonify(client_config)
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({'error': 'Failed to get config'}), 500