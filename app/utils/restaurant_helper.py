# -*- coding: utf-8 -*-
"""
Утилиты для работы с ресторанами из GeoJSON файла.
Функции для поиска и выбора ресторанов для заказов.
"""

import json
import random
import logging
from typing import Dict, List, Optional
from app.utils.gps_helper import calculate_distance, is_within_radius

# Настройка логирования
logger = logging.getLogger(__name__)

# Кэш данных ресторанов
_restaurants_cache = None

def load_restaurants_data(filename: str = 'data/restaurants.geojson') -> List[Dict]:
    """
    Загрузка данных ресторанов из GeoJSON файла.
    
    Args:
        filename (str): Путь к файлу с данными ресторанов
    
    Returns:
        list: Список ресторанов
    """
    global _restaurants_cache
    
    if _restaurants_cache is not None:
        return _restaurants_cache
    
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
                'properties': properties  # Сохраняем все свойства
            }
            restaurants.append(restaurant)
        
        _restaurants_cache = restaurants
        logger.info(f"Loaded {len(restaurants)} restaurants from {filename}")
        return restaurants
        
    except FileNotFoundError:
        logger.error(f"Restaurants file not found: {filename}")
        return []
    except Exception as e:
        logger.error(f"Error loading restaurants: {str(e)}")
        return []

def get_random_restaurant() -> Optional[Dict]:
    """
    Получение случайного ресторана для заказа.
    
    Returns:
        dict: Случайный ресторан или None
    """
    restaurants = load_restaurants_data()
    
    if not restaurants:
        return None
    
    return random.choice(restaurants)

def get_restaurants_near_location(lat: float, lng: float, radius_km: float = 5.0) -> List[Dict]:
    """
    Получение ресторанов рядом с указанной позицией.
    
    Args:
        lat (float): Широта
        lng (float): Долгота  
        radius_km (float): Радиус поиска в километрах
    
    Returns:
        list: Список ресторанов в радиусе
    """
    restaurants = load_restaurants_data()
    nearby_restaurants = []
    
    for restaurant in restaurants:
        distance = calculate_distance(lat, lng, restaurant['lat'], restaurant['lng'])
        if distance <= radius_km:
            # Добавляем расстояние к данным ресторана
            restaurant_with_distance = restaurant.copy()
            restaurant_with_distance['distance_km'] = round(distance, 2)
            nearby_restaurants.append(restaurant_with_distance)
    
    # Сортируем по расстоянию
    nearby_restaurants.sort(key=lambda x: x['distance_km'])
    return nearby_restaurants

def find_restaurant_by_name(name: str) -> Optional[Dict]:
    """
    Поиск ресторана по названию.
    
    Args:
        name (str): Название для поиска
    
    Returns:
        dict: Найденный ресторан или None
    """
    restaurants = load_restaurants_data()
    
    # Точное совпадение
    for restaurant in restaurants:
        if restaurant['name'].lower() == name.lower():
            return restaurant
    
    # Частичное совпадение
    for restaurant in restaurants:
        if name.lower() in restaurant['name'].lower():
            return restaurant
    
    return None

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

def get_restaurants_by_type(amenity_type: str) -> List[Dict]:
    """
    Получение ресторанов по типу заведения.
    
    Args:
        amenity_type (str): Тип заведения (cafe, restaurant, fast_food)
    
    Returns:
        list: Список ресторанов определенного типа
    """
    restaurants = load_restaurants_data()
    filtered_restaurants = []
    
    for restaurant in restaurants:
        properties = restaurant.get('properties', {})
        if properties.get('amenity') == amenity_type:
            filtered_restaurants.append(restaurant)
    
    return filtered_restaurants

def reload_restaurants_cache():
    """
    Принудительная перезагрузка кэша ресторанов.
    Используется при обновлении данных.
    """
    global _restaurants_cache
    _restaurants_cache = None
    logger.info("Restaurants cache reloaded")

def get_restaurants_stats() -> Dict:
    """
    Получение статистики по ресторанам.
    
    Returns:
        dict: Статистика ресторанов
    """
    restaurants = load_restaurants_data()
    
    if not restaurants:
        return {
            'total_restaurants': 0,
            'by_type': {},
            'coverage_area': None
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
        }
    }