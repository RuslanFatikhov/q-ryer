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
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    
    # Игровая информация
    balance = db.Column(db.Float, default=0.0, nullable=False)
    total_deliveries = db.Column(db.Integer, default=0, nullable=False)
    
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
    def create_user(cls, username, email=None, google_id=None):
        """Создание нового пользователя"""
        user = cls(username=username, email=email, google_id=google_id)
        db.session.add(user)
        db.session.commit()
        return user
