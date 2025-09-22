"""
Google Calendar Scheduler for automatic availability sync
"""
import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.google_calendar_sync import GoogleCalendarSync
from app.models.availability import Availability
from app.services.google_calendar_service import google_calendar_service
from app import db

logger = logging.getLogger(__name__)

class GoogleCalendarScheduler:
    """Handles automatic Google Calendar availability sync"""
    
    @staticmethod
    def sync_all_users_availability():
        """
        Sync availability from Google Calendar for all users who have auto-sync enabled
        This should be called every 2-4 hours
        """
        logger.info("Starting automatic Google Calendar availability sync job")
        
        if not google_calendar_service.is_configured():
            logger.error("Google Calendar service not configured. Skipping sync job.")
            return
        
        try:
            # Get all users who have Google Calendar connected and auto-sync enabled
            sync_records = GoogleCalendarSync.query.filter(
                GoogleCalendarSync.sync_enabled == True,
                GoogleCalendarSync.auto_sync_availability == True
            ).all()
            
            logger.info(f"Found {len(sync_records)} users eligible for automatic sync")
            
            if not sync_records:
                logger.info("No users to sync. Job completed.")
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for sync_record in sync_records:
                try:
                    # Check if sync is needed (avoid too frequent syncs)
                    if sync_record.last_sync:
                        time_since_sync = datetime.utcnow() - sync_record.last_sync
                        if time_since_sync < timedelta(hours=1):
                            logger.debug(f"Skipping user {sync_record.user_id} - synced recently")
                            continue
                    
                    # Sync availability for this user
                    user_success = GoogleCalendarScheduler._sync_user_availability(sync_record.user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time
                        sync_record.last_sync = datetime.utcnow()
                        db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing user {sync_record.user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            stats = {'synced': success_count, 'errors': error_count}
            logger.info(f"Automatic Google Calendar sync job completed. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in automatic Google Calendar sync job: {str(e)}")
            raise
    
    @staticmethod
    def _sync_user_availability(user_id):
        """Sync availability from Google Calendar for a specific user"""
        try:
            # Check if user has Google Calendar connected
            sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            if not sync_record or not sync_record.sync_enabled:
                logger.debug(f"User {user_id} doesn't have Google Calendar sync enabled")
                return False
            
            # Sync availability for the next 4 weeks
            success_count = 0
            error_count = 0
            
            for week_offset in range(4):
                try:
                    today = datetime.now().date()
                    week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
                    week_end = week_start + timedelta(days=6)
                    
                    # Get busy times from Google Calendar
                    busy_times = google_calendar_service.get_busy_times(
                        user_id,
                        datetime.combine(week_start, datetime.min.time()),
                        datetime.combine(week_end, datetime.max.time())
                    )
                    
                    # Convert busy times to availability data
                    availability_data = GoogleCalendarScheduler._convert_busy_times_to_availability(busy_times, week_start)
                    
                    # Update availability in database
                    availability = Availability.get_or_create_availability(user_id, week_start)
                    availability.set_availability_data(availability_data)
                    availability.updated_at = datetime.utcnow()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing week {week_offset} for user {user_id}: {str(e)}")
                    error_count += 1
            
            if success_count > 0:
                db.session.commit()
                logger.info(f"Successfully synced {success_count} weeks for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to sync any weeks for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing availability for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _convert_busy_times_to_availability(busy_times, week_start):
        """Convert Google Calendar busy times to availability data format"""
        # Initialize all time slots as available (True)
        availability_data = {}
        
        # Days of the week (0 = Monday, 6 = Sunday)
        for day in range(7):
            current_date = week_start + timedelta(days=day)
            day_key = current_date.strftime('%Y-%m-%d')
            
            # Initialize all hours as available
            availability_data[day_key] = {
                'available': True,
                'start_time': '06:00',
                'end_time': '23:00'
            }
        
        # Mark busy times as unavailable
        for busy_period in busy_times:
            start_time = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
            
            # Convert to local date
            start_date = start_time.date()
            end_date = end_time.date()
            
            # Handle busy periods that span multiple days
            current_date = start_date
            while current_date <= end_date:
                if week_start <= current_date <= week_start + timedelta(days=6):
                    day_key = current_date.strftime('%Y-%m-%d')
                    
                    # Determine the busy hours for this day
                    day_start = max(start_time, datetime.combine(current_date, datetime.min.time()))
                    day_end = min(end_time, datetime.combine(current_date, datetime.max.time()))
                    
                    # If the entire day is busy, mark as unavailable
                    if (day_end - day_start).total_seconds() >= 8 * 3600:  # 8+ hours busy
                        availability_data[day_key]['available'] = False
                    else:
                        # For partial day busy periods, we keep the day available
                        # The user can manually adjust if needed
                        pass
                
                current_date += timedelta(days=1)
        
        return availability_data
    
    @staticmethod
    def sync_user_now(user_id):
        """
        Manually trigger sync for a specific user (for testing or immediate sync)
        """
        try:
            success = GoogleCalendarScheduler._sync_user_availability(user_id)
            
            if success:
                logger.info(f"Manual sync completed successfully for user {user_id}")
            else:
                logger.warning(f"Manual sync failed for user {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error in manual sync for user {user_id}: {str(e)}")
            return False

# Global instance
google_calendar_scheduler = GoogleCalendarScheduler()
