#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа для симулятора курьера.
Запуск Flask приложения с SocketIO поддержкой.
"""

import os
import logging
from app import create_app, socketio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    # Параметры запуска
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5200))
    
    print(f"""
🚚 Courier Simulator Starting...
📍 Host: {host}:{port}
🐛 Debug: {debug}
🌍 Environment: {os.environ.get('FLASK_ENV', 'development')}
""")
    
    # Запускаем с SocketIO поддержкой
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True  # Для разработки
    )