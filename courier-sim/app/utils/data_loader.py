# -*- coding: utf-8 -*-
"""
Простая загрузка начальных данных для симулятора курьера.
Проверяет наличие GeoJSON файлов.
"""

import os
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def load_initial_data():
    """
    Проверка наличия необходимых данных при запуске.
    """
    try:
        # Проверяем наличие файлов данных
        restaurants_file = 'data/restaurants.geojson'
        buildings_file = 'data/buildings.geojson'
        
        files_status = {
            'restaurants': os.path.exists(restaurants_file),
            'buildings': os.path.exists(buildings_file)
        }
        
        if files_status['restaurants']:
            logger.info("✅ restaurants.geojson found")
        else:
            logger.warning("⚠️  restaurants.geojson not found in data/")
        
        if files_status['buildings']:
            logger.info("✅ buildings.geojson found")
        else:
            logger.warning("⚠️  buildings.geojson not found in data/")
        
        if not any(files_status.values()):
            logger.error("❌ No data files found! Please add restaurants.geojson and buildings.geojson to data/ folder")
        else:
            logger.info("📊 Data files check completed")
        
        return files_status
        
    except Exception as e:
        logger.error(f"Error checking data files: {str(e)}")
        return {'restaurants': False, 'buildings': False}