# -*- coding: utf-8 -*-
"""
Конфигурация для Flask приложения симулятора курьера.
Содержит настройки для разных сред разработки.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Базовая директория проекта
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Базовая конфигурация для всех сред"""

    # Секретный ключ для сессий и JWT
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-super-secret-key-change-in-production")

    # Конфигурация базы данных
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        f"sqlite:///{os.path.join(basedir, 'courier_dev.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # Конфигурация SocketIO
    SOCKETIO_ASYNC_MODE = "threading"

    # Google OAuth настройки
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Mapbox настройки (берём токен из .env, если его нет → пустая строка)
    MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")

    # Firebase Cloud Messaging
    FCM_SERVER_KEY = os.environ.get("FCM_SERVER_KEY")

    # Игровая экономика - базовые настройки
    GAME_CONFIG = {
        "base_payment": 1.50,
        "pickup_fee": 0.50,
        "dropoff_fee": 0.50,
        "distance_rate": 0.80,   # $ за км
        "on_time_bonus": 1.00,

        # Радиусы и расстояния
        "pickup_radius": 30,     # метры
        "dropoff_radius": 30,    # метры
        "max_order_distance": 10000,  # метры (10 км)
        "min_order_distance": 500,    # метры (0.5 км)

        # Таймеры
        "pickup_timeout": 3600,      # 1 час
        "delivery_base_time": 300,   # 5 минут
        "delivery_speed_kmh": 5,     # км/ч для расчёта таймера

        # Настройки поиска заказов
        "order_search_radius": 5000, # метры (5 км)
        "min_search_time": 5,        # секунды
        "max_search_time": 30,       # секунды

        # GPS точность
        "max_gps_accuracy": 50       # метры
    }

    # Настройки логирования
    LOG_LEVEL = "INFO"
    LOG_FILE = os.path.join(basedir, "logs", "courier_sim.log")

    # Время запуска сервера
    SERVER_START_TIME = None

    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией"""
        import datetime
        Config.SERVER_START_TIME = datetime.datetime.utcnow().isoformat()


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    GAME_CONFIG = Config.GAME_CONFIG.copy()
    GAME_CONFIG.update({
        "pickup_radius": 100,
        "dropoff_radius": 100,
        "min_search_time": 2,
        "max_search_time": 10,
    })


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    SQLALCHEMY_RECORD_QUERIES = False
    LOG_LEVEL = "WARNING"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "postgresql://courier_user:courier_pass@localhost/courier_simulator"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists("logs"):
            os.mkdir("logs")

        file_handler = RotatingFileHandler(
            "logs/courier_sim.log", maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Courier Simulator startup")


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    GAME_CONFIG = Config.GAME_CONFIG.copy()
    GAME_CONFIG.update({
        "pickup_radius": 10,
        "dropoff_radius": 10,
        "pickup_timeout": 60,
        "min_search_time": 1,
        "max_search_time": 3,
    })
