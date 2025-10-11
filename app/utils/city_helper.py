# -*- coding: utf-8 -*-
"""
Утилиты для работы с городами.
Управление данными для разных городов.
"""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Кэш конфигурации городов
_cities_config_cache = None

def load_cities_config(filename: str = 'data/cities/cities_config.json') -> Dict:
    """
    Загрузка конфигурации городов.
    
    Args:
        filename (str): Путь к файлу конфигурации
    
    Returns:
        dict: Конфигурация всех городов
    """
    global _cities_config_cache
    
    if _cities_config_cache is not None:
        return _cities_config_cache
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            config = json.load(file)
        
        _cities_config_cache = config
        logger.info(f"Loaded {len(config.get('cities', []))} cities from config")
        return config
        
    except FileNotFoundError:
        logger.error(f"Cities config file not found: {filename}")
        return {'cities': []}
    except Exception as e:
        logger.error(f"Error loading cities config: {str(e)}")
        return {'cities': []}

def get_active_cities() -> List[Dict]:
    """
    Получение списка активных городов.
    
    Returns:
        list: Список активных городов
    """
    config = load_cities_config()
    cities = config.get('cities', [])
    return [city for city in cities if city.get('active', False)]

def get_city_by_id(city_id: str) -> Optional[Dict]:
    """
    Получение города по ID.
    
    Args:
        city_id (str): ID города (almaty, astana, и т.д.)
    
    Returns:
        dict: Данные города или None
    """
    config = load_cities_config()
    cities = config.get('cities', [])
    
    for city in cities:
        if city.get('id') == city_id:
            return city
    
    return None

def get_city_data_path(city_id: str, data_type: str = 'restaurants') -> str:
    """
    Получение пути к файлу данных для города.
    
    Args:
        city_id (str): ID города
        data_type (str): Тип данных (restaurants или buildings)
    
    Returns:
        str: Путь к файлу
    """
    return f'data/cities/{city_id}/{data_type}.geojson'

def is_city_active(city_id: str) -> bool:
    """
    Проверка, активен ли город.
    
    Args:
        city_id (str): ID города
    
    Returns:
        bool: True если город активен
    """
    city = get_city_by_id(city_id)
    if not city:
        return False
    return city.get('active', False)

def reload_cities_cache():
    """
    Принудительная перезагрузка кэша конфигурации городов.
    """
    global _cities_config_cache
    _cities_config_cache = None
    logger.info("Cities config cache reloaded")




def detect_city_by_location(lat: float, lng: float) -> str | None:
    """
    Определяет ближайший город по координатам.
    Использует данные из data/cities/cities_config.json.
    """
    import json, math, os

    path = os.path.join("data", "cities", "cities_config.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        cities = json.load(f)

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearest_city = None
    min_distance = float("inf")

    for city in cities:
        if isinstance(city, str):
            continue
        lat_c, lng_c = city.get("lat"), city.get("lng")
        if lat_c is None or lng_c is None:
            continue
        distance = haversine(lat, lng, lat_c, lng_c)
        if distance < min_distance:
            min_distance = distance
            nearest_city = city.get("id")

    return nearest_city


def detect_city_by_location(lat: float, lng: float) -> str | None:
    """
    Определяет ближайший город по координатам.
    Читает структуру {"cities": [{id, center: {lat, lng}}]}.
    """
    import json, math, os

    path = os.path.join("data", "cities", "cities_config.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cities = data.get("cities", [])

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearest_city = None
    min_distance = float("inf")

    for city in cities:
        center = city.get("center") or {}
        lat_c, lng_c = center.get("lat"), center.get("lng")
        if lat_c is None or lng_c is None:
            continue
        distance = haversine(lat, lng, lat_c, lng_c)
        if distance < min_distance:
            min_distance = distance
            nearest_city = city.get("id")

    return nearest_city
