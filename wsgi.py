#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI точка входа для продакшен деплоя симулятора курьера.
Используется с Gunicorn или другими WSGI серверами.
"""

import os
from app import create_app, socketio

# Создаем приложение для продакшена
app = create_app('production')

# WSGI приложение с SocketIO
application = socketio

if __name__ == "__main__":
    application.run(app)