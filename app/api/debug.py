# -*- coding: utf-8 -*-
"""
DEBUG API endpoints для тестирования.
⚠️ НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ!
"""

from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Order
from app.utils.game_helper import check_player_zones
from app.utils.gps_helper import calculate_distance_meters
import logging

debug_bp = Blueprint('debug', __name__)
logger = logging.getLogger(__name__)

@debug_bp.route('/simulate_position', methods=['POST'])
def simulate_position():
    """
    Симуляция позиции игрока для тестирования.
    
    POST /api/debug/simulate_position
    {
        "user_id": 1,
        "lat": 43.2220,
        "lng": 76.8512
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not all([user_id, lat, lng]):
            return jsonify({'error': 'user_id, lat, lng required'}), 400
        
        # Обновляем позицию
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.update_position(lat, lng)
        
        # Проверяем зоны
        zones = check_player_zones(user_id, lat, lng)
        
        # Если есть активный заказ, добавляем дистанции
        active_order = user.get_active_order()
        if active_order:
            distance_to_pickup = calculate_distance_meters(
                lat, lng,
                active_order.pickup_lat, active_order.pickup_lng
            )
            distance_to_dropoff = calculate_distance_meters(
                lat, lng,
                active_order.dropoff_lat, active_order.dropoff_lng
            )
            
            zones['distances'] = {
                'to_pickup_m': round(distance_to_pickup, 1),
                'to_dropoff_m': round(distance_to_dropoff, 1)
            }
        
        return jsonify({
            'success': True,
            'position': {'lat': lat, 'lng': lng},
            'zones': zones
        })
        
    except Exception as e:
        logger.error(f"Error simulating position: {str(e)}")
        return jsonify({'error': str(e)}), 500

@debug_bp.route('/teleport_to_pickup', methods=['POST'])
def teleport_to_pickup():
    """
    Телепортировать игрока к ресторану для тестирования pickup.
    
    POST /api/debug/teleport_to_pickup
    {
        "user_id": 1
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        active_order = user.get_active_order()
        if not active_order:
            return jsonify({'error': 'No active order'}), 400
        
        # Телепортируем к ресторану
        pickup_lat = active_order.pickup_lat
        pickup_lng = active_order.pickup_lng
        
        user.update_position(pickup_lat, pickup_lng)
        
        # Проверяем зоны
        zones = check_player_zones(user_id, pickup_lat, pickup_lng)
        
        return jsonify({
            'success': True,
            'message': f'Телепортировано к {active_order.pickup_name}',
            'position': {'lat': pickup_lat, 'lng': pickup_lng},
            'zones': zones,
            'order': active_order.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error teleporting: {str(e)}")
        return jsonify({'error': str(e)}), 500

@debug_bp.route('/teleport_to_dropoff', methods=['POST'])
def teleport_to_dropoff():
    """
    Телепортировать игрока к клиенту для тестирования delivery.
    
    POST /api/debug/teleport_to_dropoff
    {
        "user_id": 1
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        active_order = user.get_active_order()
        if not active_order:
            return jsonify({'error': 'No active order'}), 400
        
        if not active_order.pickup_time:
            return jsonify({'error': 'Order not picked up yet'}), 400
        
        # Телепортируем к клиенту
        dropoff_lat = active_order.dropoff_lat
        dropoff_lng = active_order.dropoff_lng
        
        user.update_position(dropoff_lat, dropoff_lng)
        
        # Проверяем зоны
        zones = check_player_zones(user_id, dropoff_lat, dropoff_lng)
        
        return jsonify({
            'success': True,
            'message': f'Телепортировано к {active_order.dropoff_address}',
            'position': {'lat': dropoff_lat, 'lng': dropoff_lng},
            'zones': zones,
            'order': active_order.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error teleporting: {str(e)}")
        return jsonify({'error': str(e)}), 500
