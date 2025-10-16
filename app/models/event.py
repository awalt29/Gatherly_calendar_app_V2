from datetime import datetime
import pytz
import json
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
    
    # External calendar event IDs for sync
    google_calendar_event_ids = db.Column(db.Text)  # JSON string of user_id -> event_id mapping
    outlook_calendar_event_ids = db.Column(db.Text)  # JSON string of user_id -> event_id mapping
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_events')
    attendees = db.relationship('User', secondary=event_attendees, backref='events')
    
    def __repr__(self):
        return f'<Event {self.title} on {self.date}>'
    
    def get_time_range(self, user_timezone=None):
        """Get formatted time range string, optionally in user's timezone"""
        if user_timezone:
            # Convert times to user's timezone
            start_time, end_time = self.get_times_in_timezone(user_timezone)
            start_formatted = start_time.strftime('%I:%M %p').lstrip('0')
            end_formatted = end_time.strftime('%I:%M %p').lstrip('0')
        else:
            # Use original times (assumed to be in server timezone)
            start_formatted = self.start_time.strftime('%I:%M %p').lstrip('0')
            end_formatted = self.end_time.strftime('%I:%M %p').lstrip('0')
        return f"{start_formatted} - {end_formatted}"
    
    def get_times_in_timezone(self, user_timezone):
        """Convert event times to user's timezone"""
        try:
            # Assume stored times are in UTC or server timezone (America/New_York by default)
            server_tz = pytz.timezone('America/New_York')  # or UTC
            user_tz = pytz.timezone(user_timezone)
            
            # Create datetime objects for the event date with times
            start_dt = datetime.combine(self.date, self.start_time)
            end_dt = datetime.combine(self.date, self.end_time)
            
            # Localize to server timezone first
            start_dt_localized = server_tz.localize(start_dt)
            end_dt_localized = server_tz.localize(end_dt)
            
            # Convert to user timezone
            start_dt_user = start_dt_localized.astimezone(user_tz)
            end_dt_user = end_dt_localized.astimezone(user_tz)
            
            return start_dt_user.time(), end_dt_user.time()
        except Exception:
            # If timezone conversion fails, return original times
            return self.start_time, self.end_time
    
    def get_date_in_timezone(self, user_timezone):
        """Get event date in user's timezone (in case it shifts due to timezone conversion)"""
        try:
            server_tz = pytz.timezone('America/New_York')
            user_tz = pytz.timezone(user_timezone)
            
            start_dt = datetime.combine(self.date, self.start_time)
            start_dt_localized = server_tz.localize(start_dt)
            start_dt_user = start_dt_localized.astimezone(user_tz)
            
            return start_dt_user.date()
        except Exception:
            return self.date
    
    def add_google_calendar_event_id(self, user_id, event_id):
        """Add Google Calendar event ID for a specific user"""
        try:
            ids = json.loads(self.google_calendar_event_ids) if self.google_calendar_event_ids else {}
            ids[str(user_id)] = event_id
            self.google_calendar_event_ids = json.dumps(ids)
        except Exception:
            self.google_calendar_event_ids = json.dumps({str(user_id): event_id})
    
    def add_outlook_calendar_event_id(self, user_id, event_id):
        """Add Outlook Calendar event ID for a specific user"""
        try:
            ids = json.loads(self.outlook_calendar_event_ids) if self.outlook_calendar_event_ids else {}
            ids[str(user_id)] = event_id
            self.outlook_calendar_event_ids = json.dumps(ids)
        except Exception:
            self.outlook_calendar_event_ids = json.dumps({str(user_id): event_id})
    
    def get_google_calendar_event_ids(self):
        """Get all Google Calendar event IDs"""
        try:
            return json.loads(self.google_calendar_event_ids) if self.google_calendar_event_ids else {}
        except Exception:
            return {}
    
    def get_outlook_calendar_event_ids(self):
        """Get all Outlook Calendar event IDs"""
        try:
            return json.loads(self.outlook_calendar_event_ids) if self.outlook_calendar_event_ids else {}
        except Exception:
            return {}
    
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
