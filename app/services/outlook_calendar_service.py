import os
import requests
from datetime import datetime, timedelta
from flask import current_app, url_for
import msal
from app.models.outlook_calendar_sync import OutlookCalendarSync
from app.models.user import User
from app import db
import logging

logger = logging.getLogger(__name__)

class OutlookCalendarService:
    def __init__(self):
        # Initialize without current_app to avoid context issues
        self._client_id = None
        self._client_secret = None
        self._redirect_uri = None
        self._scopes = None
        self._authority = None
    
    @property
    def client_id(self):
        if self._client_id is None:
            self._client_id = current_app.config.get('OUTLOOK_CLIENT_ID')
        return self._client_id
    
    @property
    def client_secret(self):
        if self._client_secret is None:
            self._client_secret = current_app.config.get('OUTLOOK_CLIENT_SECRET')
        return self._client_secret
    
    @property
    def redirect_uri(self):
        if self._redirect_uri is None:
            self._redirect_uri = current_app.config.get('OUTLOOK_REDIRECT_URI')
        return self._redirect_uri
    
    @property
    def scopes(self):
        if self._scopes is None:
            self._scopes = current_app.config.get('OUTLOOK_SCOPES', [])
        return self._scopes
    
    @property
    def authority(self):
        if self._authority is None:
            self._authority = current_app.config.get('OUTLOOK_AUTHORITY', 'https://login.microsoftonline.com/common')
        return self._authority
    
    def is_configured(self):
        """Check if Outlook Calendar is properly configured"""
        return bool(self.client_id and self.client_secret and self.scopes)
    
    def get_authorization_url(self, state=None):
        """Get Microsoft OAuth authorization URL"""
        if not self.is_configured():
            raise ValueError("Outlook Calendar not configured")
        
        # Create MSAL app
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        # Generate authorization URL
        auth_url = app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state
        )
        
        logger.info(f"Generated Outlook authorization URL for state: {state}")
        return auth_url
    
    def handle_oauth_callback(self, authorization_code, user_id):
        """Handle OAuth callback and store tokens"""
        if not self.is_configured():
            raise ValueError("Outlook Calendar not configured")
        
        # Create MSAL app
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        try:
            # Exchange authorization code for tokens
            result = app.acquire_token_by_authorization_code(
                authorization_code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            if "error" in result:
                logger.error(f"Outlook OAuth error: {result.get('error_description', result.get('error'))}")
                return False
            
            # Get or create OutlookCalendarSync record
            sync_record = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
            if not sync_record:
                sync_record = OutlookCalendarSync(user_id=user_id)
                db.session.add(sync_record)
            
            # Store tokens
            if result.get('refresh_token'):
                sync_record.set_refresh_token(result['refresh_token'])
            sync_record.access_token = result['access_token']
            
            # Calculate expiry time
            expires_in = result.get('expires_in', 3600)  # Default to 1 hour
            sync_record.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            sync_record.sync_enabled = True
            
            # Update user's Outlook Calendar status
            user = User.query.get(user_id)
            if user:
                user.outlook_calendar_enabled = True
            
            db.session.commit()
            
            logger.info(f"Outlook Calendar connected successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling Outlook OAuth callback for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def get_access_token(self, user_id):
        """Get valid access token for a user, refreshing if necessary"""
        sync_record = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
        if not sync_record:
            return None
        
        # Check if token is expired and refresh if needed
        if sync_record.is_token_expired():
            if not self._refresh_access_token(sync_record):
                return None
        
        return sync_record.access_token
    
    def _refresh_access_token(self, sync_record):
        """Refresh access token using refresh token"""
        refresh_token = sync_record.get_refresh_token()
        if not refresh_token:
            logger.error(f"No refresh token available for user {sync_record.user_id}")
            return False
        
        # Create MSAL app
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        try:
            # Refresh the token
            result = app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=self.scopes
            )
            
            if "error" in result:
                logger.error(f"Outlook token refresh error: {result.get('error_description', result.get('error'))}")
                return False
            
            # Update tokens
            sync_record.access_token = result['access_token']
            if result.get('refresh_token'):
                sync_record.set_refresh_token(result['refresh_token'])
            
            # Calculate expiry time
            expires_in = result.get('expires_in', 3600)
            sync_record.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            db.session.commit()
            logger.info(f"Outlook access token refreshed for user {sync_record.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing Outlook token for user {sync_record.user_id}: {str(e)}")
            return False
    
    def get_calendar_events(self, user_id, start_time, end_time):
        """Get calendar events from Outlook for a specific time range"""
        access_token = self.get_access_token(user_id)
        if not access_token:
            logger.error(f"No valid access token for user {user_id}")
            return []
        
        # Format times for Microsoft Graph API
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # Microsoft Graph API endpoint
        url = f"https://graph.microsoft.com/v1.0/me/calendar/events"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            '$filter': f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'",
            '$select': 'id,subject,start,end,showAs,isAllDay',
            '$orderby': 'start/dateTime'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('value', [])
            
            logger.info(f"Retrieved {len(events)} Outlook events for user {user_id}")
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Outlook events for user {user_id}: {str(e)}")
            return []
    
    def get_busy_times(self, user_id, start_time, end_time):
        """Get busy times from Outlook Calendar in the same format as Google Calendar"""
        events = self.get_calendar_events(user_id, start_time, end_time)
        
        logger.info(f"Processing {len(events)} Outlook events for user {user_id}")
        
        busy_times = []
        for event in events:
            try:
                subject = event.get('subject', 'No subject')
                show_as = event.get('showAs', 'busy').lower()
                
                logger.info(f"Outlook event: '{subject}', showAs: '{show_as}'")
                logger.info(f"  Start: {event.get('start', {}).get('dateTime', 'Unknown')}")
                logger.info(f"  End: {event.get('end', {}).get('dateTime', 'Unknown')}")
                
                # Skip events that don't show as busy (free, workingElsewhere)
                if show_as in ['free', 'workingElsewhere']:
                    logger.info(f"  Skipping event '{subject}' - showAs: '{show_as}'")
                    continue
                
                # Extract start and end times
                start_dt_str = event['start']['dateTime']
                end_dt_str = event['end']['dateTime']
                
                # Parse datetime strings (they come in ISO format from Graph API)
                if start_dt_str.endswith('Z'):
                    start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start_dt_str)
                    end_dt = datetime.fromisoformat(end_dt_str)
                
                busy_times.append({
                    'start': start_dt,
                    'end': end_dt
                })
                
                logger.info(f"  Added as busy time: {start_dt} to {end_dt}")
                
            except Exception as e:
                logger.warning(f"Error parsing Outlook event: {event}, error: {str(e)}")
                continue
        
        logger.info(f"Converted {len(busy_times)} Outlook events to busy times for user {user_id}")
        return busy_times
    
    def create_event(self, user_id, event_data):
        """Create an event in Outlook Calendar"""
        access_token = self.get_access_token(user_id)
        if not access_token:
            logger.error(f"No valid access token for user {user_id}")
            return False
        
        # Microsoft Graph API endpoint
        url = "https://graph.microsoft.com/v1.0/me/calendar/events"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, json=event_data)
            response.raise_for_status()
            
            created_event = response.json()
            logger.info(f"Created Outlook event for user {user_id}: {created_event.get('id')}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Outlook event for user {user_id}: {str(e)}")
            return False
    
    def disconnect_user(self, user_id):
        """Disconnect user's Outlook Calendar"""
        try:
            # Remove sync record
            sync_record = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
            if sync_record:
                db.session.delete(sync_record)
            
            # Update user status
            user = User.query.get(user_id)
            if user:
                user.outlook_calendar_enabled = False
            
            db.session.commit()
            logger.info(f"Outlook Calendar disconnected for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Outlook Calendar for user {user_id}: {str(e)}")
            db.session.rollback()
            return False

# Create global instance
outlook_calendar_service = OutlookCalendarService()
