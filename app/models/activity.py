from datetime import datetime
from app import db

class Activity(db.Model):
    """Model for group activity suggestions"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    suggested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed'
    order_index = db.Column(db.Integer, default=0)
    
    # Relationships
    group = db.relationship('Group', backref='activities')
    suggested_by = db.relationship('User', backref='suggested_activities')
    
    def __repr__(self):
        return f'<Activity {self.venue} for group {self.group_id}>'
    
    def to_dict(self):
        """Convert activity to dictionary for JSON responses"""
        return {
            'id': self.id,
            'venue': self.venue,
            'suggested_by': {
                'id': self.suggested_by.id,
                'name': self.suggested_by.first_name or self.suggested_by.email
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status,
            'order_index': self.order_index,
            'can_delete': False  # Will be set based on permissions
        }
