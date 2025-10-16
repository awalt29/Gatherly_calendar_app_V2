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
    # Ensure the is_admin field exists and handle None values
    try:
        admin_value = current_user.is_admin
        # Handle None values - treat as False and fall back to user ID check
        if admin_value is None:
            return current_user.id == 1
        return admin_value
    except AttributeError:
        # If is_admin field doesn't exist, fall back to user ID check
        return current_user.id == 1

@bp.route('/debug')
@login_required
def debug():
    """Debug admin status"""
    try:
        user_info = {
            'user_id': current_user.id,
            'email': current_user.email,
            'username': getattr(current_user, 'username', 'None'),
            'has_is_admin_field': hasattr(current_user, 'is_admin'),
            'is_admin_value': getattr(current_user, 'is_admin', 'Field not found'),
            'fallback_check': current_user.id == 1,
            'is_admin_function_result': is_admin()
        }
        return f"<h1>Admin Debug</h1><pre>{user_info}</pre>"
    except Exception as e:
        return f"<h1>Debug Error</h1><p>{str(e)}</p>"

@bp.route('/dashboard')
def dashboard():
    """Public dashboard showing all users"""
    # Removed admin check - now accessible to anyone
    
    try:
        # Get all users - simplified version
        users = User.query.all()
        
        # Simple user stats without complex queries
        user_stats = []
        for user in users:
            try:
                # Safe counting with error handling
                friend_count = 0
                availability_count = 0
                has_google_calendar = False
                has_default_schedule = False
                
                try:
                    friend_count = Friend.query.filter(
                        (Friend.user_id == user.id) | (Friend.friend_id == user.id),
                        Friend.status == 'accepted'
                    ).count()
                except:
                    pass
                
                try:
                    availability_count = Availability.query.filter_by(user_id=user.id).count()
                except:
                    pass
                
                try:
                    google_sync = GoogleCalendarSync.query.filter_by(user_id=user.id).first()
                    has_google_calendar = bool(google_sync and google_sync.access_token)
                except:
                    pass
                
                try:
                    has_default_schedule = bool(DefaultSchedule.query.filter_by(user_id=user.id).first())
                except:
                    pass
                
                # Check if user has is_admin field
                is_user_admin = False
                try:
                    is_user_admin = getattr(user, 'is_admin', False)
                except:
                    is_user_admin = (user.id == 1)
                
                user_stats.append({
                    'user': user,
                    'friend_count': friend_count,
                    'availability_count': availability_count,
                    'has_google_calendar': has_google_calendar,
                    'has_default_schedule': has_default_schedule,
                    'is_admin': is_user_admin
                })
            except Exception as user_error:
                logger.error(f"Error processing user {user.id}: {str(user_error)}")
                # Add user with minimal data
                user_stats.append({
                    'user': user,
                    'friend_count': 0,
                    'availability_count': 0,
                    'has_google_calendar': False,
                    'has_default_schedule': False,
                    'is_admin': (user.id == 1)
                })
        
        # Sort by user ID
        user_stats.sort(key=lambda x: x['user'].id)
        
        return render_template('admin/dashboard.html', 
                             user_stats=user_stats,
                             total_users=len(users))
    
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        return f"<h1>Admin Dashboard</h1><p>Error: {str(e)}</p><p>Users found: {len(User.query.all()) if User.query else 'N/A'}</p>", 500

@bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user and all their data"""
    # Removed admin check - any logged-in user can delete users
    
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    try:
        user = User.query.get_or_404(user_id)
        username = user.username
        
        # Delete all user-related data in correct order to avoid foreign key violations
        
        # 1. Delete notifications related to this user
        from app.models.notification import Notification
        Notification.query.filter_by(user_id=user_id).delete()
        Notification.query.filter_by(from_user_id=user_id).delete()
        
        # 2. Delete notifications related to friendships involving this user
        friend_ids = db.session.query(Friend.id).filter(
            (Friend.user_id == user_id) | (Friend.friend_id == user_id)
        ).all()
        for friend_record in friend_ids:
            Notification.query.filter_by(friend_id=friend_record[0]).delete()
        
        # 3. Delete event invitations
        from app.models.event_invitation import EventInvitation
        EventInvitation.query.filter_by(invitee_id=user_id).delete()
        
        # 4. Delete events created by this user and their invitations
        from app.models.event import Event
        user_events = Event.query.filter_by(created_by_id=user_id).all()
        for event in user_events:
            EventInvitation.query.filter_by(event_id=event.id).delete()
            db.session.delete(event)
        
        # 5. Remove user from events they're attending (but didn't create)
        events_attending = Event.query.filter(Event.attendees.any(id=user_id)).all()
        for event in events_attending:
            event.attendees.remove(user)
        
        # 6. Delete friendships
        Friend.query.filter(
            (Friend.user_id == user_id) | (Friend.friend_id == user_id)
        ).delete()
        
        # 7. Delete availability records
        Availability.query.filter_by(user_id=user_id).delete()
        
        # 8. Delete default schedule
        DefaultSchedule.query.filter_by(user_id=user_id).delete()
        
        # 9. Delete Google Calendar sync
        GoogleCalendarSync.query.filter_by(user_id=user_id).delete()
        
        # 10. Delete Outlook Calendar sync
        from app.models.outlook_calendar_sync import OutlookCalendarSync
        OutlookCalendarSync.query.filter_by(user_id=user_id).delete()
        
        # 11. Handle groups created by this user and group memberships
        from app.models.group import Group, GroupMembership
        
        # Delete groups created by this user
        user_groups = Group.query.filter_by(created_by_id=user_id).all()
        for group in user_groups:
            # Delete all memberships for this group first
            GroupMembership.query.filter_by(group_id=group.id).delete()
            # Then delete the group
            db.session.delete(group)
        
        # Remove user from groups they're a member of
        GroupMembership.query.filter_by(user_id=user_id).delete()
        
        # 12. Finally, delete the user
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
def user_details(user_id):
    """Get detailed information about a specific user"""
    # Removed admin check - now accessible to anyone
    
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
    # Removed admin check - any logged-in user can toggle admin status
    
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
def sms_status():
    """Check SMS service configuration status"""
    return jsonify({
        'configured': sms_service.is_configured(),
        'user_phone': 'N/A (public access)',
        'user_sms_enabled': 'N/A (public access)'
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
def google_calendar_status():
    """Check Google Calendar service configuration status"""
    return jsonify({
        'configured': google_calendar_service.is_configured(),
        'user_connected': 'N/A (public access)'
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
