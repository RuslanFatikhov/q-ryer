# -*- coding: utf-8 -*-
"""
Утилиты для работы со зданиями из GeoJSON файла.
Функции для поиска и выбора зданий для доставки.
"""

import json
import random
import logging
from typing import Dict, List, Optional
from app.utils.gps_helper import calculate_distance, is_within_radius

# Настройка логирования
logger = logging.getLogger(__name__)

# Кэш данных зданий
_buildings_cache = None

def load_buildings_data(filename: str = 'data/buildings.geojson') -> List[Dict]:
    """
    Загрузка данных зданий из GeoJSON файла.
    
    Args:
        filename (str): Путь к файлу с данными зданий
    
    Returns:
        list: Список зданий
    """
    global _buildings_cache
    
    if _buildings_cache is not None:
        return _buildings_cache
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            geojson_data = json.load(file)
        
        buildings = []
        features = geojson_data.get('features', [])
        
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Формируем адрес
            street = properties.get('addr:street', '')
            house_number = properties.get('addr:housenumber', '')
            address = f"{street} {house_number}".strip()
            
            if not address:
                continue
            
            # Получаем координаты
            coordinates = geometry.get('coordinates')
            if not coordinates or len(coordinates) < 2:
                continue
            
            lng, lat = coordinates[0], coordinates[1]
            
            building = {
                'address': address,
                'lat': lat,
                'lng': lng,
                'properties': properties  # Сохраняем все свойства на случай если понадобятся
            }
            buildings.append(building)
        
        _buildings_cache = buildings
        logger.info(f"Loaded {len(buildings)} buildings from {filename}")
        return buildings
        
    except FileNotFoundError:
        logger.error(f"Buildings file not found: {filename}")
        return []
    except Exception as e:
        logger.error(f"Error loading buildings: {str(e)}")
        return []

def get_random_building() -> Optional[Dict]:
    """
    Получение случайного здания для доставки.
    
    Returns:
        dict: Случайное здание или None
    """
    buildings = load_buildings_data()
    
    if not buildings:
        return None
    
    return random.choice(buildings)

def get_buildings_near_location(lat: float, lng: float, radius_km: float = 5.0) -> List[Dict]:
    """
    Получение зданий рядом с указанной позицией.
    
    Args:
        lat (float): Широта
        lng (float): Долгота  
        radius_km (float): Радиус поиска в километрах
    
    Returns:
        list: Список зданий в радиусе
    """
    buildings = load_buildings_data()
    nearby_buildings = []
    
    for building in buildings:
        distance = calculate_distance(lat, lng, building['lat'], building['lng'])
        if distance <= radius_km:
            # Добавляем расстояние к данным здания
            building_with_distance = building.copy()
            building_with_distance['distance_km'] = round(distance, 2)
            nearby_buildings.append(building_with_distance)
    
    # Сортируем по расстоянию
    nearby_buildings.sort(key=lambda x: x['distance_km'])
    return nearby_buildings

def find_building_by_address(address: str) -> Optional[Dict]:
    """
    Поиск здания по адресу.
    
    Args:
        address (str): Адрес для поиска
    
    Returns:
        dict: Найденное здание или None
    """
    buildings = load_buildings_data()
    
    # Точное совпадение
    for building in buildings:
        if building['address'].lower() == address.lower():
            return building
    
    # Частичное совпадение
    for building in buildings:
        if address.lower() in building['address'].lower():
            return building
    
    return None

def is_player_at_building(player_lat: float, player_lng: float, 
                         building_lat: float, building_lng: float, 
                         radius_meters: float = 30.0) -> bool:
    """
    Проверка, находится ли игрок рядом со зданием.
    
    Args:
        player_lat (float): Широта игрока
        player_lng (float): Долгота игрока
        building_lat (float): Широта здания
        building_lng (float): Долгота здания
        radius_meters (float): Радиус в метрах
    
    Returns:
        bool: True если игрок в зоне доставки
    """
    return is_within_radius(building_lat, building_lng, player_lat, player_lng, radius_meters)

def get_delivery_distance(pickup_lat: float, pickup_lng: float,
                         building_lat: float, building_lng: float) -> float:
    """
    Расчет расстояния доставки от ресторана к зданию.
    
    Args:
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        building_lat (float): Широта здания
        building_lng (float): Долгота здания
    
    Returns:
        float: Расстояние в километрах
    """
    return calculate_distance(pickup_lat, pickup_lng, building_lat, building_lng)

def validate_building_for_delivery(building: Dict, pickup_lat: float, pickup_lng: float,
                                 min_distance_km: float = 0.5, 
                                 max_distance_km: float = 10.0) -> bool:
    """
    Проверка, подходит ли здание для доставки.
    
    Args:
        building (dict): Данные здания
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        min_distance_km (float): Минимальное расстояние
        max_distance_km (float): Максимальное расстояние
    
    Returns:
        bool: True если здание подходит
    """
    distance = get_delivery_distance(pickup_lat, pickup_lng, 
                                   building['lat'], building['lng'])
    
    return min_distance_km <= distance <= max_distance_km

def get_suitable_buildings_for_delivery(pickup_lat: float, pickup_lng: float,
                                      min_distance_km: float = 0.5,
                                      max_distance_km: float = 10.0) -> List[Dict]:
    """
    Получение списка подходящих зданий для доставки.
    
    Args:
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        min_distance_km (float): Минимальное расстояние
        max_distance_km (float): Максимальное расстояние
    
    Returns:
        list: Список подходящих зданий
    """
    buildings = load_buildings_data()
    suitable_buildings = []
    
    for building in buildings:
        if validate_building_for_delivery(building, pickup_lat, pickup_lng, 
                                        min_distance_km, max_distance_km):
            # Добавляем расстояние к данным
            building_with_distance = building.copy()
            building_with_distance['delivery_distance_km'] = round(
                get_delivery_distance(pickup_lat, pickup_lng, building['lat'], building['lng']), 2
            )
            suitable_buildings.append(building_with_distance)
    
    return suitable_buildings

def get_random_building_for_delivery(pickup_lat: float, pickup_lng: float,
                                   min_distance_km: float = 0.5,
                                   max_distance_km: float = 10.0) -> Optional[Dict]:
    """
    Получение случайного подходящего здания для доставки.
    
    Args:
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        min_distance_km (float): Минимальное расстояние
        max_distance_km (float): Максимальное расстояние
    
    Returns:
        dict: Случайное подходящее здание или None
    """
    suitable_buildings = get_suitable_buildings_for_delivery(
        pickup_lat, pickup_lng, min_distance_km, max_distance_km
    )
    
    if not suitable_buildings:
        return None
    
    return random.choice(suitable_buildings)

def reload_buildings_cache():
    """
    Принудительная перезагрузка кэша зданий.
    Используется при обновлении данных.
    """
    global _buildings_cache
    _buildings_cache = None
    logger.info("Buildings cache reloaded")

def get_buildings_stats() -> Dict:
    """
    Получение статистики по зданиям.
    
    Returns:
        dict: Статистика зданий
    """
    buildings = load_buildings_data()
    
    if not buildings:
        return {
            'total_buildings': 0,
            'coverage_area': None
        }
    
    # Находим границы покрытия
    latitudes = [b['lat'] for b in buildings]
    longitudes = [b['lng'] for b in buildings]
    
    return {
        'total_buildings': len(buildings),
        'coverage_area': {
            'min_lat': min(latitudes),
            'max_lat': max(latitudes),
            'min_lng': min(longitudes),
            'max_lng': max(longitudes)
        }
    }