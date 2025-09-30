from app import db
from datetime import datetime, timedelta
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import os
import base64

class OutlookCalendarSync(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)
    outlook_calendar_id = db.Column(db.String(255), default='primary')  # Primary calendar ID
    encrypted_refresh_token = db.Column(db.Text, nullable=False)  # Encrypted refresh token
    access_token = db.Column(db.Text)  # Temporary, refreshed automatically
    token_expires_at = db.Column(db.DateTime)
    sync_enabled = db.Column(db.Boolean, default=True)
    auto_sync_availability = db.Column(db.Boolean, default=True)
    auto_add_events = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref='outlook_calendar_sync', uselist=False)
    
    def __repr__(self):
        return f'<OutlookCalendarSync {self.user_id} - {self.outlook_calendar_id}>'
    
    @staticmethod
    def _get_encryption_key():
        """Get or create encryption key for tokens"""
        key = os.environ.get('OUTLOOK_TOKEN_ENCRYPTION_KEY')
        if not key:
            # Generate a new key if none exists (for development)
            key = Fernet.generate_key().decode()
            os.environ['OUTLOOK_TOKEN_ENCRYPTION_KEY'] = key
        return key.encode() if isinstance(key, str) else key
    
    def set_refresh_token(self, refresh_token):
        """Encrypt and store refresh token"""
        if refresh_token:
            fernet = Fernet(self._get_encryption_key())
            encrypted_token = fernet.encrypt(refresh_token.encode())
            self.encrypted_refresh_token = base64.b64encode(encrypted_token).decode()
    
    def get_refresh_token(self):
        """Decrypt and return refresh token"""
        if self.encrypted_refresh_token:
            try:
                fernet = Fernet(self._get_encryption_key())
                encrypted_token = base64.b64decode(self.encrypted_refresh_token.encode())
                return fernet.decrypt(encrypted_token).decode()
            except Exception as e:
                # Token decryption failed, return None
                return None
        return None
    
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() >= self.token_expires_at
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'calendar_id': self.outlook_calendar_id,
            'sync_enabled': self.sync_enabled,
            'auto_sync_availability': self.auto_sync_availability,
            'auto_add_events': self.auto_add_events,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'token_expired': self.is_token_expired()
        }
