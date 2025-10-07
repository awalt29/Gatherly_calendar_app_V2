from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.availability import Availability
from app.models.friend import Friend
from app.models.default_schedule import DefaultSchedule
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('calendar', __name__)

@bp.route('/')
@login_required
def index():
    """Main calendar page showing scrollable Apple Calendar-style view"""
    return render_template('calendar/scrollable.html')

# Removed old calendar route and week API - only using scrollable calendar

@bp.route('/day/<date>')
@login_required
def day_detail(date):
    """Detailed view for a specific day"""
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        week_start = Availability.get_week_start(date_obj)
        day_name = date_obj.strftime('%A').lower()
        
        # Get current user's friends
        friends = current_user.get_friends()
        friend_ids = [friend.id for friend in friends]
        friend_ids.append(current_user.id)
        
        # Get availability data for this week
        availabilities = Availability.query.filter(
            Availability.user_id.in_(friend_ids),
            Availability.week_start_date == week_start
        ).all()
        
        # Get users available on this day
        available_users = []
        for friend in friends + [current_user]:
            user_availability = next(
                (av for av in availabilities if av.user_id == friend.id), 
                None
            )
            
            if user_availability and user_availability.is_available_on_day(day_name):
                # Get time ranges converted to the viewing user's timezone for display
                viewer_timezone = current_user.timezone if current_user.timezone else None
                time_ranges = user_availability.get_time_ranges(day_name, viewer_timezone)
                
                available_users.append({
                    'user': friend,
                    'time_ranges': time_ranges,
                    'user_timezone': getattr(friend, 'timezone', None)
                })
        
        return render_template('calendar/day_detail.html', 
                             date=date_obj,
                             available_users=available_users,
                             user_timezone=current_user.timezone)
    
    except ValueError:
        return "Invalid date format", 400

@bp.route('/api/months/<month_offset>')
@login_required
def get_month_data(month_offset):
    """API endpoint to get calendar data for 2-week chunks"""
    try:
        # Convert month_offset to int and validate
        try:
            chunk_offset = int(month_offset)
        except ValueError:
            return jsonify({'error': 'Invalid chunk offset'}), 400
            
        # Calculate the start date for this 2-week chunk
        today = datetime.now().date()
        week_start_today = Availability.get_week_start(today)
        
        # Each chunk is 2 weeks (14 days)
        chunk_start = week_start_today + timedelta(weeks=chunk_offset * 2)
        chunk_end = chunk_start + timedelta(days=13)  # 2 weeks - 1 day
        
        # Get current user's friends
        friends = current_user.get_friends()
        friend_ids = [friend.id for friend in friends]
        friend_ids.append(current_user.id)  # Include current user
        
        # Get the 2 weeks for this chunk
        weeks = []
        for week_num in range(2):
            week_start = chunk_start + timedelta(weeks=week_num)
            weeks.append({
                'week_start': week_start,
                'week_start_str': week_start.strftime('%Y-%m-%d')
            })
        
        # Get availability data for both weeks
        week_starts = [w['week_start'] for w in weeks]
        availabilities = Availability.query.filter(
            Availability.user_id.in_(friend_ids),
            Availability.week_start_date.in_(week_starts)
        ).all()
        
        # Organize data by weeks
        chunk_data = {
            'chunk_start': chunk_start.strftime('%Y-%m-%d'),
            'chunk_name': f"{chunk_start.strftime('%b %d')} - {chunk_end.strftime('%b %d, %Y')}",
            'weeks': []
        }
        
        for week in weeks:
            week_start = week['week_start']
            week_data = {
                'week_start': week_start.strftime('%Y-%m-%d'),
                'days': []
            }
            
            # Generate 7 days of the week, starting with Sunday (US calendar format)
            # Backend week_start is Monday, so Sunday is -1 day, then Mon-Sat are 0-5
            for day_offset in [-1, 0, 1, 2, 3, 4, 5]:  # Sunday first, then Mon-Sat
                current_date = week_start + timedelta(days=day_offset)
                day_name = current_date.strftime('%A').lower()
                
                day_data = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': day_name,
                    'day_short': current_date.strftime('%a').upper(),
                    'day_number': current_date.day,
                    'is_today': current_date == today,
                    'is_current_month': True,  # All dates are relevant in 2-week chunks
                    'users': []
                }
                
                # Create a consistent color mapping for this group of friends
                # Sort friends by ID to ensure consistent color assignment
                all_users = sorted(friends + [current_user], key=lambda x: x.id)
                user_color_map = {}
                for i, user in enumerate(all_users):
                    user_color_map[user.id] = i % 8  # 8 available colors
                
                # Add availability for each friend
                for friend in friends + [current_user]:
                    user_availability = next(
                        (av for av in availabilities if av.user_id == friend.id and av.week_start_date == week_start), 
                        None
                    )
                    
                    if user_availability and user_availability.is_available_on_day(day_name):
                        time_range = user_availability.get_time_range(day_name)
                        day_data['users'].append({
                            'id': friend.id,
                            'name': friend.get_full_name(),
                            'initials': friend.get_initials(),
                            'is_current_user': friend.id == current_user.id,
                            'time_range': time_range,
                            'color_index': user_color_map[friend.id]
                        })
                
                week_data['days'].append(day_data)
            
            chunk_data['weeks'].append(week_data)
        
        return jsonify(chunk_data)
    
    except Exception as e:
        logger.error(f"Error loading chunk data: {str(e)}")
        return jsonify({'error': str(e)}), 500
