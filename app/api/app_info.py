# -*- coding: utf-8 -*-
"""
API endpoints для информации о приложении.
Версия, конфигурация, системная информация.
"""

from flask import Blueprint, jsonify
import json
import os
import logging

# Создаем blueprint
app_info_bp = Blueprint('app_info', __name__)

# Настройка логирования
logger = logging.getLogger(__name__)

@app_info_bp.route('/app_info', methods=['GET'])
def get_app_info():
    """
    Получить информацию о приложении из manifest.json.
    Возвращает версию, название и другие данные.
    """
    try:
        # Путь к manifest.json (на уровень выше папки app)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        manifest_path = os.path.join(base_dir, 'manifest.json')
        
        # Читаем файл
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        logger.info("App info loaded from manifest.json")
        
        return jsonify({
            'success': True,
            'data': {
                'name': manifest_data.get('name', 'Q-RYER'),
                'version': manifest_data.get('version', '1.0.0'),
                'build': manifest_data.get('build', ''),
                'description': manifest_data.get('description', ''),
                'release_date': manifest_data.get('release_date', '')
            }
        })
        
    except FileNotFoundError:
        logger.error("manifest.json not found")
        return jsonify({
            'success': False,
            'error': 'manifest.json not found'
        }), 404
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in manifest.json: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Invalid JSON format in manifest.json'
        }), 500
        
    except Exception as e:
        logger.error(f"Error loading app info: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load app info'
        }), 500