from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def index():
    """Notifications page (if we want a dedicated page later)"""
    return render_template('notifications/index.html')

@bp.route('/api/list')
@login_required
def api_list():
    """Get all notifications for the current user"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Notification.created_at.desc()
        ).limit(50).all()  # Limit to 50 most recent
        
        return jsonify({
            'success': True,
            'notifications': [notification.to_dict() for notification in notifications]
        })
    except Exception as e:
        logger.error(f"Error fetching notifications for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch notifications'
        }), 500

@bp.route('/api/count')
@login_required
def api_count():
    """Get unread notification count for the current user"""
    try:
        unread_count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'count': unread_count
        })
    except Exception as e:
        logger.error(f"Error getting notification count for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get notification count'
        }), 500

@bp.route('/api/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def api_mark_read(notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark notification as read'
        }), 500

@bp.route('/api/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_read():
    """Mark all notifications as read for the current user"""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        })
    except Exception as e:
        logger.error(f"Error marking all notifications as read for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark notifications as read'
        }), 500

@bp.route('/api/delete/<int:notification_id>', methods=['DELETE'])
@login_required
def api_delete(notification_id):
    """Delete a specific notification"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted'
        })
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete notification'
        }), 500

@bp.route('/api/clear-all', methods=['DELETE'])
@login_required
def api_clear_all():
    """Delete all notifications for the current user"""
    try:
        Notification.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All notifications cleared'
        })
    except Exception as e:
        logger.error(f"Error clearing all notifications for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear notifications'
        }), 500
