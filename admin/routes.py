# -*- coding: utf-8 -*-
"""
Маршруты для админ-панели симулятора курьера.
Простая авторизация по паролю из .env
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import os
import logging

# Получаем абсолютный путь к папке admin
admin_dir = os.path.dirname(os.path.abspath(__file__))

# Создаем blueprint для админки с абсолютными путями
admin_pages_bp = Blueprint(
    'admin_pages',
    __name__,
    template_folder=os.path.join(admin_dir, 'templates'),
    static_folder=os.path.join(admin_dir, 'static'),
    static_url_path='/static'  # Изменили с /admin/static на /static
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем пароль из переменных окружения
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def check_auth():
    """Проверка авторизации администратора"""
    return session.get('admin_authenticated', False)

def require_auth(f):
    """Декоратор для защиты маршрутов"""
    def decorated_function(*args, **kwargs):
        if not check_auth():
            return redirect(url_for('admin_pages.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_pages_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в админку"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            logger.info("Admin logged in successfully")
            return redirect(url_for('admin_pages.users'))
        else:
            logger.warning("Failed admin login attempt")
            flash('Неверный пароль', 'error')
    
    return render_template('admin/login.html')

@admin_pages_bp.route('/logout')
def logout():
    """Выход из админки"""
    session.pop('admin_authenticated', None)
    logger.info("Admin logged out")
    return redirect(url_for('admin_pages.login'))

@admin_pages_bp.route('/')
@require_auth
def index():
    """Главная страница админки - редирект на users"""
    return redirect(url_for('admin_pages.users'))

@admin_pages_bp.route('/users')
@require_auth
def users():
    """Страница управления пользователями"""
    return render_template('admin/users.html')

@admin_pages_bp.route('/orders')
@require_auth
def orders():
    """Страница управления заказами"""
    return render_template('admin/orders.html')

@admin_pages_bp.route('/reports')
@require_auth
def reports():
    """Страница управления жалобами"""
    return render_template('admin/reports.html')

@admin_pages_bp.route('/config')
@require_auth
def config():
    """Страница настроек системы"""
    return render_template('admin/config.html')
