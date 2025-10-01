# -*- coding: utf-8 -*-
from datetime import datetime
from app import db

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, resolved, rejected
    admin_response = db.Column(db.Text, nullable=True)  # Ответ администратора
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # связи
    user = db.relationship("User", back_populates="reports")
    order = db.relationship("Order", back_populates="reports")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "message": self.message,
            "status": self.status,
            "admin_response": self.admin_response,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_status(self, new_status, admin_response=None):
        """Обновление статуса жалобы"""
        allowed_statuses = ['pending', 'resolved', 'rejected']
        
        if new_status not in allowed_statuses:
            return False
        
        self.status = new_status
        if admin_response:
            self.admin_response = admin_response
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
