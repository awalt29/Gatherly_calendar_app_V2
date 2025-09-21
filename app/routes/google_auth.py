from flask import Blueprint, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app.services.google_calendar_service import google_calendar_service
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('google_auth', __name__, url_prefix='/auth/google')

@bp.route('/connect')
@login_required
def connect():
    """Initiate Google Calendar connection"""
    try:
        if not google_calendar_service.is_configured():
            flash('Google Calendar integration is not configured', 'error')
            return redirect(url_for('settings.index'))
        
        # Store user ID in session for callback
        session['google_auth_user_id'] = current_user.id
        
        # Generate authorization URL
        auth_url = google_calendar_service.get_authorization_url(
            state=str(current_user.id)
        )
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Google auth for user {current_user.id}: {str(e)}")
        flash('Error connecting to Google Calendar. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@bp.route('/callback')
def callback():
    """Handle Google OAuth callback"""
    try:
        # Get authorization code from callback
        authorization_code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Google OAuth error: {error}")
            flash('Google Calendar connection was cancelled or failed.', 'error')
            return redirect(url_for('settings.index'))
        
        if not authorization_code:
            flash('No authorization code received from Google.', 'error')
            return redirect(url_for('settings.index'))
        
        # Get user ID from session or state
        user_id = session.get('google_auth_user_id')
        if not user_id and state:
            try:
                user_id = int(state)
            except ValueError:
                pass
        
        if not user_id:
            flash('Invalid authentication session. Please try again.', 'error')
            return redirect(url_for('settings.index'))
        
        # Handle the OAuth callback
        success = google_calendar_service.handle_oauth_callback(
            authorization_code, 
            user_id
        )
        
        # Clear session
        session.pop('google_auth_user_id', None)
        
        if success:
            flash('Google Calendar connected successfully!', 'success')
        else:
            flash('Failed to connect Google Calendar. Please try again.', 'error')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}")
        flash('Error connecting Google Calendar. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect Google Calendar"""
    try:
        success = google_calendar_service.disconnect_calendar(current_user.id)
        
        if success:
            if request.is_json:
                return jsonify({'success': True, 'message': 'Google Calendar disconnected successfully'})
            else:
                flash('Google Calendar disconnected successfully', 'success')
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Failed to disconnect Google Calendar'}), 500
            else:
                flash('Failed to disconnect Google Calendar. Please try again.', 'error')
        
    except Exception as e:
        logger.error(f"Error disconnecting Google Calendar for user {current_user.id}: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('Error disconnecting Google Calendar. Please try again.', 'error')
    
    if request.is_json:
        return jsonify({'success': True})
    else:
        return redirect(url_for('settings.index'))

@bp.route('/status')
@login_required
def status():
    """Get Google Calendar connection status"""
    try:
        return jsonify({
            'configured': google_calendar_service.is_configured(),
            'connected': current_user.google_calendar_enabled,
            'user_id': current_user.id
        })
    except Exception as e:
        logger.error(f"Error getting Google Calendar status for user {current_user.id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
