from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.activity import Activity
from app.models.group import Group
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('activities', __name__, url_prefix='/activities')

@bp.route('/group/<int:group_id>', methods=['GET'])
@login_required
def get_group_activities(group_id):
    """Get all activities for a group"""
    try:
        # Check if user is a member of the group
        group = Group.query.get_or_404(group_id)
        if not group.is_member(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get activities ordered by creation date
        activities = Activity.query.filter_by(group_id=group_id).order_by(
            Activity.order_index.asc(),
            Activity.created_at.asc()
        ).all()
        
        # Convert to dict and add permissions
        activities_data = []
        for activity in activities:
            activity_dict = activity.to_dict()
            # User can delete their own activities
            activity_dict['can_delete'] = (activity.suggested_by_id == current_user.id)
            # Only group creator can mark as complete
            activity_dict['can_complete'] = (group.created_by_id == current_user.id)
            activities_data.append(activity_dict)
        
        return jsonify({
            'success': True,
            'activities': activities_data
        })
        
    except Exception as e:
        logger.error(f"Error getting activities for group {group_id}: {str(e)}")
        return jsonify({'error': 'Failed to load activities'}), 500

@bp.route('/group/<int:group_id>', methods=['POST'])
@login_required
def add_activity(group_id):
    """Add a new activity to a group"""
    try:
        # Check if user is a member of the group
        group = Group.query.get_or_404(group_id)
        if not group.is_member(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        venue = data.get('venue', '').strip()
        
        if not venue:
            return jsonify({'error': 'Venue name is required'}), 400
        
        if len(venue) > 200:
            return jsonify({'error': 'Venue name must be 200 characters or less'}), 400
        
        # Create new activity
        activity = Activity(
            group_id=group_id,
            venue=venue,
            suggested_by_id=current_user.id,
            status='pending'
        )
        
        db.session.add(activity)
        db.session.commit()
        
        # Return the created activity with permissions
        activity_dict = activity.to_dict()
        activity_dict['can_delete'] = True  # User can delete their own
        activity_dict['can_complete'] = (group.created_by_id == current_user.id)
        
        logger.info(f"User {current_user.id} added activity '{venue}' to group {group_id}")
        
        return jsonify({
            'success': True,
            'message': f'Added "{venue}" to the activity queue',
            'activity': activity_dict
        })
        
    except Exception as e:
        logger.error(f"Error adding activity to group {group_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add activity'}), 500

@bp.route('/<int:activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    """Delete an activity (only by the user who suggested it)"""
    try:
        activity = Activity.query.get_or_404(activity_id)
        
        # Check if user is the one who suggested this activity
        if activity.suggested_by_id != current_user.id:
            return jsonify({'error': 'You can only delete activities you suggested'}), 403
        
        # Check if user is still a member of the group
        group = Group.query.get(activity.group_id)
        if not group or not group.is_member(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        venue_name = activity.venue
        db.session.delete(activity)
        db.session.commit()
        
        logger.info(f"User {current_user.id} deleted activity '{venue_name}' from group {activity.group_id}")
        
        return jsonify({
            'success': True,
            'message': f'Removed "{venue_name}" from the activity queue'
        })
        
    except Exception as e:
        logger.error(f"Error deleting activity {activity_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete activity'}), 500

@bp.route('/<int:activity_id>/complete', methods=['PUT'])
@login_required
def mark_activity_complete(activity_id):
    """Mark an activity as complete (only by group creator)"""
    try:
        activity = Activity.query.get_or_404(activity_id)
        group = Group.query.get(activity.group_id)
        
        # Check if user is the group creator
        if group.created_by_id != current_user.id:
            return jsonify({'error': 'Only the group creator can mark activities as complete'}), 403
        
        # Check if user is still a member of the group
        if not group.is_member(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Toggle completion status
        new_status = 'completed' if activity.status == 'pending' else 'pending'
        activity.status = new_status
        db.session.commit()
        
        action = 'marked as complete' if new_status == 'completed' else 'marked as pending'
        logger.info(f"User {current_user.id} {action} activity '{activity.venue}' in group {activity.group_id}")
        
        return jsonify({
            'success': True,
            'message': f'"{activity.venue}" {action}',
            'status': new_status
        })
        
    except Exception as e:
        logger.error(f"Error updating activity {activity_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update activity'}), 500
