# -*- coding: utf-8 -*-
"""
Сервис для отправки email в симуляторе курьера.
Используется для подтверждения почты при регистрации.
"""

import secrets
import time
from flask import current_app
from flask_mail import Message
from app import mail
import logging

logger = logging.getLogger(__name__)

# Временное хранилище кодов подтверждения
# В продакшене используйте Redis или базу данных
verification_codes = {}

def generate_verification_code():
    """
    Генерирует 6-значный код подтверждения.
    
    Returns:
        str: 6-значный код
    """
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def store_verification_code(email, code):
    """
    Сохраняет код подтверждения с временем истечения.
    
    Args:
        email (str): Email пользователя
        code (str): Код подтверждения
    """
    expiry_time = time.time() + current_app.config.get('EMAIL_VERIFICATION_CODE_EXPIRY', 900)
    verification_codes[email.lower()] = {
        'code': code,
        'expires_at': expiry_time
    }
    logger.info(f"Код подтверждения сохранён для {email}")

def get_verification_code(email):
    """
    Получает сохранённый код подтверждения.
    
    Args:
        email (str): Email пользователя
        
    Returns:
        dict or None: Данные кода или None если не найден
    """
    return verification_codes.get(email.lower())

def delete_verification_code(email):
    """
    Удаляет использованный код подтверждения.
    
    Args:
        email (str): Email пользователя
    """
    if email.lower() in verification_codes:
        del verification_codes[email.lower()]
        logger.info(f"Код подтверждения удалён для {email}")

def is_code_expired(email):
    """
    Проверяет, истёк ли код подтверждения.
    
    Args:
        email (str): Email пользователя
        
    Returns:
        bool: True если код истёк или не существует
    """
    code_data = get_verification_code(email)
    if not code_data:
        return True
    return time.time() > code_data['expires_at']

def send_verification_email(email, code):
    """
    Отправляет email с кодом подтверждения.
    
    Args:
        email (str): Email получателя
        code (str): Код подтверждения
        
    Returns:
        bool: True если отправка успешна, False если ошибка
    """
    try:
        msg = Message(
            subject='Код подтверждения регистрации',
            recipients=[email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        # HTML версия письма
        msg.html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 0 auto; }}
                .header {{ color: #2c3e50; text-align: center; }}
                .code {{ font-size: 32px; font-weight: bold; color: #3498db; text-align: center; 
                         letter-spacing: 5px; padding: 20px; background-color: #ecf0f1; 
                         border-radius: 5px; margin: 20px 0; }}
                .footer {{ color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="header">🚴 Добро пожаловать в Симулятор Курьера!</h2>
                <p>Вы получили это письмо, потому что регистрируетесь в нашей игре.</p>
                <p>Ваш код подтверждения:</p>
                <div class="code">{code}</div>
                <p>Код действителен <strong>15 минут</strong>.</p>
                <p>Если вы не регистрировались в игре, просто проигнорируйте это письмо.</p>
                <div class="footer">
                    <p>© 2025 Симулятор Курьера. Все права защищены.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия (на случай если HTML не поддерживается)
        msg.body = f"""
        Добро пожаловать в Симулятор Курьера!
        
        Ваш код подтверждения: {code}
        
        Код действителен 15 минут.
        
        Если вы не регистрировались в игре, просто проигнорируйте это письмо.
        """
        
        mail.send(msg)
        logger.info(f"Email с кодом подтверждения отправлен на {email}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки email на {email}: {str(e)}")
        return False

def send_password_reset_email(email, reset_code):
    """
    Отправляет email с кодом для восстановления пароля.
    
    Args:
        email (str): Email получателя
        reset_code (str): Код восстановления
        
    Returns:
        bool: True если отправка успешна
    """
    try:
        msg = Message(
            subject='Восстановление пароля',
            recipients=[email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        msg.html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 0 auto; }}
                .header {{ color: #e74c3c; text-align: center; }}
                .code {{ font-size: 32px; font-weight: bold; color: #e74c3c; text-align: center; 
                         letter-spacing: 5px; padding: 20px; background-color: #fadbd8; 
                         border-radius: 5px; margin: 20px 0; }}
                .footer {{ color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="header">🔐 Восстановление пароля</h2>
                <p>Вы запросили восстановление пароля для вашего аккаунта.</p>
                <p>Ваш код восстановления:</p>
                <div class="code">{reset_code}</div>
                <p>Код действителен <strong>15 минут</strong>.</p>
                <p><strong>Важно:</strong> Если вы не запрашивали восстановление пароля, немедленно свяжитесь с нами.</p>
                <div class="footer">
                    <p>© 2025 Симулятор Курьера. Все права защищены.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.body = f"""
        Восстановление пароля
        
        Ваш код восстановления: {reset_code}
        
        Код действителен 15 минут.
        
        Если вы не запрашивали восстановление пароля, немедленно свяжитесь с нами.
        """
        
        mail.send(msg)
        logger.info(f"Email с кодом восстановления отправлен на {email}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки email восстановления на {email}: {str(e)}")
        return False
