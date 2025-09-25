# -*- coding: utf-8 -*-
"""
API endpoints для авторизации в симуляторе курьера.
Google OAuth и гостевой вход.
"""

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import User
import logging
import uuid
import requests

# Создаем blueprint
auth_bp = Blueprint('auth', __name__)

# Настройка логирования
logger = logging.getLogger(__name__)

@auth_bp.route('/guest_login', methods=['POST'])
def guest_login():
    """
    Гостевой вход без регистрации.
    Создает временного пользователя.
    """
    try:
        data = request.get_json() or {}
        username = data.get('username', f'Guest_{uuid.uuid4().hex[:8]}')
        
        # Проверяем, что имя пользователя не занято
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            username = f'{username}_{uuid.uuid4().hex[:4]}'
        
        # Создаем гостевого пользователя
        user = User.create_user(username=username)
        
        logger.info(f"Created guest user: {user.username} (ID: {user.id})")
        
        return jsonify({
            'success': True,
            'message': 'Guest login successful',
            'user': user.to_dict(),
            'session_type': 'guest'
        })
        
    except Exception as e:
        logger.error(f"Error in guest login: {str(e)}")
        return jsonify({'error': 'Failed to create guest user'}), 500

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
        
        # Ищем существующего пользователя
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
            # Создаем нового пользователя
            # Проверяем уникальность имени пользователя
            base_username = name
            counter = 1
            while User.query.filter_by(username=name).first():
                name = f"{base_username}_{counter}"
                counter += 1
            
            user = User.create_user(
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
def delete_guest_account():
    """
    Удаление гостевого аккаунта.
    Только для гостевых пользователей без Google ID.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        confirm = data.get('confirm', False)
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        if not confirm:
            return jsonify({'error': 'Account deletion must be confirmed'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем, что это гостевой пользователь
        if user.google_id:
            return jsonify({'error': 'Cannot delete Google-linked account'}), 403
        
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
        
        logger.info(f"Deleted guest account: {username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
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
        return jsonify({'error': 'Failed to update profile'}), 500