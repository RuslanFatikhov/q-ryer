# -*- coding: utf-8 -*-
"""
Конфигурация для Flask приложения симулятора курьера.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем .env перед обращением к os.environ
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "courier_dev.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mapbox
    MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')

    GAME_CONFIG = {
        'base_payment': 1.50,
        'pickup_fee': 0.50,
        'dropoff_fee': 0.50,
        'distance_rate': 0.80,
        'on_time_bonus': 1.00,
        'pickup_radius': 30,
        'dropoff_radius': 30,
        'delivery_speed_kmh': 5,
        'delivery_base_time': 300,
        'max_gps_accuracy': 50
    }

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Игровая конфигурация для экономики и геймплея
GAME_CONFIG = {
    'base_payment': 1.50,
    'pickup_fee': 0.50,
    'dropoff_fee': 0.50,
    'distance_rate': 0.80,
    'on_time_bonus': 1.00,
    'pickup_radius': 30,      # метры
    'dropoff_radius': 30,     # метры
    'delivery_speed_kmh': 5,  # км/ч скорость доставки
    'delivery_base_time': 300, # секунды базовое время
    'pickup_timeout': 3600,   # секунды (1 час) на pickup
    'max_gps_accuracy': 50    # метры максимальная неточность GPS
}
