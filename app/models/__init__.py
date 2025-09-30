# -*- coding: utf-8 -*-
"""
Модуль моделей для симулятора курьера.
Импортирует только нужные модели.
"""

# Импортируем модели базы данных
from .user import User
from .order import Order
from .report import Report

# Экспортируем только активные модели для использования в других модулях
# Это позволяет делать: from app.models import User, Order, Report
__all__ = ['User', 'Order', 'Report']