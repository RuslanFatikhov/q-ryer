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
    reports = db.relationship("Report", back_populates="order", lazy=True)
    """
    Модель заказа доставки
    
    Attributes:
        id (int): Уникальный идентификатор заказа
        user_id (int): ID пользователя, взявшего заказ
        restaurant_id (int): ID ресторана (точка pickup)
        building_id (int): ID здания (точка dropoff)
        pickup_lat (float): Широта точки забора
        pickup_lng (float): Долгота точки забора
        dropoff_lat (float): Широта точки доставки
        dropoff_lng (float): Долгота точки доставки
        status (str): Статус заказа
        pickup_time (datetime): Время забора заказа
        delivery_time (datetime): Время доставки заказа
        amount (float): Сумма выплаты за заказ
        timer_seconds (int): Таймер доставки в секундах
        distance_km (float): Расстояние доставки в километрах
        created_at (datetime): Время создания заказа
        updated_at (datetime): Время последнего обновления
        expires_at (datetime): Время истечения заказа
    """
    
    __tablename__ = 'orders'
    
    # Основные поля
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Связь с ресторанами и зданиями (убираем, так как работаем с GeoJSON)
    # restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    # building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    
    # Названия и адреса (храним напрямую)
    pickup_name = db.Column(db.String(200), nullable=False)  # Название ресторана
    dropoff_address = db.Column(db.String(300), nullable=False)  # Адрес здания
    
    # Координаты точек
    pickup_lat = db.Column(db.Float, nullable=False)
    pickup_lng = db.Column(db.Float, nullable=False)
    dropoff_lat = db.Column(db.Float, nullable=False)
    dropoff_lng = db.Column(db.Float, nullable=False)
    
    # Статус и временные данные
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, active, completed, cancelled, expired
    pickup_time = db.Column(db.DateTime, nullable=True)
    delivery_time = db.Column(db.DateTime, nullable=True)
    
    # Экономика заказа
    amount = db.Column(db.Float, nullable=False)
    timer_seconds = db.Column(db.Integer, nullable=False)
    distance_km = db.Column(db.Float, nullable=False)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)  # Время истечения заказа
    
    # Связи (убираем связи с несуществующими моделями)
    # restaurant = db.relationship('Restaurant', backref='orders')
    # building = db.relationship('Building', backref='orders')
    reports = db.relationship('Report', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id} ({self.status})>'
    
    def __init__(self, **kwargs):
        """
        Инициализация заказа с автоматическим расчетом параметров
        """
        super(Order, self).__init__(**kwargs)
        
        # Рассчитываем расстояние
        if self.pickup_lat and self.pickup_lng and self.dropoff_lat and self.dropoff_lng:
            self.distance_km = calculate_distance(
                self.pickup_lat, self.pickup_lng,
                self.dropoff_lat, self.dropoff_lng
            )
            
            # Рассчитываем таймер доставки
            from flask import current_app
            config = current_app.config['GAME_CONFIG']
            self.timer_seconds = int(
                (self.distance_km / config['delivery_speed_kmh']) * 3600 + 
                config['delivery_base_time']
            )
            
            # Рассчитываем сумму выплаты
            from app.utils.economy import calculate_payout
            self.amount = calculate_payout(self.distance_km)
            
            # Устанавливаем время истечения (1 час на pickup)
            self.expires_at = datetime.utcnow() + timedelta(seconds=config['pickup_timeout'])
    
    def to_dict(self):
        """
        Преобразование заказа в словарь для JSON
        
        Returns:
            dict: Словарь с информацией о заказе
        """
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
        """
        Получение оставшегося времени до истечения заказа
        
        Returns:
            int: Секунды до истечения (или 0 если просрочен)
        """
        if self.status in ['completed', 'cancelled']:
            return 0
            
        now = datetime.utcnow()
        
        if self.status == 'pending':
            # До pickup остается времени
            remaining = (self.expires_at - now).total_seconds()
        elif self.status == 'active' and self.pickup_time:
            # Время на доставку с момента pickup
            delivery_deadline = self.pickup_time + timedelta(seconds=self.timer_seconds * 2)
            remaining = (delivery_deadline - now).total_seconds()
        else:
            remaining = 0
        
        return max(0, int(remaining))
    
    def is_expired(self):
        """
        Проверка просрочки заказа
        
        Returns:
            bool: True если заказ просрочен
        """
        return self.get_time_remaining() == 0 and self.status not in ['completed', 'cancelled']
    
    def accept_order(self, user_id):
        """
        Принятие заказа игроком
        
        Args:
            user_id (int): ID пользователя
        
        Returns:
            bool: True если заказ успешно принят
        """
        if self.status != 'pending' or self.is_expired():
            return False
        
        self.user_id = user_id
        self.status = 'active'
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    def pickup_order(self):
        """
        Забор заказа (когда игрок подошел к ресторану)
        
        Returns:
            bool: True если забор успешен
        """
        if self.status != 'active' or self.pickup_time:
            return False
        
        self.pickup_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    def deliver_order(self):
        """
        Доставка заказа (когда игрок подошел к зданию)
        
        Returns:
            dict: Результат доставки с деталями выплаты
        """
        if self.status != 'active' or not self.pickup_time:
            return {'success': False, 'error': 'Order not ready for delivery'}
        
        self.delivery_time = datetime.utcnow()
        self.status = 'completed'
        self.updated_at = datetime.utcnow()
        
        # Проверяем, была ли доставка вовремя
        delivery_duration = (self.delivery_time - self.pickup_time).total_seconds()
        on_time = delivery_duration <= self.timer_seconds
        
        # Рассчитываем финальную выплату
        from app.utils.economy import calculate_final_payout
        final_payout = calculate_final_payout(self.distance_km, on_time)
        
        # Обновляем сумму заказа
        self.amount = final_payout['total']
        
        # Обновляем баланс пользователя
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
        """
        Отмена заказа
        
        Args:
            reason (str): Причина отмены
        
        Returns:
            bool: True если отмена успешна
        """
        if self.status in ['completed', 'cancelled']:
            return False
        
        self.status = 'cancelled'
        self.updated_at = datetime.utcnow()
        
        # Добавляем информацию о причине отмены в поле (можно расширить модель)
        db.session.commit()
        return True
    
    def expire_order(self):
        """
        Истечение времени заказа
        
        Returns:
            bool: True если заказ просрочен
        """
        if self.is_expired() and self.status not in ['completed', 'cancelled']:
            self.status = 'expired'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    def get_estimated_time(self):
        """
        Получение примерного времени доставки
        
        Returns:
            str: Строка с примерным временем
        """
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
        """
        Создание нового заказа.
        
        Args:
            pickup_name (str): Название ресторана
            pickup_lat (float): Широта ресторана
            pickup_lng (float): Долгота ресторана
            dropoff_address (str): Адрес здания
            dropoff_lat (float): Широта здания
            dropoff_lng (float): Долгота здания
        
        Returns:
            Order: Созданный заказ
        """
        # Создаем заказ
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
    
    @classmethod
    def get_pending_orders(cls):
        """
        Получение всех ожидающих заказов
        
        Returns:
            Query: Запрос ожидающих заказов
        """
        return cls.query.filter_by(status='pending').filter(
            cls.expires_at > datetime.utcnow()
        )
    
    @classmethod
    def get_orders_near_location(cls, lat, lng, radius_km=5):
        """
        Получение заказов рядом с указанной позицией
        
        Args:
            lat (float): Широта
            lng (float): Долгота
            radius_km (float): Радиус поиска в км
        
        Returns:
            list: Список заказов рядом с позицией
        """
        import math
        
        # Упрощенный поиск по квадрату (для более точного нужен PostGIS)
        lat_delta = radius_km / 111.0  # Примерно 1 градус = 111 км
        lng_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
        
        return cls.query.filter(
            cls.status == 'pending',
            cls.pickup_lat.between(lat - lat_delta, lat + lat_delta),
            cls.pickup_lng.between(lng - lng_delta, lng + lng_delta),
            cls.expires_at > datetime.utcnow()
        ).all()
    
    @classmethod
    def cleanup_expired_orders(cls):
        """
        Очистка просроченных заказов (для cron задач)
        
        Returns:
            int: Количество обновленных заказов
        """
        expired_orders = cls.query.filter(
            cls.status.in_(['pending', 'active']),
            cls.expires_at <= datetime.utcnow()
        ).all()
        
        count = 0
        for order in expired_orders:
            if order.expire_order():
                count += 1
        
        return count
    
    @classmethod
    def get_statistics(cls):
        """
        Получение общей статистики по заказам
        
        Returns:
            dict: Статистика заказов
        """
        total_orders = cls.query.count()
        completed_orders = cls.query.filter_by(status='completed').count()
        active_orders = cls.query.filter_by(status='active').count()
        pending_orders = cls.query.filter_by(status='pending').count()
        
        avg_amount = db.session.query(func.avg(cls.amount)).filter_by(status='completed').scalar() or 0
        total_revenue = db.session.query(func.sum(cls.amount)).filter_by(status='completed').scalar() or 0
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'active_orders': active_orders,
            'pending_orders': pending_orders,
            'completion_rate': round((completed_orders / max(total_orders, 1)) * 100, 1),
            'average_amount': round(avg_amount, 2),
            'total_revenue': round(total_revenue, 2)
        }