# -*- coding: utf-8 -*-
"""
Простая загрузка начальных данных для симулятора курьера.
Проверяет наличие GeoJSON файлов в структуре городов.
"""
import os
import json
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def load_initial_data():
    """
    Проверка наличия необходимых данных при запуске.
    Проверяет новую структуру data/cities/{city_id}/
    """
    try:
        # Проверяем наличие конфигурации городов
        cities_config_path = 'data/cities/cities_config.json'
        
        if not os.path.exists(cities_config_path):
            logger.warning("⚠️  cities_config.json not found")
            return {'cities_config': False}
        
        logger.info("✅ cities_config.json found")
        
        # Читаем конфиг и получаем список городов
        with open(cities_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        cities = [city['id'] for city in config.get('cities', [])]
        files_status = {'cities_config': True}
        
        # Проверяем наличие данных только для городов из конфига
        for city_id in cities:
            restaurants_file = f'data/cities/{city_id}/restaurants.geojson'
            buildings_file = f'data/cities/{city_id}/buildings.geojson'
            
            if os.path.exists(restaurants_file):
                logger.info(f"✅ {city_id}: restaurants.geojson found")
                files_status[f'{city_id}_restaurants'] = True
            else:
                logger.warning(f"⚠️  {city_id}: restaurants.geojson not found")
                files_status[f'{city_id}_restaurants'] = False
            
            if os.path.exists(buildings_file):
                logger.info(f"✅ {city_id}: buildings.geojson found")
                files_status[f'{city_id}_buildings'] = True
            else:
                logger.warning(f"⚠️  {city_id}: buildings.geojson not found")
                files_status[f'{city_id}_buildings'] = False
        
        logger.info("📊 Data files check completed")
        return files_status
        
    except Exception as e:
        logger.error(f"Error checking data files: {str(e)}")
        return {'cities_config': False}
