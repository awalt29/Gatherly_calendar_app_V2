from app import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'friend_request', 'friend_accepted', 'group_added', 'event_invited'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Optional reference IDs for linking to specific entities
    friend_id = db.Column(db.Integer, db.ForeignKey('friend.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who triggered the notification
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    friend = db.relationship('Friend', backref='notifications')
    group = db.relationship('Group', backref='notifications')
    event = db.relationship('Event', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.type} for user {self.user_id}>'
    
    def to_dict(self):
        """Convert notification to dictionary for JSON responses"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'from_user': {
                'id': self.from_user.id,
                'name': self.from_user.get_full_name(),
                'initials': self.from_user.get_initials()
            } if self.from_user else None,
            'friend_id': self.friend_id,
            'group_id': self.group_id,
            'event_id': self.event_id
        }
    
    @staticmethod
    def create_friend_request_notification(user_id, from_user_id, friend_id):
        """Create a notification for a new friend request"""
        from app.models.user import User
        from_user = User.query.get(from_user_id)
        
        notification = Notification(
            user_id=user_id,
            type='friend_request',
            title='New Friend Request',
            message=f'{from_user.get_full_name()} sent you a friend request',
            friend_id=friend_id,
            from_user_id=from_user_id
        )
        db.session.add(notification)
        return notification
    
    @staticmethod
    def create_friend_accepted_notification(user_id, from_user_id):
        """Create a notification for an accepted friend request"""
        from app.models.user import User
        from_user = User.query.get(from_user_id)
        
        notification = Notification(
            user_id=user_id,
            type='friend_accepted',
            title='Friend Request Accepted',
            message=f'{from_user.get_full_name()} accepted your friend request',
            from_user_id=from_user_id
        )
        db.session.add(notification)
        return notification
    
    @staticmethod
    def create_group_added_notification(user_id, from_user_id, group_id):
        """Create a notification for being added to a group"""
        from app.models.user import User
        from app.models.group import Group
        from_user = User.query.get(from_user_id)
        group = Group.query.get(group_id)
        
        notification = Notification(
            user_id=user_id,
            type='group_added',
            title='Added to Group',
            message=f'{from_user.get_full_name()} added you to "{group.name}"',
            group_id=group_id,
            from_user_id=from_user_id
        )
        db.session.add(notification)
        return notification
    
    @staticmethod
    def create_event_invited_notification(user_id, from_user_id, event_id):
        """Create a notification for being invited to an event"""
        from app.models.user import User
        from app.models.event import Event
        from_user = User.query.get(from_user_id)
        event = Event.query.get(event_id)
        
        notification = Notification(
            user_id=user_id,
            type='event_invited',
            title='Event Invitation',
            message=f'{from_user.get_full_name()} invited you to "{event.title}"',
            event_id=event_id,
            from_user_id=from_user_id
        )
        db.session.add(notification)
        return notification
