from app import db
from datetime import datetime
import json

class DefaultSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_name = db.Column(db.String(100), nullable=False, default='Default Schedule')
    schedule_data = db.Column(db.Text, nullable=False)  # JSON string of weekly availability
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('default_schedules', lazy='dynamic'))

    def __repr__(self):
        return f'<DefaultSchedule {self.schedule_name} for User {self.user_id}>'

    def set_schedule_data(self, availability_data):
        """Store availability data as JSON string"""
        self.schedule_data = json.dumps(availability_data)

    def get_schedule_data(self):
        """Retrieve availability data from JSON string"""
        if self.schedule_data:
            return json.loads(self.schedule_data)
        return {}

    @staticmethod
    def get_active_default(user_id):
        """Get the active default schedule for a user"""
        return DefaultSchedule.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).first()
