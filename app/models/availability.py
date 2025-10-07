from datetime import datetime, timedelta, time
import pytz
from app import db
import json

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_start_date = db.Column(db.Date, nullable=False)
    availability_data = db.Column(db.Text)  # JSON string storing weekly availability
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint to prevent duplicate entries for same user and week
    __table_args__ = (db.UniqueConstraint('user_id', 'week_start_date', name='unique_user_week'),)

    def __repr__(self):
        return '<Availability user_id={} week={}>'.format(self.user_id, self.week_start_date)

    def set_availability_data(self, data):
        """Store availability data as JSON string"""
        self.availability_data = json.dumps(data)

    def get_availability_data(self):
        """Retrieve availability data from JSON string"""
        if self.availability_data:
            data = json.loads(self.availability_data)
            # Handle both old format (direct availability data) and new format (with timezone)
            if 'timezone' in data and 'availability' in data:
                return data['availability']  # New format (backward compatibility)
            else:
                return data  # Standard format
        return {}

    def get_day_availability(self, day_name):
        """Get availability for a specific day"""
        data = self.get_availability_data()
        return data.get(day_name.lower(), {})

    def is_available_on_day(self, day_name):
        """Check if user is available on a specific day"""
        day_data = self.get_day_availability(day_name)
        return day_data.get('available', False)

    def get_time_range(self, day_name):
        """Get time range for a specific day"""
        day_data = self.get_day_availability(day_name)
        if day_data.get('available', False):
            return {
                'start': day_data.get('start', '09:00'),
                'end': day_data.get('end', '17:00'),
                'all_day': day_data.get('all_day', False)
            }
        return None
    
    def get_time_ranges(self, day_name, user_timezone=None):
        """Get all time ranges for a specific day, optionally in user's timezone"""
        day_data = self.get_day_availability(day_name)
        if day_data.get('available', False):
            # Check if we have multiple time ranges
            time_ranges = day_data.get('time_ranges', [])
            if time_ranges:
                ranges = time_ranges
            else:
                # Fall back to single time range for backward compatibility
                ranges = [{
                    'start': day_data.get('start', '09:00'),
                    'end': day_data.get('end', '17:00')
                }]
            
            # Convert to user timezone if specified
            if user_timezone:
                converted_ranges = []
                for time_range in ranges:
                    converted_start, converted_end = self._convert_time_to_timezone(
                        time_range['start'], time_range['end'], user_timezone
                    )
                    converted_ranges.append({
                        'start': converted_start,
                        'end': converted_end
                    })
                return converted_ranges
            else:
                # Format original times to 12-hour format if they're in 24-hour format
                formatted_ranges = []
                for time_range in ranges:
                    start_formatted = self._format_time_to_12hour(time_range['start'])
                    end_formatted = self._format_time_to_12hour(time_range['end'])
                    formatted_ranges.append({
                        'start': start_formatted,
                        'end': end_formatted
                    })
                return formatted_ranges
        return []
    
    def _convert_time_to_timezone(self, start_time_str, end_time_str, user_timezone):
        """Convert time strings to user's timezone"""
        try:
            # All times are stored in server timezone (America/New_York)
            server_tz = pytz.timezone('America/New_York')
            user_tz = pytz.timezone(user_timezone)
            
            # Parse time strings
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Create datetime objects for today (date doesn't matter for time conversion)
            today = datetime.now().date()
            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)
            
            # Localize to server timezone
            start_dt_localized = server_tz.localize(start_dt)
            end_dt_localized = server_tz.localize(end_dt)
            
            # Convert to user timezone
            start_dt_user = start_dt_localized.astimezone(user_tz)
            end_dt_user = end_dt_localized.astimezone(user_tz)
            
            # Return formatted time strings in 12-hour format
            start_formatted = start_dt_user.strftime('%I:%M %p').lstrip('0')
            end_formatted = end_dt_user.strftime('%I:%M %p').lstrip('0')
            return start_formatted, end_formatted
        except Exception:
            # If conversion fails, return original times
            return start_time_str, end_time_str
    
    def _format_time_to_12hour(self, time_str):
        """Convert time string from 24-hour to 12-hour format"""
        try:
            # Parse the time string
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            # Format to 12-hour format
            return time_obj.strftime('%I:%M %p').lstrip('0')
        except Exception:
            # If parsing fails, return original
            return time_str

    @staticmethod
    def get_week_start(date):
        """Get the Monday of the week containing the given date"""
        days_since_monday = date.weekday()
        return date - timedelta(days=days_since_monday)

    @staticmethod
    def get_or_create_availability(user_id, week_start_date):
        """Get existing availability or create a new one"""
        availability = Availability.query.filter_by(
            user_id=user_id,
            week_start_date=week_start_date
        ).first()
        
        if not availability:
            availability = Availability(
                user_id=user_id,
                week_start_date=week_start_date,
                availability_data=json.dumps({})
            )
            db.session.add(availability)
            db.session.commit()
        
        return availability

    def update_day_availability(self, day_name, available, start_time=None, end_time=None, all_day=False):
        """Update availability for a specific day"""
        data = self.get_availability_data()
        
        day_data = {
            'available': available
        }
        
        if available:
            if all_day:
                day_data.update({
                    'start': '00:00',
                    'end': '23:59',
                    'all_day': True
                })
            else:
                day_data.update({
                    'start': start_time or '09:00',
                    'end': end_time or '17:00',
                    'all_day': False
                })
        
        data[day_name.lower()] = day_data
        self.set_availability_data(data)
        self.updated_at = datetime.utcnow()
        db.session.commit()
