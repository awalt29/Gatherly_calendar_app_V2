from datetime import datetime
from app import db

# Association table for many-to-many relationship between events and users
event_attendees = db.Table('event_attendees',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_events')
    attendees = db.relationship('User', secondary=event_attendees, backref='events')
    
    def __repr__(self):
        return f'<Event {self.title} on {self.date}>'
    
    def get_time_range(self):
        """Get formatted time range string"""
        start_formatted = self.start_time.strftime('%I:%M %p').lstrip('0')
        end_formatted = self.end_time.strftime('%I:%M %p').lstrip('0')
        return f"{start_formatted} - {end_formatted}"
    
    def get_attendee_names(self):
        """Get list of attendee names"""
        return [user.get_full_name() for user in self.attendees]
    
    def is_attendee(self, user):
        """Check if user is an attendee"""
        return user in self.attendees
    
    def get_invitation_statuses(self):
        """Get invitation statuses for all invitees"""
        from app.models.event_invitation import EventInvitation
        invitations = EventInvitation.query.filter_by(event_id=self.id).all()
        
        status_map = {}
        for invitation in invitations:
            status_map[invitation.invitee_id] = {
                'status': invitation.status,
                'user': invitation.invitee,
                'responded_at': invitation.responded_at
            }
        
        return status_map
