# -*- coding: utf-8 -*-
"""
API endpoints для работы с городами.
"""

from flask import Blueprint, jsonify
from app.utils.city_helper import load_cities_config, get_active_cities, get_city_by_id

# Создаем Blueprint для городов
cities_bp = Blueprint('cities', __name__)

@cities_bp.route('/api/cities', methods=['GET'])
def get_cities():
    """
    Получить список всех городов.
    
    Returns:
        JSON: Список городов с их конфигурацией
    """
    try:
        config = load_cities_config()
        cities = config.get('cities', [])
        
        return jsonify({
            'success': True,
            'cities': cities
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cities_bp.route('/api/cities/active', methods=['GET'])
def get_active_cities_endpoint():
    """
    Получить список активных городов.
    
    Returns:
        JSON: Список активных городов
    """
    try:
        active_cities = get_active_cities()
        
        return jsonify({
            'success': True,
            'cities': active_cities,
            'count': len(active_cities)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cities_bp.route('/api/cities/<city_id>', methods=['GET'])
def get_city_info(city_id):
    """
    Получить информацию о конкретном городе.
    
    Args:
        city_id (str): ID города
    
    Returns:
        JSON: Данные города
    """
    try:
        city = get_city_by_id(city_id)
        
        if not city:
            return jsonify({
                'success': False,
                'error': f'City {city_id} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'city': city
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cities_bp.route('/api/user/city', methods=['POST'])
def set_user_city():
    """
    Установить город для пользователя.
    
    Request JSON:
        user_id (int): ID пользователя
        city_id (str): ID города
    
    Returns:
        JSON: Результат операции
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        city_id = data.get('city_id')
        
        if not user_id or not city_id:
            return jsonify({
                'success': False,
                'error': 'user_id and city_id are required'
            }), 400
        
        # Проверяем что город существует
        city = get_city_by_id(city_id)
        if not city:
            return jsonify({
                'success': False,
                'error': f'City {city_id} not found'
            }), 404
        
        # Обновляем город пользователя
        from app.models import User
        from app import db
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        user.city_id = city_id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'City set to {city_id}',
            'city': city
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
