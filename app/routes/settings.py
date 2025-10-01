from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from app import db
from app.models.google_calendar_sync import GoogleCalendarSync
from app.models.user import User
from app.models.friend import Friend
from app.models.group import Group, GroupMembership
from app.models.activity import Activity
from app.models.availability import Availability
from app.models.event import Event
from app.models.event_invitation import EventInvitation

bp = Blueprint('settings', __name__)

@bp.route('/settings')
@login_required
def index():
    """Settings page with profile information and account settings"""
    # Load Google Calendar sync data explicitly
    google_sync = GoogleCalendarSync.query.filter_by(user_id=current_user.id).first()
    
    # Load Outlook Calendar sync data explicitly
    from app.models.outlook_calendar_sync import OutlookCalendarSync
    outlook_sync = OutlookCalendarSync.query.filter_by(user_id=current_user.id).first()
    
    return render_template('settings/index.html', user=current_user, google_calendar_sync=google_sync, outlook_calendar_sync=outlook_sync)

@bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update user settings"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Update SMS notifications preference
        sms_notifications = data.get('sms_notifications') == 'true' or data.get('sms_notifications') == True
        current_user.sms_notifications = sms_notifications
        
        # Update other profile fields if provided
        if 'first_name' in data:
            current_user.first_name = data.get('first_name', '').strip()
        if 'last_name' in data:
            current_user.last_name = data.get('last_name', '').strip()
        if 'phone' in data:
            current_user.phone = data.get('phone', '').strip()
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Settings updated successfully'})
        else:
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings.index'))
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        else:
            flash('Error updating settings. Please try again.', 'error')
            return redirect(url_for('settings.index'))

@bp.route('/settings/google-calendar', methods=['POST'])
@login_required
def update_google_calendar_settings():
    """Update Google Calendar sync settings"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Get or create GoogleCalendarSync record
        sync_record = GoogleCalendarSync.query.filter_by(user_id=current_user.id).first()
        if not sync_record:
            return jsonify({'success': False, 'error': 'Google Calendar not connected'}), 400
        
        # Update settings
        if 'auto_sync_availability' in data:
            sync_record.auto_sync_availability = data.get('auto_sync_availability') == 'true' or data.get('auto_sync_availability') == True
        
        if 'auto_add_events' in data:
            sync_record.auto_add_events = data.get('auto_add_events') == 'true' or data.get('auto_add_events') == True
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Google Calendar settings updated successfully'})
        else:
            flash('Google Calendar settings updated successfully!', 'success')
            return redirect(url_for('settings.index'))
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('Error updating Google Calendar settings. Please try again.', 'error')
            return redirect(url_for('settings.index'))

@bp.route('/settings/outlook-calendar', methods=['POST'])
@login_required
def update_outlook_calendar_settings():
    """Update Outlook Calendar sync settings"""
    try:
        from app.models.outlook_calendar_sync import OutlookCalendarSync
        
        data = request.get_json() if request.is_json else request.form
        
        # Get or create OutlookCalendarSync record
        sync_record = OutlookCalendarSync.query.filter_by(user_id=current_user.id).first()
        if not sync_record:
            return jsonify({'success': False, 'error': 'Outlook Calendar not connected'}), 400
        
        # Update settings
        if 'auto_sync_availability' in data:
            sync_record.auto_sync_availability = data.get('auto_sync_availability') == 'true' or data.get('auto_sync_availability') == True
        
        if 'auto_add_events' in data:
            sync_record.auto_add_events = data.get('auto_add_events') == 'true' or data.get('auto_add_events') == True
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Outlook Calendar settings updated successfully'})
        else:
            flash('Outlook Calendar settings updated successfully!', 'success')
            return redirect(url_for('settings.index'))
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('Error updating Outlook Calendar settings. Please try again.', 'error')
            return redirect(url_for('settings.index'))

@bp.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            error_msg = 'All fields are required.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Check current password
        if not current_user.check_password(current_password):
            error_msg = 'Current password is incorrect.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Validate new password
        if len(new_password) < 6:
            error_msg = 'New password must be at least 6 characters long.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Check password confirmation
        if new_password != confirm_password:
            error_msg = 'New passwords do not match.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Check if new password is different from current
        if current_user.check_password(new_password):
            error_msg = 'New password must be different from your current password.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        success_msg = 'Password changed successfully!'
        if request.is_json:
            return jsonify({'success': True, 'message': success_msg})
        else:
            flash(success_msg, 'success')
            return redirect(url_for('settings.index'))
            
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error changing password: {str(e)}'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash('Error changing password. Please try again.', 'error')
            return redirect(url_for('settings.index'))

@bp.route('/settings/edit-profile', methods=['POST'])
@login_required
def edit_profile():
    """Edit user profile information"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validation
        if not first_name or not last_name:
            error_msg = 'First name and last name are required.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        if not email:
            error_msg = 'Email is required.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            error_msg = 'This email is already registered to another account.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('settings.index'))
        
        # Check if phone is already taken by another user (if provided)
        if phone:
            existing_user_phone = User.query.filter(User.phone == phone, User.id != current_user.id).first()
            if existing_user_phone:
                error_msg = 'This phone number is already registered to another account.'
                if request.is_json:
                    return jsonify({'success': False, 'error': error_msg}), 400
                else:
                    flash(error_msg, 'error')
                    return redirect(url_for('settings.index'))
        
        # Update profile information
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email
        current_user.phone = phone if phone else None
        
        db.session.commit()
        
        success_msg = 'Profile updated successfully!'
        if request.is_json:
            return jsonify({'success': True, 'message': success_msg})
        else:
            flash(success_msg, 'success')
            return redirect(url_for('settings.index'))
            
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error updating profile: {str(e)}'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash('Error updating profile. Please try again.', 'error')
            return redirect(url_for('settings.index'))

@bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    try:
        user_id = current_user.id
        
        # Delete user's data in the correct order to avoid foreign key constraints
        
        # 1. Delete event invitations where user is invited
        EventInvitation.query.filter_by(invitee_id=user_id).delete()
        
        # 2. Remove user from all events they're attending (many-to-many relationship)
        user = current_user
        for event in user.events:
            event.attendees.remove(user)
        
        # 3. Delete events created by the user (now safe since user is no longer an attendee)
        Event.query.filter_by(created_by_id=user_id).delete()
        
        # 4. Delete activities suggested by the user
        Activity.query.filter_by(suggested_by_id=user_id).delete()
        
        # 5. Delete user's availability records
        Availability.query.filter_by(user_id=user_id).delete()
        
        # 6. Delete user's default schedules
        from app.models.default_schedule import DefaultSchedule
        DefaultSchedule.query.filter_by(user_id=user_id).delete()
        
        # 7. Delete group memberships for groups created by the user (all members)
        groups_created_by_user = Group.query.filter_by(created_by_id=user_id).all()
        for group in groups_created_by_user:
            GroupMembership.query.filter_by(group_id=group.id).delete()
        
        # 8. Delete the user's own group memberships in other groups
        GroupMembership.query.filter_by(user_id=user_id).delete()
        
        # 9. Delete groups created by the user (activities should cascade)
        Group.query.filter_by(created_by_id=user_id).delete()
        
        # 10. Delete friendships (both as requester and receiver)
        Friend.query.filter(
            (Friend.user_id == user_id) | 
            (Friend.friend_id == user_id)
        ).delete()
        
        # 11. Delete Google Calendar sync data
        GoogleCalendarSync.query.filter_by(user_id=user_id).delete()
        
        # 12. Finally, delete the user account
        db.session.delete(current_user)
        
        # Commit all deletions
        db.session.commit()
        
        # Log out the user
        logout_user()
        
        return jsonify({
            'success': True, 
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Failed to delete account: {str(e)}'
        }), 500

@bp.route('/settings/debug-user', methods=['GET'])
@login_required
def debug_user():
    """Debug endpoint to show current user info and calendar sync status"""
    try:
        from app.models.google_calendar_sync import GoogleCalendarSync
        from app.models.outlook_calendar_sync import OutlookCalendarSync
        from app.models.availability import Availability
        from datetime import datetime, timedelta
        
        # Get user info
        user_info = {
            'user_id': current_user.id,
            'email': current_user.email,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
            'google_calendar_enabled': getattr(current_user, 'google_calendar_enabled', False),
            'outlook_calendar_enabled': getattr(current_user, 'outlook_calendar_enabled', False)
        }
        
        # Get Google sync info
        google_sync = GoogleCalendarSync.query.filter_by(user_id=current_user.id).first()
        google_info = None
        if google_sync:
            google_info = {
                'sync_enabled': google_sync.sync_enabled,
                'auto_sync_availability': google_sync.auto_sync_availability,
                'auto_add_events': google_sync.auto_add_events,
                'last_sync': google_sync.last_sync.isoformat() if google_sync.last_sync else None
            }
        
        # Get Outlook sync info
        outlook_sync = OutlookCalendarSync.query.filter_by(user_id=current_user.id).first()
        outlook_info = None
        if outlook_sync:
            outlook_info = {
                'sync_enabled': outlook_sync.sync_enabled,
                'auto_sync_availability': outlook_sync.auto_sync_availability,
                'auto_add_events': outlook_sync.auto_add_events,
                'last_sync': outlook_sync.last_sync.isoformat() if outlook_sync.last_sync else None,
                'token_expires_at': outlook_sync.token_expires_at.isoformat() if outlook_sync.token_expires_at else None
            }
        
        # Get recent availability records
        recent_availability = Availability.query.filter_by(user_id=current_user.id).order_by(Availability.updated_at.desc()).limit(5).all()
        availability_info = []
        for avail in recent_availability:
            monday_data = avail.get_day_availability('monday')
            availability_info.append({
                'week_start': avail.week_start_date.isoformat(),
                'updated_at': avail.updated_at.isoformat() if avail.updated_at else None,
                'monday_available': monday_data.get('available', False),
                'monday_time_ranges': monday_data.get('time_ranges', [])
            })
        
        debug_data = {
            'user': user_info,
            'google_sync': google_info,
            'outlook_sync': outlook_info,
            'recent_availability': availability_info
        }
        
        return jsonify(debug_data)
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500
