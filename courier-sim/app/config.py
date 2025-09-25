# -*- coding: utf-8 -*-
"""
Конфигурация для Flask приложения симулятора курьера.
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "courier_dev.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
