from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.availability import Availability
from app.models.default_schedule import DefaultSchedule
from app.models.google_calendar_sync import GoogleCalendarSync
from app.services.google_calendar_service import google_calendar_service
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('availability', __name__)

@bp.route('/availability')
@login_required
def index():
    """Availability setting page"""
    return render_template('availability/index.html')

@bp.route('/availability/google-status')
@login_required
def google_calendar_status():
    """Check Google Calendar integration status"""
    try:
        status = {
            'service_configured': google_calendar_service.is_configured(),
            'user_connected': False,
            'sync_enabled': False
        }
        
        sync_record = GoogleCalendarSync.query.filter_by(user_id=current_user.id).first()
        if sync_record:
            status['user_connected'] = True
            status['sync_enabled'] = sync_record.sync_enabled
            
        logger.info(f"Google Calendar status for user {current_user.id}: {status}")
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error checking Google Calendar status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/availability/api/<date>')
@login_required
def get_availability_data(date):
    """Get availability data for a specific week"""
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        week_start = Availability.get_week_start(date_obj)
        
        availability = Availability.query.filter_by(
            user_id=current_user.id,
            week_start_date=week_start
        ).first()
        
        if availability:
            return jsonify({
                'week_start': week_start.strftime('%Y-%m-%d'),
                'availability_data': availability.get_availability_data()
            })
        else:
            return jsonify({
                'week_start': week_start.strftime('%Y-%m-%d'),
                'availability_data': {}
            })
    
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

@bp.route('/availability/submit', methods=['POST'])
@login_required
def submit_availability():
    """Submit availability data for a week"""
    try:
        data = request.get_json()
        week_start_str = data.get('week_start')
        availability_data = data.get('availability_data', {})
        
        if not week_start_str:
            return jsonify({'error': 'Week start date is required'}), 400
        
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        
        # Get or create availability record
        availability = Availability.get_or_create_availability(
            current_user.id, 
            week_start
        )
        
        # Update availability data
        availability.set_availability_data(availability_data)
        availability.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Availability updated successfully'})
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/availability/week/<int:week_offset>')
@login_required
def get_week_availability(week_offset):
    """Get availability data for a specific week offset"""
    try:
        # Use a fixed reference date to ensure consistent week calculations
        # Use the start of the current week as the reference point
        today = datetime.now().date()
        reference_week_start = Availability.get_week_start(today)
        week_start = reference_week_start + timedelta(weeks=week_offset)
        
        availability = Availability.query.filter_by(
            user_id=current_user.id,
            week_start_date=week_start
        ).first()
        
        auto_applied_this_request = False
        
        # If no availability exists for this week and it's current week or future, check for default schedule
        if not availability and week_offset >= 0:
            logger.info(f"No availability found for week {week_offset}, checking for default schedule")
            default_schedule = DefaultSchedule.get_active_default(current_user.id)
            if default_schedule:
                logger.info(f"Found default schedule, applying to week {week_offset}")
                # Create new availability with default schedule
                availability = Availability(
                    user_id=current_user.id,
                    week_start_date=week_start
                )
                availability.set_availability_data(default_schedule.get_schedule_data())
                db.session.add(availability)
                db.session.commit()
                auto_applied_this_request = True
                logger.info(f"Auto-applied default schedule to week {week_offset} for user {current_user.id}")
            else:
                logger.info(f"No default schedule found for user {current_user.id}")
        
        # Calculate the actual week offset from the reference point (current week)
        current_week_start = Availability.get_week_start(today)
        actual_week_offset = (week_start - current_week_start).days // 7
        
        week_data = {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            'availability_data': availability.get_availability_data() if availability else {},
            'auto_applied_default': auto_applied_this_request,
            'actual_week_offset': actual_week_offset,
            'requested_week_offset': week_offset
        }
        
        # Add day information - Sunday first (US calendar format)
        days = []
        for day_offset in [-1, 0, 1, 2, 3, 4, 5]:  # Sunday first, then Mon-Sat
            current_date = week_start + timedelta(days=day_offset)
            day_name = current_date.strftime('%A').lower()
            
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'day_name': day_name,
                'day_short': current_date.strftime('%a'),
                'day_number': current_date.day,
                'is_today': current_date == today
            }
            days.append(day_data)
        
        week_data['days'] = days
        
        return jsonify(week_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/availability/sync-google', methods=['POST'])
@login_required
def sync_from_google_calendar():
    """Sync availability from Google Calendar"""
    try:
        print(f"[SYNC] Starting Google Calendar sync for user {current_user.id}")
        
        # First, check if Google Calendar is configured at all
        if not google_calendar_service.is_configured():
            print("[SYNC] ERROR: Google Calendar service not configured - missing environment variables")
            return jsonify({'success': False, 'error': 'Google Calendar integration not configured on server'}), 500
        
        print("[SYNC] Google Calendar service is properly configured")
        
        # Check if user has Google Calendar connected
        sync_record = GoogleCalendarSync.query.filter_by(user_id=current_user.id).first()
        if not sync_record:
            print(f"[SYNC] ERROR: No Google Calendar sync record found for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Google Calendar not connected'}), 400
        
        if not sync_record.sync_enabled:
            print(f"[SYNC] ERROR: Google Calendar sync disabled for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Google Calendar sync disabled'}), 400
        
        print(f"[SYNC] Found Google Calendar sync record for user {current_user.id}, sync_enabled: {sync_record.sync_enabled}")
        
        # Test if we can get Google Calendar service
        service = google_calendar_service.get_calendar_service(current_user.id)
        if not service:
            logger.error(f"Failed to get Google Calendar service for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Failed to connect to Google Calendar service'}), 400
        
        logger.info(f"Successfully got Google Calendar service for user {current_user.id}")
        
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
                    current_user.id,
                    datetime.combine(week_start, datetime.min.time()),
                    datetime.combine(week_end, datetime.max.time())
                )
                
                # Debug logging
                print(f"[SYNC] Google Calendar sync for user {current_user.id}, week {week_start}")
                print(f"[SYNC] Found {len(busy_times)} busy periods: {busy_times}")
                
                # Convert busy times to availability data
                availability_data = _convert_busy_times_to_availability(busy_times, week_start)
                print(f"[SYNC] Converted to availability data: {availability_data}")
                
                # Update availability in database
                availability = Availability.get_or_create_availability(current_user.id, week_start)
                availability.set_availability_data(availability_data)
                availability.updated_at = datetime.utcnow()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing week {week_offset} for user {current_user.id}: {str(e)}")
                error_count += 1
        
        # Update last sync time
        sync_record.last_sync = datetime.utcnow()
        db.session.commit()
        
        if success_count > 0:
            message = f'Successfully synced {success_count} weeks from Google Calendar'
            if error_count > 0:
                message += f' ({error_count} weeks had errors)'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': 'Failed to sync any weeks from Google Calendar'}), 500
        
    except Exception as e:
        logger.error(f"Error syncing Google Calendar for user {current_user.id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/availability/sync-outlook', methods=['POST'])
@login_required
def sync_from_outlook_calendar():
    """Sync availability from Outlook Calendar"""
    try:
        from app.services.outlook_calendar_service import outlook_calendar_service
        from app.models.outlook_calendar_sync import OutlookCalendarSync
        
        print(f"[SYNC] Starting Outlook Calendar sync for user {current_user.id}")
        
        # First, check if Outlook Calendar is configured at all
        if not outlook_calendar_service.is_configured():
            print("[SYNC] ERROR: Outlook Calendar service not configured - missing environment variables")
            return jsonify({'success': False, 'error': 'Outlook Calendar integration not configured on server'}), 500
        
        print("[SYNC] Outlook Calendar service is properly configured")
        
        # Check if user has Outlook Calendar connected
        sync_record = OutlookCalendarSync.query.filter_by(user_id=current_user.id).first()
        if not sync_record:
            print(f"[SYNC] ERROR: No Outlook Calendar sync record found for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Outlook Calendar not connected'}), 400
        
        if not sync_record.sync_enabled:
            print(f"[SYNC] ERROR: Outlook Calendar sync disabled for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Outlook Calendar sync disabled'}), 400
        
        print(f"[SYNC] Found Outlook Calendar sync record for user {current_user.id}, sync_enabled: {sync_record.sync_enabled}")
        
        # Test if we can get access token
        access_token = outlook_calendar_service.get_access_token(current_user.id)
        if not access_token:
            logger.error(f"Failed to get Outlook Calendar access token for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Failed to connect to Outlook Calendar service'}), 400
        
        logger.info(f"Successfully got Outlook Calendar access token for user {current_user.id}")
        
        # Sync availability for the next 4 weeks
        success_count = 0
        error_count = 0
        
        for week_offset in range(4):
            try:
                today = datetime.now().date()
                week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
                week_end = week_start + timedelta(days=6)
                
                # Get busy times from Outlook Calendar
                start_datetime = datetime.combine(week_start, datetime.min.time())
                end_datetime = datetime.combine(week_end, datetime.max.time())
                
                events = outlook_calendar_service.get_calendar_events(
                    current_user.id, 
                    start_datetime, 
                    end_datetime
                )
                
                # Convert Outlook events to busy times
                busy_times = []
                for event in events:
                    # Skip free/tentative events, only mark busy/out-of-office as unavailable
                    show_as = event.get('showAs', 'busy').lower()
                    if show_as in ['busy', 'oof', 'workingelsewhere']:
                        start_str = event['start']['dateTime']
                        end_str = event['end']['dateTime']
                        
                        # Parse ISO datetime strings
                        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        
                        busy_times.append({
                            'start': start_dt,
                            'end': end_dt,
                            'summary': event.get('subject', 'Busy')
                        })
                
                print(f"[SYNC] Found {len(busy_times)} busy periods for week {week_offset}")
                logger.info(f"[SYNC] Busy times for week {week_offset}: {busy_times}")
                logger.info(f"[SYNC] Week start: {week_start}, Week end: {week_end}")
                
                # Convert to availability format and save
                availability_data = _convert_busy_times_to_availability(busy_times, week_start)
                logger.info(f"[SYNC] Converted availability data: {availability_data}")
                
                # Get or create availability record
                availability = Availability.query.filter_by(
                    user_id=current_user.id,
                    week_start_date=week_start
                ).first()
                
                if not availability:
                    availability = Availability(
                        user_id=current_user.id,
                        week_start_date=week_start
                    )
                    db.session.add(availability)
                
                # Update availability data using the same method as Google Calendar sync
                availability.set_availability_data(availability_data)
                availability.updated_at = datetime.utcnow()
                
                success_count += 1
                print(f"[SYNC] Successfully synced week {week_offset} (starting {week_start})")
                
            except Exception as week_error:
                error_count += 1
                logger.error(f"Error syncing Outlook Calendar week {week_offset} for user {current_user.id}: {str(week_error)}")
                continue
        
        # Update last sync time
        sync_record.last_sync = datetime.utcnow()
        db.session.commit()
        
        if success_count > 0:
            message = f'Successfully synced {success_count} weeks from Outlook Calendar'
            if error_count > 0:
                message += f' ({error_count} weeks had errors)'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': 'Failed to sync any weeks from Outlook Calendar'}), 500
        
    except Exception as e:
        logger.error(f"Error syncing Outlook Calendar for user {current_user.id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def _convert_busy_times_to_availability(busy_times, week_start):
    """Convert Google Calendar busy times to Gatherly availability format with multiple time ranges"""
    from flask import current_app
    
    # Get existing user availability to preserve their preferences
    existing_availability = Availability.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()
    
    availability_data = {}
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        day_name = day_names[current_date.weekday()]  # Monday = 0
        
        # Get existing availability for this day
        existing_day_data = {}
        if existing_availability:
            existing_day_data = existing_availability.get_day_availability(day_name)
        
        # Find busy periods for this day
        day_busy_times = []
        for busy_period in busy_times:
            busy_start = busy_period['start'].date()
            busy_end = busy_period['end'].date()
            
            # If busy period spans this day
            if busy_start <= current_date <= busy_end:
                # Extract time portion if it's the same day
                if busy_start == current_date:
                    start_time = busy_period['start'].time()
                else:
                    start_time = datetime.min.time()
                
                if busy_end == current_date:
                    end_time = busy_period['end'].time()
                else:
                    end_time = datetime.max.time()
                
                day_busy_times.append({
                    'start': start_time,
                    'end': end_time
                })
        
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
            available_ranges = _subtract_busy_times_from_ranges(existing_time_ranges, day_busy_times)
            
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
            # User didn't have availability set - preserve their choice (don't add availability)
            # Only copy existing data if it exists, otherwise leave the day unchanged
            if existing_day_data:
                availability_data[day_name] = existing_day_data
            else:
                # No existing data - keep as not available (don't auto-add weekday availability)
                availability_data[day_name] = {
                    'available': False,
                    'start': '09:00',
                    'end': '17:00',
                    'time_ranges': [],
                    'all_day': False
                }
    
    return availability_data

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
        
        # Convert back to time ranges and filter out short periods
        for start_min, end_min in current_ranges:
            duration_minutes = end_min - start_min
            if duration_minutes >= 60:  # At least 1 hour
                available_ranges.append({
                    'start': minutes_to_time_str(start_min),
                    'end': minutes_to_time_str(end_min)
                })
    
    return available_ranges


@bp.route('/availability/save-default', methods=['POST'])
@login_required
def save_default_schedule():
    """Save current week's availability as default schedule"""
    try:
        data = request.get_json()
        week_offset = data.get('week_offset', 0)
        availability_data = data.get('availability_data')
        
        # If availability_data is provided in the request, use it directly
        if availability_data:
            logger.info(f"Using availability data from request for user {current_user.id}")
            schedule_data = availability_data
        else:
            # Fallback: Get the current week's availability from database
            today = datetime.now().date()
            week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
            availability = Availability.get_or_create_availability(current_user.id, week_start)
            
            if not availability.availability_data:
                return jsonify({'success': False, 'error': 'No availability data found for this week'}), 400
            
            schedule_data = availability.get_availability_data()
        
        # Deactivate any existing default schedules
        existing_defaults = DefaultSchedule.query.filter_by(user_id=current_user.id, is_active=True).all()
        for existing in existing_defaults:
            existing.is_active = False
        
        # Create new default schedule
        default_schedule = DefaultSchedule(
            user_id=current_user.id,
            schedule_name='Default Schedule',
            is_active=True
        )
        default_schedule.set_schedule_data(schedule_data)
        
        db.session.add(default_schedule)
        db.session.commit()
        
        # Apply default schedule to all future weeks (next 52 weeks - full year)
        logger.info(f"Starting batch application of default schedule for user {current_user.id}")
        _apply_default_to_future_weeks(current_user.id, default_schedule, max_weeks=52)
        logger.info(f"Completed batch application of default schedule for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Default schedule saved and applied to the entire year!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving default schedule for user {current_user.id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/availability/has-default')
@login_required
def has_default_schedule():
    """Check if user has a default schedule"""
    default_schedule = DefaultSchedule.get_active_default(current_user.id)
    return jsonify({
        'has_default': default_schedule is not None,
        'schedule_name': default_schedule.schedule_name if default_schedule else None,
        'created_at': default_schedule.created_at.isoformat() if default_schedule else None
    })


def _apply_default_to_future_weeks(user_id, default_schedule, max_weeks=52):
    """Helper function to apply default schedule to all future weeks"""
    try:
        today = datetime.now().date()
        applied_count = 0
        updated_count = 0
        
        for week_offset in range(0, max_weeks + 1):  # Start from week 0 (current week)
            week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
            
            # Get or create availability for this week
            existing_availability = Availability.query.filter_by(
                user_id=user_id,
                week_start_date=week_start
            ).first()
            
            if existing_availability:
                # Update existing availability with new default schedule
                existing_availability.set_availability_data(default_schedule.get_schedule_data())
                existing_availability.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new availability with default schedule
                new_availability = Availability(
                    user_id=user_id,
                    week_start_date=week_start
                )
                new_availability.set_availability_data(default_schedule.get_schedule_data())
                db.session.add(new_availability)
                applied_count += 1
        
        db.session.commit()
        logger.info(f"Applied default schedule to {applied_count} new weeks and updated {updated_count} existing weeks for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error applying default schedule to future weeks for user {user_id}: {str(e)}")
        db.session.rollback()
