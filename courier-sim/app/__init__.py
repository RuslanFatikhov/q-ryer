# -*- coding: utf-8 -*-
"""
Главный модуль инициализации Flask приложения для симулятора курьера.
Настраивает базу данных, SocketIO, CORS и регистрирует blueprints.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
import os

# Инициализация расширений
db = SQLAlchemy()
socketio = SocketIO()

def create_app(config_name=None):
    """
    Factory функция для создания Flask приложения
    
    Args:
        config_name (str): Название конфигурации ('development', 'production')
    
    Returns:
        Flask: Настроенное приложение
    """
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    app.config.from_object(config_map.get(config_name, DevelopmentConfig))
    
    # Инициализируем расширения
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    CORS(app)
    
    # Регистрируем blueprints
    from app.api.auth import auth_bp
    from app.api.player import player_bp
    from app.api.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(player_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Регистрируем SocketIO обработчики
    from app.socketio_handlers import game_events
    
    # Создаем таблицы в базе данных
    with app.app_context():
        db.create_all()
        
        # Загружаем начальные данные
        from app.utils.data_loader import load_initial_data
        load_initial_data()
    
    # Добавляем базовые маршруты
    @app.route('/')
    def index():
        return {
            'status': 'success',
            'message': 'Courier Simulator API is running',
            'version': '1.0.0'
        }
    
    @app.route('/api/health')
    def health_check():
        try:
            db.session.execute('SELECT 1')
            return {
                'status': 'healthy',
                'database': 'connected'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }, 500
    
    return app
