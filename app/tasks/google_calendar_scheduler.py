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
                    
                # Convert busy times to availability data using the same logic as manual sync
                availability_data = GoogleCalendarScheduler._convert_busy_times_to_availability_format(busy_times, week_start)
                    
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
    def _convert_busy_times_to_availability_format(busy_times, week_start):
        """Convert Google Calendar busy times to Gatherly availability format (matching manual sync)"""
        # Default availability: 9 AM to 5 PM on weekdays (same as manual sync)
        default_start = "09:00"
        default_end = "17:00"
        
        availability_data = {}
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            day_name = day_names[current_date.weekday()]  # Monday = 0
            
            # Check if it's a weekday (default available) or weekend (default not available)
            is_weekday = current_date.weekday() < 5
            
            # Find busy periods for this day
            day_busy_times = []
            for busy_period in busy_times:
                try:
                    # Handle both datetime and date formats
                    if isinstance(busy_period['start'], str):
                        if 'T' in busy_period['start']:
                            busy_start_dt = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                            busy_end_dt = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                        else:
                            busy_start_dt = datetime.strptime(busy_period['start'], '%Y-%m-%d')
                            busy_end_dt = datetime.strptime(busy_period['end'], '%Y-%m-%d')
                    else:
                        # Already datetime objects
                        busy_start_dt = busy_period['start']
                        busy_end_dt = busy_period['end']
                    
                    busy_start = busy_start_dt.date()
                    busy_end = busy_end_dt.date()
                    
                    # If busy period spans this day
                    if busy_start <= current_date <= busy_end:
                        # Extract time portion if it's the same day
                        if busy_start == current_date:
                            start_time = busy_start_dt.time()
                        else:
                            start_time = datetime.min.time()
                        
                        if busy_end == current_date:
                            end_time = busy_end_dt.time()
                        else:
                            end_time = datetime.max.time()
                        
                        day_busy_times.append({
                            'start': start_time,
                            'end': end_time
                        })
                except Exception as e:
                    logger.error(f"Error parsing busy period: {busy_period}, error: {str(e)}")
                    continue
            
            # Determine availability based on busy times (same logic as manual sync)
            if is_weekday and not day_busy_times:
                # Weekday with no conflicts - available default hours
                availability_data[day_name] = {
                    'available': True,
                    'start': default_start,
                    'end': default_end,
                    'all_day': False
                }
            elif is_weekday and day_busy_times:
                # Weekday with conflicts - find largest available block
                largest_block = GoogleCalendarScheduler._find_largest_available_block(day_busy_times)
                
                if largest_block and largest_block[2] >= 2:  # At least 2 hours
                    start_time, end_time, duration_hours = largest_block
                    availability_data[day_name] = {
                        'available': True,
                        'start': start_time.strftime('%H:%M'),
                        'end': end_time.strftime('%H:%M'),
                        'all_day': False
                    }
                else:
                    # No suitable time block found
                    availability_data[day_name] = {
                        'available': False,
                        'start': default_start,
                        'end': default_end,
                        'all_day': False
                    }
            else:
                # Weekend - default to not available
                availability_data[day_name] = {
                    'available': False,
                    'start': default_start,
                    'end': default_end,
                    'all_day': False
                }
        
        return availability_data
    
    @staticmethod
    def _find_largest_available_block(busy_periods):
        """
        Find the largest continuous available time block in a day
        
        Args:
            busy_periods: List of {'start': time, 'end': time} busy periods
            
        Returns:
            Tuple of (start_time, end_time, duration_hours) or None if no block >= 2 hours
        """
        from datetime import time
        
        # Define the full day range (6 AM to 11 PM)
        day_start = time(6, 0)  # 6:00 AM
        day_end = time(23, 0)   # 11:00 PM
        
        # Sort busy periods by start time
        sorted_busy = sorted(busy_periods, key=lambda x: x['start'])
        
        # Find all available blocks
        available_blocks = []
        current_time = day_start
        
        for busy in sorted_busy:
            # If there's a gap before this busy period
            if current_time < busy['start']:
                # Calculate duration in hours
                start_minutes = current_time.hour * 60 + current_time.minute
                end_minutes = busy['start'].hour * 60 + busy['start'].minute
                duration_hours = (end_minutes - start_minutes) / 60
                
                available_blocks.append({
                    'start': current_time,
                    'end': busy['start'],
                    'duration': duration_hours
                })
            
            # Move current time to end of this busy period
            current_time = max(current_time, busy['end'])
        
        # Check for available time after the last busy period
        if current_time < day_end:
            start_minutes = current_time.hour * 60 + current_time.minute
            end_minutes = day_end.hour * 60 + day_end.minute
            duration_hours = (end_minutes - start_minutes) / 60
            
            available_blocks.append({
                'start': current_time,
                'end': day_end,
                'duration': duration_hours
            })
        
        # Find the largest block that's at least 2 hours
        largest_block = None
        max_duration = 0
        
        for block in available_blocks:
            if block['duration'] >= 2 and block['duration'] > max_duration:
                max_duration = block['duration']
                largest_block = (block['start'], block['end'], block['duration'])
        
        return largest_block
    
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
