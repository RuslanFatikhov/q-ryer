#!/usr/bin/env python3

from app import create_app, db
from app.models.user import User

def create_test_user():
    """Создает тестового пользователя с ID=1"""
    app = create_app()
    
    with app.app_context():
        # Проверяем, есть ли уже пользователь с ID=1
        existing_user = User.query.get(1)
        if existing_user:
            print(f"✅ Тестовый пользователь уже существует: {existing_user.username} (ID: {existing_user.id})")
            return existing_user
        
        # Создаем нового тестового пользователя
        test_user = User.create_user(
            username="TestDriver",
            email="test@courier-sim.local"
        )
        
        print(f"✅ Создан тестовый пользователь: {test_user.username} (ID: {test_user.id})")
        return test_user

if __name__ == "__main__":
    create_test_user()
