from datetime import datetime
from app import db

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined, blocked
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint to prevent duplicate friend requests
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)

    def __repr__(self):
        return '<Friend user_id={} friend_id={} status={}>'.format(
            self.user_id, self.friend_id, self.status)

    @staticmethod
    def send_friend_request(user_id, friend_id):
        """Send a friend request"""
        # Check if friendship already exists
        existing = Friend.query.filter(
            ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
        ).first()
        
        if existing:
            return existing, False  # Already exists
        
        # Create new friend request
        friend_request = Friend(
            user_id=user_id,
            friend_id=friend_id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.commit()
        return friend_request, True

    def accept_request(self):
        """Accept a friend request"""
        if self.status == 'pending':
            self.status = 'accepted'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def decline_request(self):
        """Decline a friend request"""
        if self.status == 'pending':
            self.status = 'declined'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def block_user(self):
        """Block a user"""
        self.status = 'blocked'
        self.updated_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def get_pending_requests(user_id):
        """Get all pending friend requests for a user"""
        return Friend.query.filter_by(friend_id=user_id, status='pending').all()

    @staticmethod
    def get_sent_requests(user_id):
        """Get all friend requests sent by a user"""
        return Friend.query.filter_by(user_id=user_id, status='pending').all()

    @staticmethod
    def get_accepted_friends(user_id):
        """Get all accepted friends for a user"""
        friends = []
        
        # Friends where user sent the request
        sent_friends = Friend.query.filter_by(user_id=user_id, status='accepted').all()
        
        # Friends where user received the request
        received_friends = Friend.query.filter_by(friend_id=user_id, status='accepted').all()
        
        friends.extend(sent_friends)
        friends.extend(received_friends)
        
        return friends

    @staticmethod
    def are_friends(user_id, friend_id):
        """Check if two users are friends"""
        return Friend.query.filter(
            ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
        ).filter_by(status='accepted').first() is not None

    @staticmethod
    def get_friendship_status(user_id, friend_id):
        """Get the status of friendship between two users"""
        friendship = Friend.query.filter(
            ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
        ).first()
        
        if friendship:
            return friendship.status
        return None
