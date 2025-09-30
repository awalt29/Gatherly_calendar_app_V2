from flask import Blueprint, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app.services.outlook_calendar_service import outlook_calendar_service
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('outlook_auth', __name__, url_prefix='/auth/outlook')

@bp.route('/connect')
@login_required
def connect():
    """Initiate Outlook Calendar connection"""
    try:
        if not outlook_calendar_service.is_configured():
            flash('Outlook Calendar integration is not configured', 'error')
            return redirect(url_for('settings.index'))
        
        # Store user ID in session for callback
        session['outlook_auth_user_id'] = current_user.id
        
        # Generate authorization URL
        auth_url = outlook_calendar_service.get_authorization_url(
            state=str(current_user.id)
        )
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Outlook auth for user {current_user.id}: {str(e)}")
        flash('Error connecting to Outlook Calendar. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@bp.route('/callback')
def callback():
    """Handle Outlook OAuth callback"""
    try:
        # Get authorization code from callback
        authorization_code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        if error:
            logger.warning(f"Outlook OAuth error: {error} - {error_description}")
            flash('Outlook Calendar connection was cancelled or failed.', 'error')
            return redirect(url_for('settings.index'))
        
        if not authorization_code:
            flash('No authorization code received from Outlook.', 'error')
            return redirect(url_for('settings.index'))
        
        # Get user ID from session or state
        user_id = session.get('outlook_auth_user_id')
        if not user_id and state:
            try:
                user_id = int(state)
            except ValueError:
                pass
        
        if not user_id:
            flash('Invalid authentication session. Please try again.', 'error')
            return redirect(url_for('settings.index'))
        
        # Handle the OAuth callback
        success = outlook_calendar_service.handle_oauth_callback(
            authorization_code, 
            user_id
        )
        
        # Clear session
        session.pop('outlook_auth_user_id', None)
        
        if success:
            flash('Outlook Calendar connected successfully!', 'success')
        else:
            flash('Failed to connect Outlook Calendar. Please try again.', 'error')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        logger.error(f"Error in Outlook OAuth callback: {str(e)}")
        flash('Error connecting Outlook Calendar. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect Outlook Calendar"""
    try:
        success = outlook_calendar_service.disconnect_user(current_user.id)
        
        if success:
            flash('Outlook Calendar disconnected successfully!', 'success')
        else:
            flash('Error disconnecting Outlook Calendar. Please try again.', 'error')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        logger.error(f"Error disconnecting Outlook Calendar for user {current_user.id}: {str(e)}")
        flash('Error disconnecting Outlook Calendar. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@bp.route('/status')
@login_required
def status():
    """Get Outlook Calendar connection status"""
    try:
        return jsonify({
            'configured': outlook_calendar_service.is_configured(),
            'connected': current_user.outlook_calendar_enabled,
            'user_id': current_user.id
        })
    except Exception as e:
        logger.error(f"Error getting Outlook Calendar status for user {current_user.id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
