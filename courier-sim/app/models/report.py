# app/models/report.py
from datetime import datetime
from app import db

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, resolved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            "created_at": self.created_at.isoformat()
        }
