# -*- coding: utf-8 -*-
"""
GPS и геолокационные вспомогательные функции.
Содержит функции для расчета расстояний, проверки радиусов и работы с координатами.
"""

import math
from typing import Tuple, Optional

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Вычисление расстояния между двумя точками по формуле гаверсинуса.
    
    Args:
        lat1 (float): Широта первой точки
        lng1 (float): Долгота первой точки
        lat2 (float): Широта второй точки
        lng2 (float): Долгота второй точки
    
    Returns:
        float: Расстояние в километрах
    """
    # Радиус Земли в километрах
    R = 6371.0
    
    # Преобразуем градусы в радианы
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Разность координат
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    # Формула гаверсинуса
    a = (math.sin(dlat / 2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Расстояние в километрах
    distance = R * c
    
    return distance

def calculate_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Вычисление расстояния в метрах.
    
    Args:
        lat1 (float): Широта первой точки
        lng1 (float): Долгота первой точки
        lat2 (float): Широта второй точки
        lng2 (float): Долгота второй точки
    
    Returns:
        float: Расстояние в метрах
    """
    return calculate_distance(lat1, lng1, lat2, lng2) * 1000

def is_within_radius(center_lat: float, center_lng: float, 
                    point_lat: float, point_lng: float, 
                    radius_meters: float) -> bool:
    """
    Проверка, находится ли точка в заданном радиусе от центра.
    
    Args:
        center_lat (float): Широта центра
        center_lng (float): Долгота центра
        point_lat (float): Широта проверяемой точки
        point_lng (float): Долгота проверяемой точки
        radius_meters (float): Радиус в метрах
    
    Returns:
        bool: True если точка в радиусе
    """
    distance_meters = calculate_distance_meters(
        center_lat, center_lng, point_lat, point_lng
    )
    return distance_meters <= radius_meters

def get_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Вычисление направления (азимута) от первой точки ко второй.
    
    Args:
        lat1 (float): Широта первой точки
        lng1 (float): Долгота первой точки
        lat2 (float): Широта второй точки
        lng2 (float): Долгота второй точки
    
    Returns:
        float: Направление в градусах (0-360)
    """
    # Преобразуем в радианы
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlng_rad = math.radians(lng2 - lng1)
    
    # Вычисляем направление
    y = math.sin(dlng_rad) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlng_rad))
    
    bearing_rad = math.atan2(y, x)
    bearing_degrees = math.degrees(bearing_rad)
    
    # Нормализуем к диапазону 0-360
    bearing_degrees = (bearing_degrees + 360) % 360
    
    return bearing_degrees

def get_compass_direction(bearing: float) -> str:
    """
    Преобразование азимута в текстовое направление.
    
    Args:
        bearing (float): Азимут в градусах
    
    Returns:
        str: Текстовое направление (С, СВ, В, и т.д.)
    """
    directions = [
        "С", "ССВ", "СВ", "ВСВ",
        "В", "ВЮВ", "ЮВ", "ЮЮВ", 
        "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ",
        "З", "ЗСЗ", "СЗ", "ССЗ"
    ]
    
    # Каждое направление покрывает 22.5 градусов
    index = round(bearing / 22.5) % 16
    return directions[index]

def get_bounding_box(center_lat: float, center_lng: float, 
                    radius_km: float) -> Tuple[float, float, float, float]:
    """
    Получение ограничивающего прямоугольника для поиска точек в радиусе.
    
    Args:
        center_lat (float): Широта центра
        center_lng (float): Долгота центра
        radius_km (float): Радиус в километрах
    
    Returns:
        tuple: (min_lat, min_lng, max_lat, max_lng)
    """
    # Примерные коэффициенты для быстрого расчета
    lat_delta = radius_km / 111.0  # ~111 км на градус широты
    lng_delta = radius_km / (111.0 * math.cos(math.radians(center_lat)))
    
    min_lat = center_lat - lat_delta
    max_lat = center_lat + lat_delta
    min_lng = center_lng - lng_delta
    max_lng = center_lng + lng_delta
    
    return (min_lat, min_lng, max_lat, max_lng)

def validate_coordinates(lat: float, lng: float) -> bool:
    """
    Проверка корректности координат.
    
    Args:
        lat (float): Широта
        lng (float): Долгота
    
    Returns:
        bool: True если координаты корректны
    """
    return (-90 <= lat <= 90) and (-180 <= lng <= 180)

def is_in_almaty_bounds(lat: float, lng: float) -> bool:
    """
    Проверка, находятся ли координаты в пределах Алматы.
    
    Args:
        lat (float): Широта
        lng (float): Долгота
    
    Returns:
        bool: True если координаты в пределах Алматы
    """
    # Примерные границы Алматы
    almaty_bounds = {
        'min_lat': 43.160,
        'max_lat': 43.350,
        'min_lng': 76.800,
        'max_lng': 77.050
    }
    
    return (almaty_bounds['min_lat'] <= lat <= almaty_bounds['max_lat'] and
            almaty_bounds['min_lng'] <= lng <= almaty_bounds['max_lng'])

def format_distance(distance_km: float) -> str:
    """
    Форматирование расстояния для отображения.
    
    Args:
        distance_km (float): Расстояние в километрах
    
    Returns:
        str: Отформатированная строка расстояния
    """
    if distance_km < 1:
        meters = int(distance_km * 1000)
        return f"{meters} м"
    else:
        return f"{distance_km:.1f} км"

def get_estimated_walk_time(distance_km: float, speed_kmh: float = 5.0) -> int:
    """
    Расчет примерного времени пешей ходьбы.
    
    Args:
        distance_km (float): Расстояние в километрах
        speed_kmh (float): Скорость ходьбы в км/ч (по умолчанию 5 км/ч)
    
    Returns:
        int: Время в минутах
    """
    time_hours = distance_km / speed_kmh
    return int(time_hours * 60)

def interpolate_position(lat1: float, lng1: float, 
                        lat2: float, lng2: float, 
                        progress: float) -> Tuple[float, float]:
    """
    Интерполяция позиции между двумя точками.
    
    Args:
        lat1 (float): Широта начальной точки
        lng1 (float): Долгота начальной точки
        lat2 (float): Широта конечной точки
        lng2 (float): Долгота конечной точки
        progress (float): Прогресс от 0.0 до 1.0
    
    Returns:
        tuple: Интерполированные координаты (lat, lng)
    """
    # Простая линейная интерполяция
    lat = lat1 + (lat2 - lat1) * progress
    lng = lng1 + (lng2 - lng1) * progress
    
    return (lat, lng)

def get_random_point_in_radius(center_lat: float, center_lng: float, 
                              radius_km: float) -> Tuple[float, float]:
    """
    Генерация случайной точки в заданном радиусе от центра.
    
    Args:
        center_lat (float): Широта центра
        center_lng (float): Долгота центра
        radius_km (float): Радиус в километрах
    
    Returns:
        tuple: Случайные координаты (lat, lng)
    """
    import random
    
    # Случайный угол
    angle = random.uniform(0, 2 * math.pi)
    
    # Случайное расстояние (равномерное распределение по площади)
    distance = radius_km * math.sqrt(random.uniform(0, 1))
    
    # Вычисляем новые координаты
    lat_delta = (distance / 111.0) * math.cos(angle)
    lng_delta = (distance / (111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle)
    
    new_lat = center_lat + lat_delta
    new_lng = center_lng + lng_delta
    
    return (new_lat, new_lng)

def calculate_accuracy_confidence(accuracy_meters: float) -> str:
    """
    Оценка качества GPS сигнала по точности.
    
    Args:
        accuracy_meters (float): Точность в метрах
    
    Returns:
        str: Уровень доверия ('excellent', 'good', 'fair', 'poor')
    """
    if accuracy_meters <= 5:
        return 'excellent'
    elif accuracy_meters <= 15:
        return 'good'
    elif accuracy_meters <= 50:
        return 'fair'
    else:
        return 'poor'

def is_gps_accuracy_acceptable(accuracy_meters: float, max_allowed: float = 50.0) -> bool:
    """
    Проверка приемлемости точности GPS для игры.
    
    Args:
        accuracy_meters (float): Точность в метрах
        max_allowed (float): Максимально допустимая точность
    
    Returns:
        bool: True если точность приемлема
    """
    return accuracy_meters <= max_allowed

class GPSHelper:
    """
    Класс-помощник для работы с GPS координатами.
    Содержит удобные методы для частых операций.
    """
    
    @staticmethod
    def get_delivery_zones(center_lat: float, center_lng: float, 
                          pickup_radius: float = 30, 
                          dropoff_radius: float = 30) -> dict:
        """
        Получение зон для pickup и dropoff.
        
        Args:
            center_lat (float): Широта центра
            center_lng (float): Долгота центра
            pickup_radius (float): Радиус зоны pickup в метрах
            dropoff_radius (float): Радиус зоны dropoff в метрах
        
        Returns:
            dict: Словарь с зонами
        """
        return {
            'pickup': {
                'center': {'lat': center_lat, 'lng': center_lng},
                'radius_meters': pickup_radius
            },
            'dropoff': {
                'center': {'lat': center_lat, 'lng': center_lng},
                'radius_meters': dropoff_radius
            }
        }
    
    @staticmethod
    def check_delivery_status(user_lat: float, user_lng: float,
                            pickup_lat: float, pickup_lng: float,
                            dropoff_lat: float, dropoff_lng: float,
                            pickup_radius: float = 30,
                            dropoff_radius: float = 30) -> dict:
        """
        Проверка статуса доставки относительно зон pickup и dropoff.
        
        Args:
            user_lat (float): Широта пользователя
            user_lng (float): Долгота пользователя
            pickup_lat (float): Широта pickup
            pickup_lng (float): Долгота pickup
            dropoff_lat (float): Широта dropoff
            dropoff_lng (float): Долгота dropoff
            pickup_radius (float): Радиус pickup в метрах
            dropoff_radius (float): Радиус dropoff в метрах
        
        Returns:
            dict: Статус доставки
        """
        in_pickup = is_within_radius(
            pickup_lat, pickup_lng, user_lat, user_lng, pickup_radius
        )
        
        in_dropoff = is_within_radius(
            dropoff_lat, dropoff_lng, user_lat, user_lng, dropoff_radius
        )
        
        distance_to_pickup = calculate_distance_meters(
            user_lat, user_lng, pickup_lat, pickup_lng
        )
        
        distance_to_dropoff = calculate_distance_meters(
            user_lat, user_lng, dropoff_lat, dropoff_lng
        )
        
        return {
            'in_pickup_zone': in_pickup,
            'in_dropoff_zone': in_dropoff,
            'distance_to_pickup': distance_to_pickup,
            'distance_to_dropoff': distance_to_dropoff,
            'pickup_direction': get_compass_direction(
                get_bearing(user_lat, user_lng, pickup_lat, pickup_lng)
            ),
            'dropoff_direction': get_compass_direction(
                get_bearing(user_lat, user_lng, dropoff_lat, dropoff_lng)
            )
        }
    
    @staticmethod
    def validate_order_distance(pickup_lat: float, pickup_lng: float,
                              dropoff_lat: float, dropoff_lng: float,
                              min_distance_km: float = 0.5,
                              max_distance_km: float = 10.0) -> dict:
        """
        Валидация расстояния заказа.
        
        Args:
            pickup_lat (float): Широта pickup
            pickup_lng (float): Долгота pickup
            dropoff_lat (float): Широта dropoff
            dropoff_lng (float): Долгота dropoff
            min_distance_km (float): Минимальное расстояние
            max_distance_km (float): Максимальное расстояние
        
        Returns:
            dict: Результат валидации
        """
        distance = calculate_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        
        is_valid = min_distance_km <= distance <= max_distance_km
        
        return {
            'is_valid': is_valid,
            'distance_km': distance,
            'min_allowed': min_distance_km,
            'max_allowed': max_distance_km,
            'reason': (
                'too_short' if distance < min_distance_km else
                'too_long' if distance > max_distance_km else
                'valid'
            )
        }