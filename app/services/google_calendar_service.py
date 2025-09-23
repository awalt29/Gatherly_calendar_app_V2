import os
from datetime import datetime, timedelta
from flask import current_app, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.models.google_calendar_sync import GoogleCalendarSync
from app.models.user import User
from app import db
import logging

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        # Initialize without current_app to avoid context issues
        self._client_id = None
        self._client_secret = None
        self._redirect_uri = None
        self._scopes = None
    
    @property
    def client_id(self):
        if self._client_id is None:
            self._client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        return self._client_id
    
    @property
    def client_secret(self):
        if self._client_secret is None:
            self._client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        return self._client_secret
    
    @property
    def redirect_uri(self):
        if self._redirect_uri is None:
            self._redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
        return self._redirect_uri
    
    @property
    def scopes(self):
        if self._scopes is None:
            self._scopes = current_app.config.get('GOOGLE_SCOPES', [])
        return self._scopes
    
    def is_configured(self):
        """Check if Google Calendar is properly configured"""
        return bool(self.client_id and self.client_secret and self.scopes)
    
    def get_authorization_url(self, state=None):
        """Get Google OAuth authorization URL"""
        if not self.is_configured():
            raise ValueError("Google Calendar not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent screen to get refresh token
        )
        
        return auth_url
    
    def handle_oauth_callback(self, authorization_code, user_id):
        """Handle OAuth callback and store tokens"""
        if not self.is_configured():
            raise ValueError("Google Calendar not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        try:
            # Exchange authorization code for tokens
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Get or create GoogleCalendarSync record
            sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            if not sync_record:
                sync_record = GoogleCalendarSync(user_id=user_id)
                db.session.add(sync_record)
            
            # Store tokens
            sync_record.set_refresh_token(credentials.refresh_token)
            sync_record.access_token = credentials.token
            sync_record.token_expires_at = credentials.expiry
            sync_record.sync_enabled = True
            
            # Update user's Google Calendar status
            user = User.query.get(user_id)
            if user:
                user.google_calendar_enabled = True
            
            db.session.commit()
            
            logger.info(f"Google Calendar connected successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def get_credentials(self, user_id):
        """Get valid credentials for a user"""
        sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
        if not sync_record:
            return None
        
        refresh_token = sync_record.get_refresh_token()
        if not refresh_token:
            return None
        
        credentials = Credentials(
            token=sync_record.access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )
        
        # Refresh token if needed
        if sync_record.needs_refresh():
            try:
                credentials.refresh(Request())
                
                # Update stored tokens
                sync_record.access_token = credentials.token
                sync_record.token_expires_at = credentials.expiry
                db.session.commit()
                
                logger.info(f"Refreshed Google Calendar token for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
                return None
        
        return credentials
    
    def get_calendar_service(self, user_id):
        """Get Google Calendar service for a user"""
        credentials = self.get_credentials(user_id)
        if not credentials:
            return None
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"Error creating calendar service for user {user_id}: {str(e)}")
            return None
    
    def disconnect_calendar(self, user_id):
        """Disconnect Google Calendar for a user"""
        try:
            # Remove sync record
            sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            if sync_record:
                db.session.delete(sync_record)
            
            # Update user status
            user = User.query.get(user_id)
            if user:
                user.google_calendar_enabled = False
            
            db.session.commit()
            logger.info(f"Google Calendar disconnected for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Google Calendar for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def get_busy_times(self, user_id, start_date, end_date):
        """Get busy times from Google Calendar"""
        service = self.get_calendar_service(user_id)
        if not service:
            return []
        
        try:
            # Get the user's calendar sync settings
            sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            calendar_id = sync_record.google_calendar_id if sync_record else 'primary'
            
            # Query for busy times
            body = {
                "timeMin": start_date.isoformat() + 'Z',
                "timeMax": end_date.isoformat() + 'Z',
                "items": [{"id": calendar_id}]
            }
            
            freebusy_result = service.freebusy().query(body=body).execute()
            busy_times = freebusy_result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
            
            # Convert to datetime objects and handle timezone
            import pytz
            from datetime import timezone
            
            busy_periods = []
            for period in busy_times:
                # Parse UTC times
                start_utc = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                end_utc = datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
                
                # Convert UTC to local time (assume user is in their local timezone)
                # For now, we'll assume the server's timezone. In future, store user timezone.
                start_local = start_utc.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                end_local = end_utc.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                
                busy_periods.append({'start': start_local, 'end': end_local})
                logger.info(f"Converted busy period: {period['start']} -> {start_local}, {period['end']} -> {end_local}")
            
            logger.info(f"Converted {len(busy_periods)} busy periods from UTC to local time")
            
            return busy_periods
            
        except HttpError as e:
            logger.error(f"Google Calendar API error for user {user_id}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error getting busy times for user {user_id}: {str(e)}")
            return []
    
    def create_event(self, user_id, event_data):
        """Create an event in Google Calendar"""
        service = self.get_calendar_service(user_id)
        if not service:
            return False
        
        try:
            sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            calendar_id = sync_record.google_calendar_id if sync_record else 'primary'
            
            created_event = service.events().insert(
                calendarId=calendar_id, 
                body=event_data
            ).execute()
            
            logger.info(f"Created Google Calendar event for user {user_id}: {created_event.get('id')}")
            return created_event.get('id')
            
        except HttpError as e:
            logger.error(f"Google Calendar API error creating event for user {user_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error creating Google Calendar event for user {user_id}: {str(e)}")
            return False

# Global instance
google_calendar_service = GoogleCalendarService()
