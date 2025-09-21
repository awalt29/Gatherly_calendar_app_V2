from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from app import db, login

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=True)  # Make username optional
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), index=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    # Google Calendar integration
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    timezone = db.Column(db.String(50), default='America/New_York')
    
    # Password reset fields
    reset_token = db.Column(db.String(128), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    # Relationships
    availabilities = db.relationship('Availability', backref='user', lazy='dynamic')
    sent_friend_requests = db.relationship('Friend', 
                                         foreign_keys='Friend.user_id',
                                         backref='requester', lazy='dynamic')
    received_friend_requests = db.relationship('Friend',
                                             foreign_keys='Friend.friend_id', 
                                             backref='receiver', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.email)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        return self.email.split('@')[0]  # Use email prefix as fallback

    def get_initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return f"{self.first_name[0]}{self.first_name[1] if len(self.first_name) > 1 else 'X'}".upper()
        elif self.username:
            return self.username[:2].upper()
        return self.email[:2].upper()  # Use first 2 chars of email as fallback

    def get_friends(self):
        """Get all accepted friends"""
        from app.models.friend import Friend
        friends = []
        
        # Friends where this user sent the request
        sent_friends = Friend.query.filter_by(
            user_id=self.id, 
            status='accepted'
        ).all()
        
        # Friends where this user received the request
        received_friends = Friend.query.filter_by(
            friend_id=self.id, 
            status='accepted'
        ).all()
        
        # Get the actual user objects
        for friend_rel in sent_friends:
            friends.append(User.query.get(friend_rel.friend_id))
        
        for friend_rel in received_friends:
            friends.append(User.query.get(friend_rel.user_id))
        
        return friends

    def is_friend_with(self, user_id):
        """Check if this user is friends with another user"""
        from app.models.friend import Friend
        return Friend.query.filter(
            ((Friend.user_id == self.id) & (Friend.friend_id == user_id)) |
            ((Friend.user_id == user_id) & (Friend.friend_id == self.id))
        ).filter_by(status='accepted').first() is not None

    def generate_reset_token(self):
        """Generate a secure password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        return self.reset_token

    def verify_reset_token(self, token):
        """Verify if the reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if self.reset_token != token:
            return False
        if datetime.utcnow() > self.reset_token_expires:
            return False
        return True

    def clear_reset_token(self):
        """Clear the reset token after successful password reset"""
        self.reset_token = None
        self.reset_token_expires = None
