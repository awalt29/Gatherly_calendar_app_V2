"""
Unified Calendar Scheduler for automatic availability sync
Handles both Google Calendar and Outlook Calendar sync
"""
import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.models.google_calendar_sync import GoogleCalendarSync
from app.models.outlook_calendar_sync import OutlookCalendarSync
from app.models.availability import Availability
from app.services.google_calendar_service import google_calendar_service
from app.services.outlook_calendar_service import outlook_calendar_service
from app import db

logger = logging.getLogger(__name__)

class CalendarScheduler:
    """Handles automatic calendar availability sync for both Google and Outlook"""
    
    @staticmethod
    def sync_all_users_availability():
        """
        Sync availability from both Google Calendar and Outlook Calendar for all users who have auto-sync enabled
        This should be called every 2-4 hours
        """
        logger.info("Starting automatic calendar availability sync job (Google + Outlook)")
        
        total_stats = {'unified': {'synced': 0, 'errors': 0}, 'google_only': {'synced': 0, 'errors': 0}, 'outlook_only': {'synced': 0, 'errors': 0}}
        
        # First, sync users who have both Google AND Outlook calendars (unified approach)
        unified_stats = CalendarScheduler._sync_unified_calendar_users()
        total_stats['unified'] = unified_stats
        
        # Then sync Google-only users
        if google_calendar_service.is_configured():
            logger.info("Syncing Google-only Calendar users...")
            google_stats = CalendarScheduler._sync_google_only_users()
            total_stats['google_only'] = google_stats
        else:
            logger.warning("Google Calendar service not configured. Skipping Google sync.")
        
        # Then sync Outlook-only users
        if outlook_calendar_service.is_configured():
            logger.info("Syncing Outlook-only Calendar users...")
            outlook_stats = CalendarScheduler._sync_outlook_only_users()
            total_stats['outlook_only'] = outlook_stats
        else:
            logger.warning("Outlook Calendar service not configured. Skipping Outlook sync.")
        
        logger.info(f"Calendar sync job completed. Stats: {total_stats}")
        return total_stats
    
    @staticmethod
    def _sync_unified_calendar_users():
        """Sync users who have both Google and Outlook calendars - combine busy times"""
        logger.info("Syncing users with both Google and Outlook calendars...")
        
        try:
            # Find users who have both Google AND Outlook sync enabled
            google_users = set()
            outlook_users = set()
            
            if google_calendar_service.is_configured():
                google_records = GoogleCalendarSync.query.filter(
                    GoogleCalendarSync.sync_enabled == True,
                    GoogleCalendarSync.auto_sync_availability == True
                ).all()
                google_users = {record.user_id for record in google_records}
            
            if outlook_calendar_service.is_configured():
                outlook_records = OutlookCalendarSync.query.filter(
                    OutlookCalendarSync.sync_enabled == True,
                    OutlookCalendarSync.auto_sync_availability == True
                ).all()
                outlook_users = {record.user_id for record in outlook_records}
            
            # Find users who have BOTH calendars
            unified_users = google_users.intersection(outlook_users)
            logger.info(f"Found {len(unified_users)} users with both Google and Outlook calendars")
            
            if not unified_users:
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for user_id in unified_users:
                try:
                    # Rate limiting temporarily disabled for testing
                    # Check both sync records for rate limiting
                    google_sync = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
                    outlook_sync = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
                    
                    # Sync availability for this user with combined calendars
                    user_success = CalendarScheduler._sync_user_unified_calendars(user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time for both calendars
                        if google_sync:
                            google_sync.last_sync = datetime.utcnow()
                        if outlook_sync:
                            outlook_sync.last_sync = datetime.utcnow()
                        db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing unified calendars for user {user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            return {'synced': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Error in unified calendar sync: {str(e)}")
            return {'synced': 0, 'errors': 1}
    
    @staticmethod
    def _sync_google_only_users():
        """Sync users who have ONLY Google Calendar (not Outlook)"""
        try:
            # Get Google users
            google_records = GoogleCalendarSync.query.filter(
                GoogleCalendarSync.sync_enabled == True,
                GoogleCalendarSync.auto_sync_availability == True
            ).all()
            google_user_ids = {record.user_id for record in google_records}
            
            # Get Outlook users
            outlook_records = OutlookCalendarSync.query.filter(
                OutlookCalendarSync.sync_enabled == True,
                OutlookCalendarSync.auto_sync_availability == True
            ).all()
            outlook_user_ids = {record.user_id for record in outlook_records}
            
            # Find Google-only users (have Google but not Outlook)
            google_only_users = google_user_ids - outlook_user_ids
            logger.info(f"Found {len(google_only_users)} Google-only users")
            
            if not google_only_users:
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for user_id in google_only_users:
                try:
                    user_success = CalendarScheduler._sync_user_google_calendar(user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time
                        sync_record = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
                        if sync_record:
                            sync_record.last_sync = datetime.utcnow()
                            db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing Google Calendar for user {user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            return {'synced': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Error in Google-only calendar sync: {str(e)}")
            return {'synced': 0, 'errors': 1}
    
    @staticmethod
    def _sync_outlook_only_users():
        """Sync users who have ONLY Outlook Calendar (not Google)"""
        try:
            # Get Google users
            google_records = GoogleCalendarSync.query.filter(
                GoogleCalendarSync.sync_enabled == True,
                GoogleCalendarSync.auto_sync_availability == True
            ).all()
            google_user_ids = {record.user_id for record in google_records}
            
            # Get Outlook users
            outlook_records = OutlookCalendarSync.query.filter(
                OutlookCalendarSync.sync_enabled == True,
                OutlookCalendarSync.auto_sync_availability == True
            ).all()
            outlook_user_ids = {record.user_id for record in outlook_records}
            
            # Find Outlook-only users (have Outlook but not Google)
            outlook_only_users = outlook_user_ids - google_user_ids
            logger.info(f"Found {len(outlook_only_users)} Outlook-only users")
            
            if not outlook_only_users:
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for user_id in outlook_only_users:
                try:
                    user_success = CalendarScheduler._sync_user_outlook_calendar(user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time
                        sync_record = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
                        if sync_record:
                            sync_record.last_sync = datetime.utcnow()
                            db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing Outlook Calendar for user {user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            return {'synced': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Error in Outlook-only calendar sync: {str(e)}")
            return {'synced': 0, 'errors': 1}
    
    @staticmethod
    def _sync_google_calendar_users():
        """Sync Google Calendar users"""
        try:
            # Get all users who have Google Calendar connected and auto-sync enabled
            sync_records = GoogleCalendarSync.query.filter(
                GoogleCalendarSync.sync_enabled == True,
                GoogleCalendarSync.auto_sync_availability == True
            ).all()
            
            logger.info(f"Found {len(sync_records)} Google Calendar users eligible for automatic sync")
            
            if not sync_records:
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for sync_record in sync_records:
                try:
                    # Rate limiting temporarily disabled for testing
                    # if sync_record.last_sync:
                    #     time_since_sync = datetime.utcnow() - sync_record.last_sync
                    #     if time_since_sync < timedelta(hours=1):
                    #         logger.debug(f"Skipping Google user {sync_record.user_id} - synced recently")
                    #         continue
                    
                    # Sync availability for this user
                    user_success = CalendarScheduler._sync_user_google_calendar(sync_record.user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time
                        sync_record.last_sync = datetime.utcnow()
                        db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing Google Calendar for user {sync_record.user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            return {'synced': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Error in Google Calendar sync: {str(e)}")
            return {'synced': 0, 'errors': 1}
    
    @staticmethod
    def _sync_outlook_calendar_users():
        """Sync Outlook Calendar users"""
        try:
            # Get all users who have Outlook Calendar connected and auto-sync enabled
            sync_records = OutlookCalendarSync.query.filter(
                OutlookCalendarSync.sync_enabled == True,
                OutlookCalendarSync.auto_sync_availability == True
            ).all()
            
            logger.info(f"Found {len(sync_records)} Outlook Calendar users eligible for automatic sync")
            
            if not sync_records:
                return {'synced': 0, 'errors': 0}
            
            success_count = 0
            error_count = 0
            
            for sync_record in sync_records:
                try:
                    # Rate limiting temporarily disabled for testing
                    # if sync_record.last_sync:
                    #     time_since_sync = datetime.utcnow() - sync_record.last_sync
                    #     if time_since_sync < timedelta(hours=1):
                    #         logger.debug(f"Skipping Outlook user {sync_record.user_id} - synced recently")
                    #         continue
                    
                    # Sync availability for this user
                    user_success = CalendarScheduler._sync_user_outlook_calendar(sync_record.user_id)
                    
                    if user_success:
                        success_count += 1
                        # Update last sync time
                        sync_record.last_sync = datetime.utcnow()
                        db.session.commit()
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing Outlook Calendar for user {sync_record.user_id}: {str(e)}")
                    error_count += 1
                    db.session.rollback()
            
            return {'synced': success_count, 'errors': error_count}
            
        except Exception as e:
            logger.error(f"Error in Outlook Calendar sync: {str(e)}")
            return {'synced': 0, 'errors': 1}
    
    @staticmethod
    def _sync_user_google_calendar(user_id):
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
                    availability_data = CalendarScheduler._convert_busy_times_to_availability_format(busy_times, week_start, user_id)
                    
                    # Update availability in database - merge with existing data
                    availability = Availability.get_or_create_availability(user_id, week_start)
                    existing_data = availability.get_availability_data()
                    
                    # Only update days that have changes, preserve others
                    for day_name, day_data in availability_data.items():
                        existing_data[day_name] = day_data
                    
                    availability.set_availability_data(existing_data)
                    availability.updated_at = datetime.utcnow()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing Google Calendar week {week_offset} for user {user_id}: {str(e)}")
                    error_count += 1
            
            if success_count > 0:
                db.session.commit()
                logger.info(f"Successfully synced {success_count} Google Calendar weeks for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to sync any Google Calendar weeks for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing Google Calendar availability for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _sync_user_outlook_calendar(user_id):
        """Sync availability from Outlook Calendar for a specific user"""
        try:
            # Check if user has Outlook Calendar connected
            sync_record = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
            if not sync_record or not sync_record.sync_enabled:
                logger.debug(f"User {user_id} doesn't have Outlook Calendar sync enabled")
                return False
            
            # Sync availability for the next 4 weeks
            success_count = 0
            error_count = 0
            
            for week_offset in range(4):
                try:
                    today = datetime.now().date()
                    week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
                    week_end = week_start + timedelta(days=6)
                    
                    # Get busy times from Outlook Calendar
                    busy_times = outlook_calendar_service.get_busy_times(
                        user_id,
                        datetime.combine(week_start, datetime.min.time()),
                        datetime.combine(week_end, datetime.max.time())
                    )
                    
                    # Convert busy times to availability data
                    availability_data = CalendarScheduler._convert_busy_times_to_availability_format(busy_times, week_start, user_id)
                    
                    # Update availability in database - merge with existing data
                    availability = Availability.get_or_create_availability(user_id, week_start)
                    existing_data = availability.get_availability_data()
                    
                    # Only update days that have changes, preserve others
                    for day_name, day_data in availability_data.items():
                        existing_data[day_name] = day_data
                    
                    availability.set_availability_data(existing_data)
                    availability.updated_at = datetime.utcnow()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing Outlook Calendar week {week_offset} for user {user_id}: {str(e)}")
                    error_count += 1
            
            if success_count > 0:
                db.session.commit()
                logger.info(f"Successfully synced {success_count} Outlook Calendar weeks for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to sync any Outlook Calendar weeks for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing Outlook Calendar availability for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _convert_busy_times_to_availability_format(busy_times, week_start, user_id):
        """Convert calendar busy times to Gatherly availability format with multiple time ranges"""
        # Get existing user availability to preserve their preferences
        existing_availability = Availability.query.filter_by(
            user_id=user_id,
            week_start_date=week_start
        ).first()
        
        availability_data = {}
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            day_name = day_names[current_date.weekday()]  # Monday = 0
            
            # Find busy periods for this day first
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
            
            # Only process days that have busy times - skip days with no calendar conflicts
            if not day_busy_times:
                continue
                
            # Get existing availability for this day (only for days with conflicts)
            existing_day_data = {}
            if existing_availability:
                existing_day_data = existing_availability.get_day_availability(day_name)
            
            # Process availability based on existing preferences and busy times
            if existing_day_data.get('available', False):
                # User had availability set - adjust it based on busy times
                existing_time_ranges = existing_day_data.get('time_ranges', [])
                if not existing_time_ranges:
                    # Fallback to single time range
                    existing_time_ranges = [{
                        'start': existing_day_data.get('start', '09:00'),
                        'end': existing_day_data.get('end', '17:00')
                    }]
                
                # Remove busy times from existing availability
                available_ranges = CalendarScheduler._subtract_busy_times_from_ranges(existing_time_ranges, day_busy_times)
                
                if available_ranges:
                    # Update the first range for backward compatibility
                    first_range = available_ranges[0]
                    availability_data[day_name] = {
                        'available': True,
                        'start': first_range['start'],
                        'end': first_range['end'],
                        'time_ranges': available_ranges,
                        'all_day': False
                    }
                else:
                    # No available time left
                    availability_data[day_name] = {
                        'available': False,
                        'start': existing_day_data.get('start', '09:00'),
                        'end': existing_day_data.get('end', '17:00'),
                        'time_ranges': [],
                        'all_day': False
                    }
            else:
                # User didn't have availability set for this day - preserve existing data exactly
                if existing_day_data:
                    availability_data[day_name] = existing_day_data
                # If no existing data, don't add anything - let the day remain as it was
        
        return availability_data
    
    @staticmethod
    def _subtract_busy_times_from_ranges(time_ranges, busy_times):
        """Remove busy time periods from available time ranges"""
        def time_to_minutes(time_str):
            if isinstance(time_str, str):
                # Handle both 24-hour format (HH:MM) and 12-hour format (H:MM AM/PM)
                if 'AM' in time_str or 'PM' in time_str:
                    # Parse 12-hour format
                    time_part = time_str.replace(' AM', '').replace(' PM', '')
                    hours, minutes = time_part.split(':')
                    hours = int(hours)
                    minutes = int(minutes)
                    
                    if 'PM' in time_str and hours != 12:
                        hours += 12
                    elif 'AM' in time_str and hours == 12:
                        hours = 0
                        
                    return hours * 60 + minutes
                else:
                    # Parse 24-hour format
                    hours, minutes = time_str.split(':')
                    return int(hours) * 60 + int(minutes)
            else:  # time object
                return time_str.hour * 60 + time_str.minute
        
        def minutes_to_time_str(minutes):
            hours = minutes // 60
            mins = minutes % 60
            # Convert to 12-hour format to match manually set availability
            if hours == 0:
                return f"12:{mins:02d} AM"
            elif hours < 12:
                return f"{hours}:{mins:02d} AM"
            elif hours == 12:
                return f"12:{mins:02d} PM"
            else:
                return f"{hours - 12}:{mins:02d} PM"
        
        available_ranges = []
        
        for time_range in time_ranges:
            range_start = time_to_minutes(time_range['start'])
            range_end = time_to_minutes(time_range['end'])
            
            # Start with the full range
            current_ranges = [(range_start, range_end)]
            
            # Subtract each busy time
            for busy_time in busy_times:
                busy_start = time_to_minutes(busy_time['start'])
                busy_end = time_to_minutes(busy_time['end'])
                
                new_ranges = []
                for start, end in current_ranges:
                    if busy_end <= start or busy_start >= end:
                        # No overlap
                        new_ranges.append((start, end))
                    else:
                        # There's overlap - split the range
                        if start < busy_start:
                            # Keep the part before the busy time
                            new_ranges.append((start, busy_start))
                        if busy_end < end:
                            # Keep the part after the busy time
                            new_ranges.append((busy_end, end))
                
                current_ranges = new_ranges
            
            # Convert back to time ranges and filter out very short periods
            for start_min, end_min in current_ranges:
                duration_minutes = end_min - start_min
                if duration_minutes >= 30:  # At least 30 minutes
                    available_ranges.append({
                        'start': minutes_to_time_str(start_min),
                        'end': minutes_to_time_str(end_min)
                    })
        
        return available_ranges
    
    @staticmethod
    def _sync_user_unified_calendars(user_id):
        """Sync availability from both Google and Outlook calendars for a specific user - combines busy times"""
        try:
            # Check if user has both calendars connected
            google_sync = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            outlook_sync = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
            
            if not (google_sync and google_sync.sync_enabled and outlook_sync and outlook_sync.sync_enabled):
                logger.debug(f"User {user_id} doesn't have both Google and Outlook Calendar sync enabled")
                return False
            
            # Sync availability for the next 4 weeks
            success_count = 0
            error_count = 0
            
            for week_offset in range(4):
                try:
                    today = datetime.now().date()
                    week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
                    week_end = week_start + timedelta(days=6)
                    
                    # Get busy times from BOTH calendars
                    combined_busy_times = []
                    
                    # Get Google Calendar busy times
                    try:
                        google_busy_times = google_calendar_service.get_busy_times(
                            user_id,
                            datetime.combine(week_start, datetime.min.time()),
                            datetime.combine(week_end, datetime.max.time())
                        )
                        if google_busy_times:
                            combined_busy_times.extend(google_busy_times)
                            logger.debug(f"Found {len(google_busy_times)} Google busy periods for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Error getting Google busy times for user {user_id}: {str(e)}")
                    
                    # Get Outlook Calendar busy times
                    try:
                        outlook_busy_times = outlook_calendar_service.get_busy_times(
                            user_id,
                            datetime.combine(week_start, datetime.min.time()),
                            datetime.combine(week_end, datetime.max.time())
                        )
                        if outlook_busy_times:
                            combined_busy_times.extend(outlook_busy_times)
                            logger.debug(f"Found {len(outlook_busy_times)} Outlook busy periods for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Error getting Outlook busy times for user {user_id}: {str(e)}")
                    
                    logger.info(f"Combined {len(combined_busy_times)} total busy periods from both calendars for user {user_id}")
                    
                    # Convert combined busy times to availability data
                    availability_data = CalendarScheduler._convert_busy_times_to_availability_format(combined_busy_times, week_start, user_id)
                    
                    # Update availability in database - merge with existing data
                    availability = Availability.get_or_create_availability(user_id, week_start)
                    existing_data = availability.get_availability_data()
                    
                    # Only update days that have changes, preserve others
                    for day_name, day_data in availability_data.items():
                        existing_data[day_name] = day_data
                    
                    availability.set_availability_data(existing_data)
                    availability.updated_at = datetime.utcnow()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing unified calendars week {week_offset} for user {user_id}: {str(e)}")
                    error_count += 1
            
            if success_count > 0:
                db.session.commit()
                logger.info(f"Successfully synced {success_count} unified calendar weeks for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to sync any unified calendar weeks for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing unified calendars for user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def sync_user_now(user_id):
        """
        Manually trigger sync for a specific user (for testing or immediate sync)
        Syncs both Google and Outlook calendars if connected
        """
        results = {'google': False, 'outlook': False}
        
        try:
            # Try Google Calendar sync
            google_sync = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
            if google_sync and google_sync.sync_enabled:
                results['google'] = CalendarScheduler._sync_user_google_calendar(user_id)
                logger.info(f"Manual Google Calendar sync for user {user_id}: {'success' if results['google'] else 'failed'}")
            
            # Try Outlook Calendar sync
            outlook_sync = OutlookCalendarSync.query.filter_by(user_id=user_id).first()
            if outlook_sync and outlook_sync.sync_enabled:
                results['outlook'] = CalendarScheduler._sync_user_outlook_calendar(user_id)
                logger.info(f"Manual Outlook Calendar sync for user {user_id}: {'success' if results['outlook'] else 'failed'}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in manual sync for user {user_id}: {str(e)}")
            return results

# Global instance
calendar_scheduler = CalendarScheduler()
