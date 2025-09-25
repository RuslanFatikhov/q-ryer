# -*- coding: utf-8 -*-
"""
Экономические расчеты для симулятора курьера.
"""

from typing import Dict, Optional
from flask import current_app

def calculate_payout(distance_km: float, config: Optional[Dict] = None) -> float:
    """Расчет базовой выплаты за заказ без учета бонусов"""
    if config is None:
        config = current_app.config['GAME_CONFIG']
    
    base_payment = config['base_payment']
    pickup_fee = config['pickup_fee']
    dropoff_fee = config['dropoff_fee']
    distance_rate = config['distance_rate']
    
    total_payout = base_payment + pickup_fee + dropoff_fee + (distance_km * distance_rate)
    return round(total_payout, 2)

def calculate_final_payout(distance_km: float, on_time: bool, config: Optional[Dict] = None) -> Dict:
    """Расчет финальной выплаты с учетом бонуса за своевременность"""
    if config is None:
        config = current_app.config['GAME_CONFIG']
    
    base_payment = config['base_payment']
    pickup_fee = config['pickup_fee']
    dropoff_fee = config['dropoff_fee']
    distance_amount = distance_km * config['distance_rate']
    bonus_amount = config['on_time_bonus'] if on_time else 0.0
    
    total = base_payment + pickup_fee + dropoff_fee + distance_amount + bonus_amount
    
    return {
        'base_payment': round(base_payment, 2),
        'pickup_fee': round(pickup_fee, 2),
        'dropoff_fee': round(dropoff_fee, 2),
        'distance_amount': round(distance_amount, 2),
        'bonus_amount': round(bonus_amount, 2),
        'total': round(total, 2),
        'on_time': on_time,
        'distance_km': round(distance_km, 2)
    }

def calculate_timer(distance_km: float, config: Optional[Dict] = None) -> int:
    """Расчет таймера доставки в секундах"""
    if config is None:
        config = current_app.config['GAME_CONFIG']
    
    delivery_speed_kmh = config['delivery_speed_kmh']
    delivery_base_time = config['delivery_base_time']
    
    travel_time_seconds = (distance_km / delivery_speed_kmh) * 3600
    total_time_seconds = travel_time_seconds + delivery_base_time
    
    return int(total_time_seconds)

def calculate_delivery_stats(distance_km: float, config: Optional[Dict] = None) -> Dict:
    """Расчет всех параметров доставки"""
    if config is None:
        config = current_app.config['GAME_CONFIG']
    
    base_payout = calculate_payout(distance_km, config)
    timer_seconds = calculate_timer(distance_km, config)
    estimated_minutes = timer_seconds // 60
    potential_with_bonus = base_payout + config['on_time_bonus']
    
    return {
        'distance_km': round(distance_km, 2),
        'base_payout': round(base_payout, 2),
        'potential_payout_with_bonus': round(potential_with_bonus, 2),
        'timer_seconds': timer_seconds,
        'estimated_minutes': estimated_minutes,
        'bonus_available': config['on_time_bonus']
    }
