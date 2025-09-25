"""
Admin routes for testing and management
"""
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.tasks.sms_scheduler import sms_scheduler
from app.services.sms_service import sms_service
from app.tasks.google_calendar_scheduler import google_calendar_scheduler
from app.services.google_calendar_service import google_calendar_service
from app.models.user import User
from app.models.friend import Friend
from app.models.availability import Availability
from app.models.default_schedule import DefaultSchedule
from app.models.google_calendar_sync import GoogleCalendarSync
from app import db
# Group availability service temporarily disabled
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    """Check if current user is admin"""
    # Ensure the is_admin field exists
    try:
        return current_user.is_admin
    except AttributeError:
        # If is_admin field doesn't exist, fall back to user ID check
        return current_user.id == 1

@bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard showing all users"""
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Get all users with related data
        users = User.query.all()
        
        # Get user stats
        user_stats = []
        for user in users:
            # Count friendships
            friend_count = Friend.query.filter(
                (Friend.user_id == user.id) | (Friend.friend_id == user.id),
                Friend.status == 'accepted'
            ).count()
            
            # Count availability records
            availability_count = Availability.query.filter_by(user_id=user.id).count()
            
            # Check Google Calendar connection
            google_sync = GoogleCalendarSync.query.filter_by(user_id=user.id).first()
            has_google_calendar = bool(google_sync and google_sync.access_token)
            
            # Check if user has default schedule
            has_default_schedule = bool(DefaultSchedule.query.filter_by(user_id=user.id).first())
            
            user_stats.append({
                'user': user,
                'friend_count': friend_count,
                'availability_count': availability_count,
                'has_google_calendar': has_google_calendar,
                'has_default_schedule': has_default_schedule,
                'last_login': user.last_login or 'Never'
            })
        
        # Sort by most recent activity
        user_stats.sort(key=lambda x: x['user'].created_at or datetime.min, reverse=True)
        
        return render_template('admin/dashboard.html', 
                             user_stats=user_stats,
                             total_users=len(users))
    
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('main.index'))

@bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user and all their data"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    try:
        user = User.query.get_or_404(user_id)
        username = user.username
        
        # Delete all user-related data
        # 1. Delete friendships
        Friend.query.filter(
            (Friend.user_id == user_id) | (Friend.friend_id == user_id)
        ).delete()
        
        # 2. Delete availability records
        Availability.query.filter_by(user_id=user_id).delete()
        
        # 3. Delete default schedule
        DefaultSchedule.query.filter_by(user_id=user_id).delete()
        
        # 4. Delete Google Calendar sync
        GoogleCalendarSync.query.filter_by(user_id=user_id).delete()
        
        # 5. Delete the user
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} deleted user {username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': f'User {username} and all associated data deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

@bp.route('/user-details/<int:user_id>')
@login_required
def user_details(user_id):
    """Get detailed information about a specific user"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Get friendships
        friendships = db.session.query(Friend, User).join(
            User, 
            (User.id == Friend.friend_id) if Friend.user_id == user_id else (User.id == Friend.user_id)
        ).filter(
            (Friend.user_id == user_id) | (Friend.friend_id == user_id)
        ).all()
        
        # Get recent availability
        recent_availability = Availability.query.filter_by(user_id=user_id).order_by(
            Availability.date.desc()
        ).limit(5).all()
        
        # Get Google Calendar info
        google_sync = GoogleCalendarSync.query.filter_by(user_id=user_id).first()
        
        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
                'sms_notifications': user.sms_notifications,
                'google_calendar_enabled': user.google_calendar_enabled
            },
            'friendships': [{
                'friend_name': friendship[1].username,
                'friend_email': friendship[1].email,
                'status': friendship[0].status,
                'created_at': friendship[0].created_at.isoformat() if friendship[0].created_at else None
            } for friendship in friendships],
            'recent_availability': [{
                'date': av.date.isoformat(),
                'start_time': av.start_time,
                'end_time': av.end_time
            } for av in recent_availability],
            'google_calendar': {
                'connected': bool(google_sync and google_sync.access_token),
                'auto_sync': google_sync.auto_sync_availability if google_sync else False,
                'last_sync': google_sync.last_sync.isoformat() if google_sync and google_sync.last_sync else None
            } if google_sync else None
        })
        
    except Exception as e:
        logger.error(f"Error getting user details for {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    
    try:
        user = User.query.get_or_404(user_id)
        user.is_admin = not user.is_admin
        db.session.commit()
        
        action = 'granted' if user.is_admin else 'revoked'
        logger.info(f"Admin {current_user.username} {action} admin privileges for user {user.username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'is_admin': user.is_admin,
            'message': f'Admin privileges {action} for {user.username}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling admin status for user {user_id}: {str(e)}")
        return jsonify({'error': f'Failed to update admin status: {str(e)}'}), 500

@bp.route('/test-sms', methods=['POST'])
@login_required
def test_sms():
    """Test SMS functionality by sending a test message to current user"""
    try:
        if not current_user.phone:
            return jsonify({'error': 'No phone number configured for your account'}), 400
        
        success = sms_scheduler.send_test_reminder(current_user.id)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Test SMS sent successfully to {current_user.phone}'
            })
        else:
            return jsonify({'error': 'Failed to send test SMS'}), 500
            
    except Exception as e:
        logger.error(f"Error in test SMS endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/sms-status')
@login_required
def sms_status():
    """Check SMS service configuration status"""
    return jsonify({
        'configured': sms_service.is_configured(),
        'user_phone': current_user.phone,
        'user_sms_enabled': current_user.sms_notifications
    })

@bp.route('/run-weekly-reminders', methods=['POST'])
@login_required
def run_weekly_reminders():
    """Manually trigger weekly SMS reminders (for testing)"""
    try:
        stats = sms_scheduler.send_weekly_availability_reminders()
        return jsonify({
            'success': True,
            'message': 'Weekly reminders sent successfully',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error running weekly reminders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/run-weekend-planning-reminders', methods=['POST'])
@login_required
def run_weekend_planning_reminders():
    """Manually trigger weekend planning SMS reminders (for testing)"""
    try:
        stats = sms_scheduler.send_weekend_planning_reminders()
        return jsonify({
            'success': True,
            'message': 'Weekend planning reminders sent successfully',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error running weekend planning reminders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/test-weekend-planning-sms', methods=['POST'])
@login_required
def test_weekend_planning_sms():
    """Test weekend planning SMS functionality by sending a test message to current user"""
    try:
        if not current_user.phone:
            return jsonify({'error': 'No phone number configured for your account'}), 400
        
        success = sms_service.send_weekend_planning_reminder(current_user)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Test weekend planning SMS sent successfully to {current_user.phone}'
            })
        else:
            return jsonify({'error': 'Failed to send test weekend planning SMS'}), 500
            
    except Exception as e:
        logger.error(f"Error in test weekend planning SMS endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/sync-google-calendar', methods=['POST'])
@login_required
def sync_google_calendar():
    """Manually trigger Google Calendar sync for current user"""
    try:
        success = google_calendar_scheduler.sync_user_now(current_user.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Google Calendar sync completed successfully'
            })
        else:
            return jsonify({'error': 'Failed to sync Google Calendar'}), 500
            
    except Exception as e:
        logger.error(f"Error syncing Google Calendar: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/sync-all-google-calendars', methods=['POST'])
@login_required
def sync_all_google_calendars():
    """Manually trigger Google Calendar sync for all users (admin only)"""
    try:
        stats = google_calendar_scheduler.sync_all_users_availability()
        return jsonify({
            'success': True,
            'message': 'Google Calendar sync completed for all users',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error syncing all Google Calendars: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/google-calendar-status')
@login_required
def google_calendar_status():
    """Check Google Calendar service configuration status"""
    return jsonify({
        'configured': google_calendar_service.is_configured(),
        'user_connected': bool(google_calendar_service.get_credentials(current_user.id))
    })

# @bp.route('/check-group-availability', methods=['POST'])
# @login_required
# def check_group_availability_endpoint():
#     """Manually trigger group availability check (for testing)"""
#     try:
#         alerts_sent = check_group_availability()
#         return jsonify({
#             'success': True,
#             'message': f'Group availability check completed. {alerts_sent} alerts sent.',
#             'alerts_sent': alerts_sent
#         })
#     except Exception as e:
#         logger.error(f"Error checking group availability: {str(e)}")
#         return jsonify({'error': str(e)}), 500
