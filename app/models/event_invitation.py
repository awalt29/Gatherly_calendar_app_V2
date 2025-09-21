from app import db
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class EventInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, ForeignKey('event.id'), nullable=False)
    invitee_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'accepted', 'declined'
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    event = relationship('Event', backref='invitations')
    invitee = relationship('User', backref='event_invitations')
    
    def __repr__(self):
        return f'<EventInvitation {self.event_id} -> {self.invitee_id} ({self.status})>'
    
    def accept(self):
        """Accept the invitation and add user to event attendees"""
        if self.status != 'pending':
            return False
        
        self.status = 'accepted'
        self.responded_at = datetime.utcnow()
        
        # Add user to event attendees if not already added
        if self.invitee not in self.event.attendees:
            self.event.attendees.append(self.invitee)
        
        return True
    
    def decline(self):
        """Decline the invitation"""
        if self.status != 'pending':
            return False
            
        self.status = 'declined'
        self.responded_at = datetime.utcnow()
        
        # Remove user from event attendees if they were added
        if self.invitee in self.event.attendees:
            self.event.attendees.remove(self.invitee)
        
        return True
