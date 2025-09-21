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
    """Main calendar page showing 2-week view with friend availability"""
    return render_template('calendar/index.html')

@bp.route('/api/week/<int:week_offset>')
@login_required
def get_week_data(week_offset):
    """API endpoint to get calendar data for a specific week"""
    try:
        # Calculate the week start date
        today = datetime.now().date()
        week_start = Availability.get_week_start(today) + timedelta(weeks=week_offset)
        
        # Get current user's friends
        friends = current_user.get_friends()
        friend_ids = [friend.id for friend in friends]
        friend_ids.append(current_user.id)  # Include current user
        
        # Get availability data for all friends for this week
        availabilities = Availability.query.filter(
            Availability.user_id.in_(friend_ids),
            Availability.week_start_date == week_start
        ).all()
        
        # Organize availability data by user and day
        week_data = {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'days': []
        }
        
        # Generate 7 days of the week
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            day_name = current_date.strftime('%A').lower()
            
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'day_name': day_name,
                'day_short': current_date.strftime('%a').upper(),
                'day_number': current_date.day,
                'is_today': current_date == today,
                'users': []
            }
            
            # Add availability for each friend
            for friend in friends + [current_user]:
                user_availability = next(
                    (av for av in availabilities if av.user_id == friend.id), 
                    None
                )
                
                if user_availability and user_availability.is_available_on_day(day_name):
                    time_range = user_availability.get_time_range(day_name)
                    day_data['users'].append({
                        'id': friend.id,
                        'name': friend.get_full_name(),
                        'initials': friend.get_initials(),
                        'is_current_user': friend.id == current_user.id,
                        'time_range': time_range
                    })
            
            week_data['days'].append(day_data)
        
        return jsonify(week_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                time_range = user_availability.get_time_range(day_name)
                available_users.append({
                    'user': friend,
                    'time_range': time_range
                })
        
        return render_template('calendar/day_detail.html', 
                             date=date_obj,
                             available_users=available_users)
    
    except ValueError:
        return "Invalid date format", 400
