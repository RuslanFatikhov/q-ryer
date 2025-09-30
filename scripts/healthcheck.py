#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт проверки здоровья приложения (healthcheck).
Проверяет доступность всех критичных компонентов системы.

Использование:
    python scripts/healthcheck.py
    
Возвращает:
    0 - все компоненты работают нормально
    1 - обнаружены проблемы
"""

import sys
import os
import json
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_env_file():
    """Проверка наличия .env файла"""
    env_path = project_root / '.env'
    if not env_path.exists():
        return False, "⚠️  .env file not found. Copy .env.example to .env"
    return True, "✅ .env file exists"


def check_data_files():
    """Проверка наличия GeoJSON файлов с данными"""
    issues = []
    
    # Проверяем наличие файлов
    restaurants_path = project_root / 'data' / 'restaurants.geojson'
    buildings_path = project_root / 'data' / 'buildings.geojson'
    
    if not restaurants_path.exists():
        issues.append("⚠️  restaurants.geojson not found in data/")
    else:
        # Проверяем валидность JSON
        try:
            with open(restaurants_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data.get('features', []))
                issues.append(f"✅ restaurants.geojson found ({count} restaurants)")
        except json.JSONDecodeError:
            issues.append("❌ restaurants.geojson is not valid JSON")
    
    if not buildings_path.exists():
        issues.append("⚠️  buildings.geojson not found in data/")
    else:
        # Проверяем валидность JSON
        try:
            with open(buildings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data.get('features', []))
                issues.append(f"✅ buildings.geojson found ({count} buildings)")
        except json.JSONDecodeError:
            issues.append("❌ buildings.geojson is not valid JSON")
    
    has_errors = any('❌' in issue for issue in issues)
    return not has_errors, '\n'.join(issues)


def check_database():
    """Проверка подключения к базе данных"""
    try:
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            # Пробуем выполнить простой запрос
            db.session.execute(db.text('SELECT 1'))
            return True, "✅ Database connection successful"
    except Exception as e:
        return False, f"❌ Database connection failed: {str(e)}"


def check_models():
    """Проверка корректности моделей БД"""
    try:
        from app import create_app, db
        from app.models import User, Order, Report
        
        app = create_app()
        with app.app_context():
            # Проверяем, что таблицы созданы
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['users', 'orders', 'reports']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                return False, f"❌ Missing tables: {', '.join(missing_tables)}"
            
            return True, f"✅ All tables exist ({len(tables)} total)"
    except Exception as e:
        return False, f"❌ Models check failed: {str(e)}"


def check_config():
    """Проверка конфигурации приложения"""
    try:
        from app import create_app
        
        app = create_app()
        
        issues = []
        
        # Проверяем критичные конфигурации
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key':
            issues.append("⚠️  SECRET_KEY is using default value (insecure for production)")
        else:
            issues.append("✅ SECRET_KEY is configured")
        
        if not app.config.get('MAPBOX_ACCESS_TOKEN'):
            issues.append("❌ MAPBOX_ACCESS_TOKEN is not set")
        else:
            issues.append("✅ MAPBOX_ACCESS_TOKEN is configured")
        
        if app.config.get('SQLALCHEMY_DATABASE_URI'):
            issues.append("✅ Database URI is configured")
        else:
            issues.append("❌ Database URI is not set")
        
        # Проверяем игровую конфигурацию
        game_config = app.config.get('GAME_CONFIG', {})
        if game_config:
            issues.append(f"✅ Game config loaded ({len(game_config)} parameters)")
        else:
            issues.append("⚠️  Game config is empty")
        
        has_errors = any('❌' in issue for issue in issues)
        return not has_errors, '\n'.join(issues)
    except Exception as e:
        return False, f"❌ Config check failed: {str(e)}"


def check_dependencies():
    """Проверка установленных зависимостей"""
    try:
        required_packages = [
            'flask',
            'flask_sqlalchemy',
            'flask_socketio',
            'flask_cors',
            'python-dotenv'
        ]
        
        issues = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                issues.append(f"✅ {package}")
            except ImportError:
                issues.append(f"❌ {package} not installed")
        
        has_errors = any('❌' in issue for issue in issues)
        return not has_errors, '\n'.join(issues)
    except Exception as e:
        return False, f"❌ Dependencies check failed: {str(e)}"


def main():
    """Главная функция проверки здоровья"""
    print("=" * 60)
    print("🏥 COURIER SIMULATOR - HEALTH CHECK")
    print("=" * 60)
    print()
    
    checks = [
        ("Environment File", check_env_file),
        ("Data Files", check_data_files),
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Database", check_database),
        ("Models", check_models),
    ]
    
    results = []
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"📋 Checking {check_name}...")
        try:
            passed, message = check_func()
            results.append((check_name, passed, message))
            print(f"   {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            results.append((check_name, False, f"❌ Unexpected error: {str(e)}"))
            print(f"   ❌ Unexpected error: {str(e)}")
            all_passed = False
        print()
    
    # Итоговый отчет
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    
    for check_name, passed, _ in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    print()
    print(f"Result: {passed_count}/{total_count} checks passed")
    
    if all_passed:
        print("\n✅ All checks passed! System is healthy.")
        return 0
    else:
        print("\n❌ Some checks failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())