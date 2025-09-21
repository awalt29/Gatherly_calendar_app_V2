"""
Admin routes for testing and management
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.tasks.sms_scheduler import sms_scheduler
from app.services.sms_service import sms_service
# Group availability service temporarily disabled
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')

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
