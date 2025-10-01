# -*- coding: utf-8 -*-
"""
Модель заказа для симулятора курьера.
Хранит информацию о заказах доставки от ресторанов к зданиям.
"""

from datetime import datetime, timedelta
from app import db
from sqlalchemy import func
from app.utils.gps_helper import calculate_distance

class Order(db.Model):
    """
    Модель заказа доставки
    """
    
    __tablename__ = 'orders'
    
    # Основные поля
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Названия и адреса (храним напрямую)
    pickup_name = db.Column(db.String(200), nullable=False)
    dropoff_address = db.Column(db.String(300), nullable=False)
    
    # Координаты точек
    pickup_lat = db.Column(db.Float, nullable=False)
    pickup_lng = db.Column(db.Float, nullable=False)
    dropoff_lat = db.Column(db.Float, nullable=False)
    dropoff_lng = db.Column(db.Float, nullable=False)
    
    # Статус и временные данные
    status = db.Column(db.String(20), default='pending', nullable=False)
    pickup_time = db.Column(db.DateTime, nullable=True)
    delivery_time = db.Column(db.DateTime, nullable=True)
    
    # Экономика заказа
    amount = db.Column(db.Float, nullable=False)
    timer_seconds = db.Column(db.Integer, nullable=False)
    distance_km = db.Column(db.Float, nullable=False)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Связи
    user = db.relationship('User', back_populates='orders')
    reports = db.relationship('Report', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id} ({self.status})>'
    
    def __init__(self, **kwargs):
        """Инициализация заказа с автоматическим расчетом параметров"""
        super(Order, self).__init__(**kwargs)
        
        if self.pickup_lat and self.pickup_lng and self.dropoff_lat and self.dropoff_lng:
            self.distance_km = calculate_distance(
                self.pickup_lat, self.pickup_lng,
                self.dropoff_lat, self.dropoff_lng
            )
            
            try:
                from flask import current_app
                config = current_app.config.get('GAME_CONFIG', {})
            except RuntimeError:
                config = {
                    'delivery_speed_kmh': 5,
                    'delivery_base_time': 300,
                    'pickup_timeout': 3600
                }
            
            self.timer_seconds = int(
                (self.distance_km / config.get('delivery_speed_kmh', 5)) * 3600 + 
                config.get('delivery_base_time', 300)
            )
            
            try:
                from app.utils.economy import calculate_payout
                self.amount = calculate_payout(self.distance_km, config)
            except:
                self.amount = 1.5 + 0.5 + 0.5 + (self.distance_km * 0.8)
            
            self.expires_at = datetime.utcnow() + timedelta(seconds=config.get('pickup_timeout', 3600))
    
    def to_dict(self):
        """Преобразование заказа в словарь для JSON"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'pickup': {
                'lat': self.pickup_lat,
                'lng': self.pickup_lng,
                'name': self.pickup_name
            },
            'dropoff': {
                'lat': self.dropoff_lat,
                'lng': self.dropoff_lng,
                'address': self.dropoff_address
            },
            'amount': round(self.amount, 2),
            'distance_km': round(self.distance_km, 2),
            'timer_seconds': self.timer_seconds,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'delivery_time': self.delivery_time.isoformat() if self.delivery_time else None,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'time_remaining': self.get_time_remaining()
        }
    
    def get_time_remaining(self):
        """Получение оставшегося времени до истечения заказа"""
        if self.status in ['completed', 'cancelled']:
            return 0
            
        now = datetime.utcnow()
        
        if self.status == 'pending':
            # Время до истечения с момента создания
            remaining = (self.expires_at - now).total_seconds()
        elif self.status == 'active':
            if self.pickup_time:
                # Заказ забран - время до дедлайна доставки
                delivery_deadline = self.pickup_time + timedelta(seconds=self.timer_seconds * 2)
                remaining = (delivery_deadline - now).total_seconds()
            else:
                # Заказ принят но не забран - используем expires_at
                remaining = (self.expires_at - now).total_seconds()
        else:
            remaining = 0
        
        return max(0, int(remaining))
    
    def is_expired(self):
        """Проверка просрочки заказа"""
        return self.get_time_remaining() == 0 and self.status not in ['completed', 'cancelled']
    
    def accept_order(self, user_id):
        """Принятие заказа игроком"""
        import logging
        logger = logging.getLogger(__name__)
        
        if self.status != 'pending' or self.is_expired():
            logger.warning(f"Cannot accept order {self.id}: status={self.status}, expired={self.is_expired()}")
            return False
        
        self.user_id = user_id
        self.status = 'active'
        self.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            logger.info(f"Order {self.id} accepted by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error committing order acceptance: {str(e)}")
            db.session.rollback()
            return False
    
    def pickup_order(self):
        """Забор заказа"""
        if self.status != 'active' or self.pickup_time:
            return False
        
        self.pickup_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    def deliver_order(self):
        """Доставка заказа"""
        if self.status != 'active' or not self.pickup_time:
            return {'success': False, 'error': 'Order not ready for delivery'}
        
        self.delivery_time = datetime.utcnow()
        self.status = 'completed'
        self.updated_at = datetime.utcnow()
        
        delivery_duration = (self.delivery_time - self.pickup_time).total_seconds()
        on_time = delivery_duration <= self.timer_seconds
        
        from app.utils.economy import calculate_final_payout
        final_payout = calculate_final_payout(self.distance_km, on_time)
        
        self.amount = final_payout['total']
        
        if self.user:
            self.user.update_balance(final_payout['total'])
            self.user.increment_deliveries()
        
        db.session.commit()
        
        return {
            'success': True,
            'on_time': on_time,
            'delivery_duration': int(delivery_duration),
            'timer_seconds': self.timer_seconds,
            'payout': final_payout
        }
    
    def cancel_order(self, reason='user_cancelled'):
        """Отмена заказа"""
        if self.status in ['completed', 'cancelled']:
            return False
        
        self.status = 'cancelled'
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    def expire_order(self):
        """Истечение времени заказа"""
        if self.is_expired() and self.status not in ['completed', 'cancelled']:
            self.status = 'expired'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    def get_estimated_time(self):
        """Получение примерного времени доставки"""
        minutes = self.timer_seconds // 60
        if minutes < 60:
            return f"~{minutes} мин"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"~{hours}ч {remaining_minutes}м"
            else:
                return f"~{hours}ч"
    
    @classmethod
    def create_order(cls, pickup_name, pickup_lat, pickup_lng, 
                    dropoff_address, dropoff_lat, dropoff_lng):
        """Создание нового заказа"""
        order = cls(
            pickup_name=pickup_name,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_address=dropoff_address,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng
        )
        
        db.session.add(order)
        db.session.commit()
        
        return order
