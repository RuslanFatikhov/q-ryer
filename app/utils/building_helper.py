# -*- coding: utf-8 -*-
"""
Утилиты для работы со зданиями из GeoJSON файла.
Функции для поиска и выбора зданий для доставки.
Поддержка нескольких городов.
"""

import json
import random
import logging
from typing import Dict, List, Optional
from app.utils.gps_helper import calculate_distance
from app.utils.city_helper import get_city_data_path

logger = logging.getLogger(__name__)

# Кэш данных зданий для разных городов
_buildings_cache = {}

def load_buildings_data(city_id: str = 'almaty') -> List[Dict]:
    """
    Загрузка данных зданий из GeoJSON файла для указанного города.
    
    Args:
        city_id (str): ID города (almaty, astana и т.д.)
    
    Returns:
        list: Список зданий
    """
    global _buildings_cache
    
    # Проверяем кэш для этого города
    if city_id in _buildings_cache:
        return _buildings_cache[city_id]
    
    # Получаем путь к файлу для города
    filename = get_city_data_path(city_id, 'buildings')
    
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
                'city_id': city_id,  # Добавляем ID города
                'properties': properties
            }
            buildings.append(building)
        
        # Кэшируем результат для этого города
        _buildings_cache[city_id] = buildings
        logger.info(f"Loaded {len(buildings)} buildings for {city_id}")
        return buildings
        
    except FileNotFoundError:
        logger.error(f"Buildings file not found: {filename}")
        return []
    except Exception as e:
        logger.error(f"Error loading buildings for {city_id}: {str(e)}")
        return []

def get_random_building(city_id: str = 'almaty') -> Optional[Dict]:
    """
    Получение случайного здания для доставки в указанном городе.
    
    Args:
        city_id (str): ID города
    
    Returns:
        dict: Случайное здание или None
    """
    buildings = load_buildings_data(city_id)
    
    if not buildings:
        return None
    
    return random.choice(buildings)

def get_buildings_near_location(lat: float, lng: float, radius_km: float = 5.0, city_id: str = 'almaty') -> List[Dict]:
    """
    Получение зданий рядом с указанной позицией в городе.
    
    Args:
        lat (float): Широта
        lng (float): Долгота  
        radius_km (float): Радиус поиска в километрах
        city_id (str): ID города
    
    Returns:
        list: Список зданий в радиусе
    """
    buildings = load_buildings_data(city_id)
    nearby_buildings = []
    
    for building in buildings:
        distance = calculate_distance(lat, lng, building['lat'], building['lng'])
        if distance <= radius_km:
            building_with_distance = building.copy()
            building_with_distance['distance_km'] = round(distance, 2)
            nearby_buildings.append(building_with_distance)
    
    # Сортируем по расстоянию
    nearby_buildings.sort(key=lambda x: x['distance_km'])
    return nearby_buildings

def reload_buildings_cache(city_id: Optional[str] = None):
    """
    Принудительная перезагрузка кэша зданий.
    
    Args:
        city_id (str): ID города для перезагрузки, если None - перезагрузить все
    """
    global _buildings_cache
    
    if city_id:
        # Перезагрузить только один город
        if city_id in _buildings_cache:
            del _buildings_cache[city_id]
        logger.info(f"Buildings cache reloaded for {city_id}")
    else:
        # Перезагрузить все города
        _buildings_cache = {}
        logger.info("Buildings cache reloaded for all cities")

def get_suitable_buildings_for_delivery(pickup_lat: float, pickup_lng: float, 
                                       min_distance_km: float = 0.5, 
                                       max_distance_km: float = 3.0,
                                       city_id: str = 'almaty') -> List[Dict]:
    """
    Получение подходящих зданий для доставки на определенном расстоянии от pickup.
    
    Args:
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        min_distance_km (float): Минимальное расстояние
        max_distance_km (float): Максимальное расстояние
        city_id (str): ID города
    
    Returns:
        list: Список подходящих зданий
    """
    buildings = load_buildings_data(city_id)
    suitable_buildings = []
    
    for building in buildings:
        distance = calculate_distance(pickup_lat, pickup_lng, building['lat'], building['lng'])
        if min_distance_km <= distance <= max_distance_km:
            building_with_distance = building.copy()
            building_with_distance['distance_km'] = round(distance, 2)
            suitable_buildings.append(building_with_distance)
    
    return suitable_buildings

def get_random_building_for_delivery(pickup_lat: float, pickup_lng: float, 
                                     min_distance_km: float = 0.5, 
                                     max_distance_km: float = 3.0,
                                     city_id: str = 'almaty') -> Optional[Dict]:
    """
    Получение случайного здания для доставки на определенном расстоянии от pickup.
    
    Args:
        pickup_lat (float): Широта ресторана
        pickup_lng (float): Долгота ресторана
        min_distance_km (float): Минимальное расстояние
        max_distance_km (float): Максимальное расстояние
        city_id (str): ID города
    
    Returns:
        dict: Случайное подходящее здание или None
    """
    suitable_buildings = get_suitable_buildings_for_delivery(
        pickup_lat, pickup_lng, min_distance_km, max_distance_km, city_id
    )
    
    if not suitable_buildings:
        return None
    
    return random.choice(suitable_buildings)

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
        bool: True если игрок в зоне dropoff
    """
    from app.utils.gps_helper import is_within_radius
    return is_within_radius(building_lat, building_lng, player_lat, player_lng, radius_meters)

def get_buildings_stats(city_id: str = 'almaty') -> Dict:
    """
    Получение статистики по зданиям для города.
    
    Args:
        city_id (str): ID города
    
    Returns:
        dict: Статистика зданий
    """
    buildings = load_buildings_data(city_id)
    
    if not buildings:
        return {
            'total_buildings': 0,
            'coverage_area': None,
            'city_id': city_id
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
        },
        'city_id': city_id
    }

def get_random_building_within_game_radius(player_lat: float, player_lng: float,
                                          pickup_lat: float, pickup_lng: float,
                                          player_radius_km: float = 5.0,
                                          min_distance_from_pickup_km: float = 0.5,
                                          max_distance_from_pickup_km: float = 5.0,
                                          city_id: str = 'almaty') -> Optional[Dict]:
    """
    Получение случайного здания для доставки с проверкой двух условий:
    1. Здание находится в радиусе от ресторана (min_distance_from_pickup_km - max_distance_from_pickup_km)
    2. Здание находится в радиусе от игрока (player_radius_km)
    
    Это гарантирует, что игрок сможет играть в рамках заданного радиуса.
    
    Args:
        player_lat (float): Широта игрока
        player_lng (float): Долгота игрока
        pickup_lat (float): Широта ресторана (точка pickup)
        pickup_lng (float): Долгота ресторана (точка pickup)
        player_radius_km (float): Максимальный радиус от игрока
        min_distance_from_pickup_km (float): Минимальное расстояние от ресторана
        max_distance_from_pickup_km (float): Максимальное расстояние от ресторана
        city_id (str): ID города
    
    Returns:
        dict: Случайное подходящее здание или None, если нет подходящих
    """
    buildings = load_buildings_data(city_id)
    suitable_buildings = []
    
    for building in buildings:
        # Проверка 1: Расстояние от ресторана (для игрового баланса)
        distance_from_pickup = calculate_distance(
            pickup_lat, pickup_lng, 
            building['lat'], building['lng']
        )
        
        if not (min_distance_from_pickup_km <= distance_from_pickup <= max_distance_from_pickup_km):
            continue
        
        # Проверка 2: Расстояние от игрока (главное ограничение радиуса)
        distance_from_player = calculate_distance(
            player_lat, player_lng,
            building['lat'], building['lng']
        )
        
        if distance_from_player > player_radius_km:
            continue
        
        # Здание подходит по обоим критериям
        building_with_distances = building.copy()
        building_with_distances['distance_from_pickup_km'] = round(distance_from_pickup, 2)
        building_with_distances['distance_from_player_km'] = round(distance_from_player, 2)
        building_with_distances['delivery_distance_km'] = round(distance_from_pickup, 2)
        suitable_buildings.append(building_with_distances)
    
    if not suitable_buildings:
        logger.warning(
            f"No buildings found within player_radius={player_radius_km}km from player "
            f"AND {min_distance_from_pickup_km}-{max_distance_from_pickup_km}km from pickup"
        )
        return None
    
    # Возвращаем случайное здание из подходящих
    selected_building = random.choice(suitable_buildings)
    logger.info(
        f"Selected building: {selected_building['address']}, "
        f"distance from player: {selected_building['distance_from_player_km']}km, "
        f"distance from pickup: {selected_building['distance_from_pickup_km']}km"
    )
    
    return selected_building
