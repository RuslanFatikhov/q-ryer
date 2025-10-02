# -*- coding: utf-8 -*-
"""
API endpoints для авторизации в симуляторе курьера.
Регистрация, вход по email/username + пароль, Google OAuth.
"""

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import User
import logging
import re
import requests

# Создаем blueprint
auth_bp = Blueprint('auth', __name__)

# Настройка логирования
logger = logging.getLogger(__name__)

def validate_email(email):
    """Проверка корректности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Проверка надёжности пароля.
    Минимум 6 символов.
    """
    if len(password) < 6:
        return False, "Пароль должен содержать минимум 6 символов"
    return True, "OK"

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя.
    
    Ожидаемые данные:
    {
        "username": "nickname",
        "email": "user@example.com",
        "password": "password123"
    }
    """
    try:
        data = request.get_json()
        
        # Проверка наличия всех полей
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Валидация полей
        if not username:
            return jsonify({'error': 'Никнейм обязателен'}), 400
        
        if not email:
            return jsonify({'error': 'Email обязателен'}), 400
        
        if not password:
            return jsonify({'error': 'Пароль обязателен'}), 400
        
        # Проверка формата email
        if not validate_email(email):
            return jsonify({'error': 'Некорректный email'}), 400
        
        # Проверка надёжности пароля
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Проверка уникальности username
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Никнейм уже занят'}), 400
        
        # Проверка уникальности email
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email уже зарегистрирован'}), 400
        
        # Создаём пользователя
        user = User.create_user(username=username, email=email, password=password)
        
        logger.info(f"Зарегистрирован новый пользователь: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'message': 'Регистрация успешна',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Ошибка при регистрации'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Вход пользователя по username/email + пароль.
    
    Ожидаемые данные:
    {
        "login": "username или email",
        "password": "password123"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        login = data.get('login', '').strip()
        password = data.get('password', '')
        
        # Валидация полей
        if not login:
            return jsonify({'error': 'Логин или email обязателен'}), 400
        
        if not password:
            return jsonify({'error': 'Пароль обязателен'}), 400
        
        # Ищем пользователя по username или email
        user = None
        if validate_email(login):
            # Если это email
            user = User.query.filter_by(email=login.lower()).first()
        else:
            # Если это username
            user = User.query.filter_by(username=login).first()
        
        # Проверяем существование пользователя
        if not user:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
        
        # Проверяем, что у пользователя есть пароль (не Google OAuth)
        if not user.password_hash:
            return jsonify({'error': 'Этот аккаунт связан с Google. Войдите через Google'}), 401
        
        # Проверяем пароль
        if not user.check_password(password):
            return jsonify({'error': 'Неверный логин или пароль'}), 401
        
        # Проверяем активность аккаунта
        if not user.is_active:
            return jsonify({'error': 'Аккаунт заблокирован'}), 403
        
        logger.info(f"Пользователь вошёл: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'message': 'Вход выполнен успешно',
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Ошибка при входе: {str(e)}")
        return jsonify({'error': 'Ошибка при входе'}), 500

@auth_bp.route('/google_login', methods=['POST'])
def google_login():
    """
    Вход через Google OAuth.
    Проверяет Google ID token и создает/обновляет пользователя.
    """
    try:
        data = request.get_json()
        id_token = data.get('id_token')
        
        if not id_token:
            return jsonify({'error': 'Google ID token is required'}), 400
        
        # Проверяем токен Google
        google_user = verify_google_token(id_token)
        if not google_user:
            return jsonify({'error': 'Invalid Google token'}), 401
        
        google_id = google_user['sub']
        email = google_user.get('email')
        name = google_user.get('name', email.split('@')[0] if email else 'User')
        
        # Ищем существующего пользователя по google_id
        user = User.query.filter_by(google_id=google_id).first()
        
        if user:
            # Обновляем данные существующего пользователя
            if email and user.email != email:
                user.email = email
            if name and user.username != name:
                # Проверяем уникальность имени
                existing_username = User.query.filter_by(username=name).first()
                if not existing_username or existing_username.id == user.id:
                    user.username = name
            
            user.updated_at = db.func.now()
            db.session.commit()
            
            logger.info(f"Google user logged in: {user.username} (ID: {user.id})")
            
        else:
            # Проверяем, не занят ли email
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                return jsonify({'error': 'Email уже зарегистрирован. Войдите через форму входа'}), 409
            
            # Проверяем уникальность имени пользователя
            base_username = name
            counter = 1
            while User.query.filter_by(username=name).first():
                name = f"{base_username}_{counter}"
                counter += 1
            
            # Создаём Google пользователя БЕЗ пароля
            user = User.create_google_user(
                username=name,
                email=email,
                google_id=google_id
            )
            
            logger.info(f"Created new Google user: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'message': 'Google login successful',
            'user': user.to_dict(),
            'session_type': 'google'
        })
        
    except Exception as e:
        logger.error(f"Error in Google login: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to authenticate with Google'}), 500

@auth_bp.route('/verify_session', methods=['POST'])
def verify_session():
    """
    Проверка активной сессии пользователя.
    Используется для восстановления сессии при перезагрузке приложения.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем, что пользователь активен
        if not user.is_active:
            return jsonify({'error': 'User account is disabled'}), 403
        
        logger.info(f"Session verified for user: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'active_order': user.get_active_order().to_dict() if user.get_active_order() else None
        })
        
    except Exception as e:
        logger.error(f"Error verifying session: {str(e)}")
        return jsonify({'error': 'Failed to verify session'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Выход пользователя из системы.
    Устанавливает статус офлайн.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем, нет ли активного заказа
        active_order = user.get_active_order()
        if active_order:
            logger.warning(f"User {user.username} tried to logout with active order {active_order.id}")
            return jsonify({
                'error': 'Cannot logout with active order',
                'active_order': active_order.to_dict()
            }), 400
        
        # Устанавливаем статус офлайн
        user.set_online_status(False)
        
        logger.info(f"User logged out: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return jsonify({'error': 'Failed to logout'}), 500

@auth_bp.route('/delete_account', methods=['POST'])
def delete_account():
    """
    Удаление аккаунта пользователя.
    Только для пользователей без активных заказов.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        password = data.get('password')
        confirm = data.get('confirm', False)
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        if not confirm:
            return jsonify({'error': 'Account deletion must be confirmed'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Если у пользователя есть пароль - проверяем его
        if user.password_hash:
            if not password:
                return jsonify({'error': 'Password required for account deletion'}), 400
            if not user.check_password(password):
                return jsonify({'error': 'Incorrect password'}), 401
        
        # Проверяем, нет ли активного заказа
        active_order = user.get_active_order()
        if active_order:
            return jsonify({
                'error': 'Cannot delete account with active order',
                'active_order': active_order.to_dict()
            }), 400
        
        username = user.username
        
        # Удаляем пользователя (каскадное удаление заказов и отчетов)
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Deleted account: {username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete account'}), 500

def verify_google_token(id_token: str) -> dict:
    """
    Проверка Google ID token.
    
    Args:
        id_token (str): Google ID token
    
    Returns:
        dict: Данные пользователя Google или None
    """
    try:
        # URL для проверки Google токена
        google_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
        
        response = requests.get(google_url, timeout=10)
        
        if response.status_code == 200:
            token_info = response.json()
            
            # Проверяем, что токен для нашего приложения
            client_id = current_app.config.get('GOOGLE_CLIENT_ID')
            if client_id and token_info.get('aud') != client_id:
                logger.warning(f"Google token audience mismatch: {token_info.get('aud')} != {client_id}")
                return None
            
            # Проверяем, что токен не истек
            if 'exp' in token_info:
                import time
                if int(token_info['exp']) < time.time():
                    logger.warning("Google token expired")
                    return None
            
            return token_info
        else:
            logger.error(f"Google token verification failed: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Network error verifying Google token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Google token: {str(e)}")
        return None

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """
    Получение профиля пользователя.
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Получаем статистику пользователя
        stats = user.get_statistics()
        
        return jsonify({
            'user': user.to_dict(),
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@auth_bp.route('/update_profile', methods=['POST'])
def update_profile():
    """
    Обновление профиля пользователя.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Обновляем имя пользователя если указано
        if username and username != user.username:
            # Проверяем уникальность
            existing = User.query.filter_by(username=username).first()
            if existing and existing.id != user.id:
                return jsonify({'error': 'Username already taken'}), 409
            
            old_username = user.username
            user.username = username
            user.updated_at = db.func.now()
            db.session.commit()
            
            logger.info(f"Username updated: {old_username} → {username}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500
