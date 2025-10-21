# -*- coding: utf-8 -*-
"""
Сервис для авторизации через Telegram в симуляторе курьера.
Проверяет подлинность данных от Telegram Login Widget.
"""

import hashlib
import hmac
import time
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def verify_telegram_auth(auth_data):
    """
    Проверяет подлинность данных от Telegram Login Widget.
    
    Telegram отправляет данные с хешем, который нужно проверить
    используя секретный ключ (SHA256 хеш от bot token).
    
    Args:
        auth_data (dict): Данные авторизации от Telegram
            - id: Telegram user ID
            - first_name: Имя
            - last_name: Фамилия (опционально)
            - username: @username (опционально)
            - photo_url: URL фото (опционально)
            - auth_date: Unix timestamp авторизации
            - hash: Контрольная сумма
    
    Returns:
        bool: True если данные подлинные, False если нет
    """
    try:
        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не настроен в конфигурации")
            return False
        
        # Получаем хеш из данных
        received_hash = auth_data.get('hash')
        if not received_hash:
            logger.warning("Отсутствует hash в данных от Telegram")
            return False
        
        # Создаём копию данных без хеша для проверки
        check_data = {k: v for k, v in auth_data.items() if k != 'hash'}
        
        # Сортируем данные и создаём строку для проверки
        data_check_string = '\n'.join([f'{k}={v}' for k, v in sorted(check_data.items())])
        
        # Создаём секретный ключ из токена бота
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        
        # Вычисляем хеш
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем хеши
        if calculated_hash != received_hash:
            logger.warning("Хеш не совпадает - данные могли быть подделаны")
            return False
        
        # Проверяем актуальность данных (не старше 1 дня)
        auth_date = int(auth_data.get('auth_date', 0))
        current_time = int(time.time())
        
        if current_time - auth_date > 86400:  # 24 часа
            logger.warning("Данные от Telegram устарели (старше 24 часов)")
            return False
        
        logger.info(f"Telegram авторизация успешно проверена для user_id={auth_data.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке Telegram авторизации: {str(e)}")
        return False

def extract_user_data(auth_data):
    """
    Извлекает данные пользователя из Telegram auth data.
    
    Args:
        auth_data (dict): Данные от Telegram
        
    Returns:
        dict: Словарь с данными пользователя
    """
    return {
        'telegram_id': int(auth_data.get('id')),
        'first_name': auth_data.get('first_name', ''),
        'last_name': auth_data.get('last_name', ''),
        'username': auth_data.get('username'),
        'photo_url': auth_data.get('photo_url'),
        'auth_date': int(auth_data.get('auth_date', 0))
    }

def generate_username_from_telegram(first_name, last_name='', username=None):
    """
    Генерирует никнейм из данных Telegram.
    
    Приоритет:
    1. Telegram @username
    2. Имя + Фамилия
    3. Только имя
    
    Args:
        first_name (str): Имя
        last_name (str): Фамилия
        username (str): Telegram @username
        
    Returns:
        str: Сгенерированный никнейм
    """
    if username:
        return username
    
    if last_name:
        return f"{first_name}_{last_name}".replace(' ', '_')
    
    return first_name.replace(' ', '_')
