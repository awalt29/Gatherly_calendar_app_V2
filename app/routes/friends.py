from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.friend import Friend
from app.models.notification import Notification
from app.utils.phone_utils import search_phone_patterns

bp = Blueprint('friends', __name__)

@bp.route('/friends')
@login_required
def index():
    """Friends management page"""
    # Get pending friend requests (incoming)
    pending_requests = Friend.get_pending_requests(current_user.id)
    pending_request_users = []
    for request_obj in pending_requests:
        user = User.query.get(request_obj.user_id)
        if user:
            pending_request_users.append({
                'request': request_obj,
                'user': user
            })
    
    # Get sent friend requests (outgoing)
    sent_requests = Friend.get_sent_requests(current_user.id)
    sent_request_users = []
    for request_obj in sent_requests:
        user = User.query.get(request_obj.friend_id)
        if user:
            sent_request_users.append({
                'request': request_obj,
                'user': user
            })
    
    # Get accepted friends
    friends = current_user.get_friends()
    
    return render_template('friends/index.html',
                         pending_requests=pending_request_users,
                         sent_requests=sent_request_users,
                         friends=friends)

@bp.route('/friends/add', methods=['POST'])
@login_required
def add_friend():
    """Send a friend request by phone number"""
    try:
        data = request.get_json() if request.is_json else request.form
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400
        
        # Search for user by phone number with flexible matching
        phone_patterns = search_phone_patterns(phone_number)
        user = User.query.filter(User.phone.in_(phone_patterns)).first()
        
        if not user:
            return jsonify({
                'user_not_found': True,
                'phone_number': phone_number,
                'message': f'No user found with phone number {phone_number}'
            }), 404
        
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot add yourself as a friend'}), 400
        
        # Send friend request
        friend_request, created = Friend.send_friend_request(current_user.id, user.id)
        
        if created:
            # Create notification for the recipient
            Notification.create_friend_request_notification(
                user_id=user.id,
                from_user_id=current_user.id,
                friend_id=friend_request.id
            )
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Friend request sent to {user.get_full_name()}'
            })
        else:
            if friend_request.status == 'accepted':
                return jsonify({'error': 'Already friends with this user'}), 400
            elif friend_request.status == 'pending':
                return jsonify({'error': 'Friend request already sent'}), 400
            else:
                return jsonify({'error': 'Cannot send friend request'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/friends/accept/<int:friend_request_id>', methods=['POST'])
@login_required
def accept_friend(friend_request_id):
    """Accept a friend request"""
    try:
        friend_request = Friend.query.get_or_404(friend_request_id)
        
        # Verify this request is for the current user
        if friend_request.friend_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if friend_request.accept_request():
            requester = User.query.get(friend_request.user_id)
            
            # Create notification for the original requester
            Notification.create_friend_accepted_notification(
                user_id=requester.id,
                from_user_id=current_user.id
            )
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'You are now friends with {requester.get_full_name()}'
            })
        else:
            return jsonify({'error': 'Could not accept friend request'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/friends/decline/<int:friend_request_id>', methods=['POST'])
@login_required
def decline_friend(friend_request_id):
    """Decline a friend request"""
    try:
        friend_request = Friend.query.get_or_404(friend_request_id)
        
        # Verify this request is for the current user
        if friend_request.friend_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if friend_request.decline_request():
            return jsonify({
                'success': True,
                'message': 'Friend request declined'
            })
        else:
            return jsonify({'error': 'Could not decline friend request'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/friends/search')
@login_required
def search_friends():
    """Search for users by phone number"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 3:
        return jsonify([])
    
    # Search for users by phone number with flexible matching
    phone_patterns = search_phone_patterns(query)
    
    # Create OR conditions for all possible patterns
    phone_conditions = []
    for pattern in phone_patterns:
        phone_conditions.append(User.phone.ilike(f'%{pattern}%'))
    
    if phone_conditions:
        from sqlalchemy import or_
        users = User.query.filter(
            or_(*phone_conditions)
        ).filter(User.id != current_user.id).limit(10).all()
    else:
        users = []
    
    results = []
    for user in users:
        # Check friendship status
        friendship_status = Friend.get_friendship_status(current_user.id, user.id)
        
        results.append({
            'id': user.id,
            'name': user.get_full_name(),
            'phone': user.phone,
            'friendship_status': friendship_status
        })
    
    return jsonify(results)

@bp.route('/friends/api/list')
@login_required
def get_friends_list():
    """Get user's friends list for API usage"""
    try:
        friends = current_user.get_friends()
        friends_data = []
        
        for friend in friends:
            friends_data.append({
                'id': friend.id,
                'name': friend.get_full_name(),
                'initials': friend.get_initials()
            })
        
        return jsonify({
            'success': True,
            'friends': friends_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/friends/remove/<int:friend_user_id>', methods=['POST'])
@login_required
def remove_friend(friend_user_id):
    """Remove a friend (unfriend)"""
    try:
        # Find the friendship record
        friendship = Friend.query.filter(
            ((Friend.user_id == current_user.id) & (Friend.friend_id == friend_user_id)) |
            ((Friend.user_id == friend_user_id) & (Friend.friend_id == current_user.id))
        ).filter_by(status='accepted').first()
        
        if not friendship:
            return jsonify({'error': 'Friendship not found'}), 404
        
        # Get the friend's name for the response
        friend_user = User.query.get(friend_user_id)
        if not friend_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete the friendship
        db.session.delete(friendship)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{friend_user.get_full_name()} has been removed from your friends list'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/friends/invite', methods=['POST'])
@login_required
def send_invite():
    """Send an invite to join the app via SMS"""
    try:
        data = request.get_json() if request.is_json else request.form
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400
        
        # Check if user already exists (shouldn't happen, but safety check)
        phone_patterns = search_phone_patterns(phone_number)
        existing_user = User.query.filter(User.phone.in_(phone_patterns)).first()
        if existing_user:
            return jsonify({'error': 'User already exists with this phone number'}), 400
        
        # Send SMS invite
        from app.services.sms_service import send_app_invite_sms
        success = send_app_invite_sms(phone_number, current_user.get_full_name())
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Invite sent to {phone_number}! They\'ll receive a text message with a link to join Gatherly.'
            })
        else:
            return jsonify({'error': 'Failed to send invite. Please try again later.'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
