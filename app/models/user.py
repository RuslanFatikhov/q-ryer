# -*- coding: utf-8 -*-
"""
Модель пользователя для симулятора курьера.
"""

from datetime import datetime
from app import db
from sqlalchemy import func

class User(db.Model):
    """Модель пользователя/игрока в симуляторе курьера"""
    
    __tablename__ = 'users'
    
    # Основные поля
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Пароль (хэшированный)
    password_hash = db.Column(db.String(255), nullable=True)
    
    # Игровая информация
    balance = db.Column(db.Float, default=0.0, nullable=False)
    total_deliveries = db.Column(db.Integer, default=0, nullable=False)
    
    # Настройки поиска заказов
    # Радиус поиска в километрах (диапазон: 3-25 км, по умолчанию 5 км)
    search_radius_km = db.Column(db.Integer, default=5, nullable=False)
    
    # Статус пользователя
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    
    # Позиция и активность
    last_position_lat = db.Column(db.Float, nullable=True)
    last_position_lng = db.Column(db.Float, nullable=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связи с другими моделями (без backref, так как они определены в других моделях)
    orders = db.relationship('Order', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    

    def set_password(self, password):
        """
        Устанавливает хэшированный пароль.
        
        Args:
            password (str): Пароль в открытом виде
        """
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Проверяет пароль пользователя.
        
        Args:
            password (str): Пароль для проверки
            
        Returns:
            bool: True если пароль правильный, иначе False
        """
        from werkzeug.security import check_password_hash
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}(id={self.id})>'
    
    def to_dict(self):
        """Преобразование объекта пользователя в словарь для JSON"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'balance': round(self.balance, 2),
            'total_deliveries': self.total_deliveries,
            'search_radius_km': self.search_radius_km,
            'is_online': self.is_online,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat()
        }
    
    def update_balance(self, amount):
        """Обновление баланса пользователя"""
        self.balance += amount
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self.balance
    
    def update_position(self, lat, lng):
        """Обновление позиции пользователя"""
        self.last_position_lat = lat
        self.last_position_lng = lng
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def set_online_status(self, is_online):
        """Установка статуса онлайн/офлайн"""
        self.is_online = is_online
        if is_online:
            self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_search_radius(self, radius_km):
        """Обновление радиуса поиска заказов (1-25 км)"""
        # Валидация радиуса
        if not isinstance(radius_km, (int, float)):
            raise ValueError("Радиус должен быть числом")
        
        if radius_km < 1 or radius_km > 25:
            raise ValueError("Радиус должен быть от 1 до 25 км")
        
        self.search_radius_km = int(radius_km)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self.search_radius_km
    
    def increment_deliveries(self):
        """Увеличение счетчика доставок на 1"""
        self.total_deliveries += 1
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_active_order(self):
        """Получение активного заказа пользователя (pending или active)"""
        from .order import Order
        return Order.query.filter_by(user_id=self.id).filter(
            Order.status.in_(['pending', 'active'])
        ).first()
    
    def get_statistics(self):
        """Получение статистики пользователя"""
        from .order import Order
        
        completed_orders = Order.query.filter_by(user_id=self.id, status='completed').count()
        cancelled_orders = Order.query.filter_by(user_id=self.id, status='cancelled').count()
        total_earnings = db.session.query(func.sum(Order.amount)).filter_by(user_id=self.id, status='completed').scalar() or 0
        
        return {
            'total_deliveries': self.total_deliveries,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'total_earnings': round(total_earnings, 2),
            'current_balance': round(self.balance, 2)
        }
    
    @classmethod
    def create_user(cls, username, email, password):
        """
        Создание нового пользователя с паролем.
        
        Args:
            username (str): Уникальный никнейм
            email (str): Уникальная почта
            password (str): Пароль в открытом виде
            
        Returns:
            User: Созданный пользователь
        """
        user = cls(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    @classmethod
    def create_google_user(cls, username, email, google_id):
        """
        Создание пользователя через Google OAuth (без пароля).
        
        Args:
            username (str): Уникальный никнейм
            email (str): Уникальная почта
            google_id (str): Google ID пользователя
            
        Returns:
            User: Созданный пользователь
        """
        user = cls(username=username, email=email, google_id=google_id)
        db.session.add(user)
        db.session.commit()
        return user
