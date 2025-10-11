# -*- coding: utf-8 -*-
"""
Утилиты для работы с ресторанами из GeoJSON файла.
Функции для поиска и выбора ресторанов для заказов.
Поддержка нескольких городов.
"""

import json
import random
import logging
from typing import Dict, List, Optional
from app.utils.gps_helper import calculate_distance, is_within_radius
from app.utils.city_helper import get_city_data_path

logger = logging.getLogger(__name__)

# Кэш данных ресторанов для разных городов
_restaurants_cache = {}

def load_restaurants_data(city_id: str = 'almaty') -> List[Dict]:
    """
    Загрузка данных ресторанов из GeoJSON файла для указанного города.
    
    Args:
        city_id (str): ID города (almaty, astana и т.д.)
    
    Returns:
        list: Список ресторанов
    """
    global _restaurants_cache
    
    # Проверяем кэш для этого города
    if city_id in _restaurants_cache:
        return _restaurants_cache[city_id]
    
    # Получаем путь к файлу для города
    filename = get_city_data_path(city_id, 'restaurants')
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            geojson_data = json.load(file)
        
        restaurants = []
        features = geojson_data.get('features', [])
        
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Получаем название
            name = properties.get('name')
            if not name:
                continue
            
            # Получаем координаты
            coordinates = geometry.get('coordinates')
            if not coordinates or len(coordinates) < 2:
                continue
            
            lng, lat = coordinates[0], coordinates[1]
            
            restaurant = {
                'name': name,
                'lat': lat,
                'lng': lng,
                'city_id': city_id,  # Добавляем ID города
                'properties': properties
            }
            restaurants.append(restaurant)
        
        # Кэшируем результат для этого города
        _restaurants_cache[city_id] = restaurants
        logger.info(f"Loaded {len(restaurants)} restaurants for {city_id}")
        return restaurants
        
    except FileNotFoundError:
        logger.error(f"Restaurants file not found: {filename}")
        return []
    except Exception as e:
        logger.error(f"Error loading restaurants for {city_id}: {str(e)}")
        return []

def get_random_restaurant(city_id: str = 'almaty') -> Optional[Dict]:
    """
    Получение случайного ресторана для заказа в указанном городе.
    
    Args:
        city_id (str): ID города
    
    Returns:
        dict: Случайный ресторан или None
    """
    restaurants = load_restaurants_data(city_id)
    
    if not restaurants:
        return None
    
    return random.choice(restaurants)

def get_restaurants_near_location(lat: float, lng: float, radius_km: float = 5.0, city_id: str = 'almaty') -> List[Dict]:
    """
    Получение ресторанов рядом с указанной позицией в городе.
    
    Args:
        lat (float): Широта
        lng (float): Долгота  
        radius_km (float): Радиус поиска в километрах
        city_id (str): ID города
    
    Returns:
        list: Список ресторанов в радиусе
    """
    restaurants = load_restaurants_data(city_id)
    nearby_restaurants = []
    
    for restaurant in restaurants:
        distance = calculate_distance(lat, lng, restaurant['lat'], restaurant['lng'])
        if distance <= radius_km:
            restaurant_with_distance = restaurant.copy()
            restaurant_with_distance['distance_km'] = round(distance, 2)
            nearby_restaurants.append(restaurant_with_distance)
    
    # Сортируем по расстоянию
    nearby_restaurants.sort(key=lambda x: x['distance_km'])
    return nearby_restaurants

def is_player_at_restaurant(player_lat: float, player_lng: float, 
                           restaurant_lat: float, restaurant_lng: float, 
                           radius_meters: float = 30.0) -> bool:
    """
    Проверка, находится ли игрок рядом с рестораном.
    
    Args:
        player_lat (float): Широта игрока
        player_lng (float): Долгота игрока
        restaurant_lat (float): Широта ресторана
        restaurant_lng (float): Долгота ресторана
        radius_meters (float): Радиус в метрах
    
    Returns:
        bool: True если игрок в зоне pickup
    """
    return is_within_radius(restaurant_lat, restaurant_lng, player_lat, player_lng, radius_meters)

def reload_restaurants_cache(city_id: Optional[str] = None):
    """
    Принудительная перезагрузка кэша ресторанов.
    
    Args:
        city_id (str): ID города для перезагрузки, если None - перезагрузить все
    """
    global _restaurants_cache
    
    if city_id:
        # Перезагрузить только один город
        if city_id in _restaurants_cache:
            del _restaurants_cache[city_id]
        logger.info(f"Restaurants cache reloaded for {city_id}")
    else:
        # Перезагрузить все города
        _restaurants_cache = {}
        logger.info("Restaurants cache reloaded for all cities")

def get_restaurants_stats(city_id: str = 'almaty') -> Dict:
    """
    Получение статистики по ресторанам для города.
    
    Args:
        city_id (str): ID города
    
    Returns:
        dict: Статистика ресторанов
    """
    restaurants = load_restaurants_data(city_id)
    
    if not restaurants:
        return {
            'total_restaurants': 0,
            'by_type': {},
            'coverage_area': None,
            'city_id': city_id
        }
    
    # Статистика по типам
    by_type = {}
    for restaurant in restaurants:
        amenity = restaurant.get('properties', {}).get('amenity', 'unknown')
        by_type[amenity] = by_type.get(amenity, 0) + 1
    
    # Находим boundaries покрытия
    latitudes = [r['lat'] for r in restaurants]
    longitudes = [r['lng'] for r in restaurants]
    
    return {
        'total_restaurants': len(restaurants),
        'by_type': by_type,
        'coverage_area': {
            'min_lat': min(latitudes),
            'max_lat': max(latitudes),
            'min_lng': min(longitudes),
            'max_lng': max(longitudes)
        },
        'city_id': city_id
    }
