from datetime import datetime
from app import db

class Group(db.Model):
    """Model for friend groups with availability alerts"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settings for notifications
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    created_by = db.relationship('User', backref='created_groups')
    memberships = db.relationship('GroupMembership', backref='group', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Group {self.name}>'
    
    def get_members(self):
        """Get all members of this group"""
        from app.models.user import User
        member_ids = [m.user_id for m in self.memberships.filter_by(status='active').all()]
        return User.query.filter(User.id.in_(member_ids)).all()
    
    def get_member_count(self):
        """Get count of active members"""
        return self.memberships.filter_by(status='active').count()
    
    def is_member(self, user_id):
        """Check if a user is an active member of this group"""
        return self.memberships.filter_by(user_id=user_id, status='active').first() is not None
    
    def add_member(self, user_id):
        """Add a user to the group"""
        if not self.is_member(user_id):
            membership = GroupMembership(group_id=self.id, user_id=user_id, status='active')
            db.session.add(membership)
            return True
        return False
    
    def remove_member(self, user_id):
        """Remove a user from the group"""
        membership = self.memberships.filter_by(user_id=user_id).first()
        if membership:
            db.session.delete(membership)
            return True
        return False
    
    def to_dict(self):
        """Convert group to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.get_full_name(),
            'member_count': self.get_member_count(),
            'notifications_enabled': self.notifications_enabled,
            'created_at': self.created_at.isoformat(),
            'members': [{'id': m.id, 'name': m.get_full_name(), 'initials': m.get_initials()} 
                       for m in self.get_members()]
        }


class GroupMembership(db.Model):
    """Model for group membership (many-to-many relationship between users and groups)"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, pending
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='group_memberships')
    
    # Unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='unique_group_user'),)
    
    def __repr__(self):
        return f'<GroupMembership group_id={self.group_id} user_id={self.user_id}>'


class GroupAvailabilityAlert(db.Model):
    """Model to track when group availability alerts were sent to prevent spam"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # The date when the group was available
    alert_sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', backref='availability_alerts')
    
    # Unique constraint to prevent duplicate alerts for the same day
    __table_args__ = (db.UniqueConstraint('group_id', 'date', name='unique_group_date_alert'),)
    
    def __repr__(self):
        return f'<GroupAvailabilityAlert group_id={self.group_id} date={self.date}>'
