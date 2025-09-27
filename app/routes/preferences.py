from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.group import Group, GroupMembership
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('groups', __name__)  # Changed from 'preferences' to 'groups'

@bp.route('/groups')
@login_required
def index():
    """Groups page - manage friend groups and availability alerts"""
    # Get user's created groups (private and shared)
    created_groups = Group.query.filter_by(created_by_id=current_user.id).all()
    
    # Get shared groups user is a member of (includes created and joined)
    member_group_ids = [m.group_id for m in current_user.group_memberships if m.status == 'active']
    shared_groups = Group.query.filter(
        Group.id.in_(member_group_ids),
        Group.group_type == 'shared'
    ).all() if member_group_ids else []
    
    # Get user's friends for adding to groups
    friends = current_user.get_friends()
    
    return render_template('groups/index.html', 
                         created_groups=created_groups,
                         shared_groups=shared_groups,
                         friends=friends)

@bp.route('/groups/create', methods=['POST'])
@login_required
def create_group():
    """Create a new friend group"""
    try:
        data = request.get_json() if request.is_json else request.form
        logger.info(f"Group creation request - is_json: {request.is_json}, data: {data}")
        
        name = data.get('name', '').strip()
        group_type = data.get('group_type', 'private').strip()
        member_ids = data.getlist('member_ids') if hasattr(data, 'getlist') else data.get('member_ids', [])
        
        logger.info(f"Parsed data - name: '{name}', group_type: '{group_type}', member_ids: {member_ids}")
        
        # Validation
        if not name:
            error_msg = 'Group name is required'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('groups.index'))
        
        if len(name) > 100:
            error_msg = 'Group name must be 100 characters or less'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('groups.index'))
        
        # Validate group_type
        if group_type not in ['private', 'shared']:
            group_type = 'private'
        
        # Create the group
        group = Group(
            name=name,
            created_by_id=current_user.id,
            group_type=group_type
        )
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add the creator as a member
        creator_membership = GroupMembership(group_id=group.id, user_id=current_user.id)
        db.session.add(creator_membership)
        
        # Add selected friends as members
        added_members = []
        for member_id in member_ids:
            try:
                member_id = int(member_id)
                # Verify the user is friends with this person
                if current_user.is_friend_with(member_id):
                    membership = GroupMembership(group_id=group.id, user_id=member_id)
                    db.session.add(membership)
                    user = User.query.get(member_id)
                    if user:
                        added_members.append(user.get_full_name())
            except (ValueError, TypeError):
                continue
        
        db.session.commit()
        
        success_msg = f'Group "{name}" created successfully!'
        if added_members:
            success_msg += f' Added members: {", ".join(added_members)}'
        
        logger.info(f'User {current_user.id} created group "{name}" with {len(added_members)} members')
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': success_msg,
                'group': group.to_dict()
            })
        else:
            flash(success_msg, 'success')
            return redirect(url_for('groups.index'))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error creating group: {str(e)}')
        error_msg = 'Error creating group. Please try again.'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('groups.index'))

@bp.route('/groups/<int:group_id>/settings', methods=['POST'])
@login_required
def update_group_settings(group_id):
    """Update group settings (notifications, minimum overlap, etc.)"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Check if user is the creator or a member
        if group.created_by_id != current_user.id and not group.is_member(current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json() if request.is_json else request.form
        
        # Update settings (only creator can change these)
        if group.created_by_id == current_user.id:
            if 'notifications_enabled' in data:
                group.notifications_enabled = data.get('notifications_enabled') in [True, 'true', 'on', '1']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Group settings updated successfully',
            'group': group.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating group settings: {str(e)}')
        return jsonify({'success': False, 'error': 'Error updating group settings'}), 500

@bp.route('/groups/<int:group_id>/members', methods=['POST'])
@login_required
def add_group_member(group_id):
    """Add a member to a group"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Only group creator can add members
        if group.created_by_id != current_user.id:
            return jsonify({'success': False, 'error': 'Only group creator can add members'}), 403
        
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid user ID'}), 400
        
        # Verify the user is friends with this person
        if not current_user.is_friend_with(user_id):
            return jsonify({'success': False, 'error': 'You can only add friends to groups'}), 400
        
        # Add the member
        if group.add_member(user_id):
            db.session.commit()
            user = User.query.get(user_id)
            return jsonify({
                'success': True,
                'message': f'{user.get_full_name()} added to group',
                'group': group.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'User is already in the group'}), 400
            
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding group member: {str(e)}')
        return jsonify({'success': False, 'error': 'Error adding member to group'}), 500

@bp.route('/groups/<int:group_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def remove_group_member(group_id, user_id):
    """Remove a member from a group"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Group creator can remove anyone, members can remove themselves
        if group.created_by_id != current_user.id and user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        if group.remove_member(user_id):
            db.session.commit()
            user = User.query.get(user_id)
            action = 'left' if user_id == current_user.id else 'removed from'
            return jsonify({
                'success': True,
                'message': f'{user.get_full_name()} {action} the group',
                'group': group.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'User is not in the group'}), 400
            
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error removing group member: {str(e)}')
        return jsonify({'success': False, 'error': 'Error removing member from group'}), 500

@bp.route('/groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """Delete a group (only creator can do this)"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Only group creator can delete
        if group.created_by_id != current_user.id:
            return jsonify({'success': False, 'error': 'Only group creator can delete the group'}), 403
        
        group_name = group.name
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Group "{group_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting group: {str(e)}')
        return jsonify({'success': False, 'error': 'Error deleting group'}), 500
