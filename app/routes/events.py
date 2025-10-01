from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, time
from app import db
from app.models.event import Event
from app.models.event_invitation import EventInvitation
from app.models.user import User
from app.models.google_calendar_sync import GoogleCalendarSync
from app.models.notification import Notification
from app.services.google_calendar_service import google_calendar_service
from app.services.sms_service import SMSService
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('events', __name__)

@bp.route('/events')
@login_required
def index():
    """Events page showing user's events and pending invitations"""
    # Get all events where the user is an attendee or creator
    user_events = Event.query.filter(
        (Event.attendees.contains(current_user)) | 
        (Event.created_by_id == current_user.id)
    ).order_by(Event.date.desc(), Event.start_time.desc()).all()
    
    # Get pending invitations for this user
    pending_invitations = EventInvitation.query.filter_by(
        invitee_id=current_user.id,
        status='pending'
    ).order_by(EventInvitation.created_at.desc()).all()
    
    return render_template('events/index.html', events=user_events, pending_invitations=pending_invitations)

@bp.route('/events/<int:event_id>/data')
@login_required
def get_event_data(event_id):
    """Get event data for editing"""
    event = Event.query.get_or_404(event_id)
    
    # Only the event creator can edit
    if event.created_by_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    return jsonify({
        'success': True,
        'event': {
            'id': event.id,
            'title': event.title,
            'location': event.location or '',
            'description': event.description,
            'date': event.date.isoformat(),
            'start_time': event.start_time.strftime('%H:%M'),
            'end_time': event.end_time.strftime('%H:%M')
        }
    })

@bp.route('/events/<int:event_id>/guests')
@login_required
def get_event_guests(event_id):
    """Get event guests for editing"""
    event = Event.query.get_or_404(event_id)
    
    # Only the event creator can view guests for editing
    if event.created_by_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    guests = []
    
    # Add creator (always attending)
    creator = event.created_by
    guests.append({
        'id': creator.id,
        'name': creator.get_full_name(),
        'initials': creator.get_initials(),
        'status': 'organizer'
    })
    
    # Add current attendees (excluding creator)
    for attendee in event.attendees:
        if attendee.id != creator.id:
            guests.append({
                'id': attendee.id,
                'name': attendee.get_full_name(),
                'initials': attendee.get_initials(),
                'status': 'attending'
            })
    
    # Add pending invitations
    invitations = EventInvitation.query.filter_by(event_id=event_id).all()
    for invitation in invitations:
        if invitation.invitee_id not in [g['id'] for g in guests]:
            guests.append({
                'id': invitation.invitee.id,
                'name': invitation.invitee.get_full_name(),
                'initials': invitation.invitee.get_initials(),
                'status': invitation.status
            })
    
    return jsonify({
        'success': True,
        'guests': guests
    })

@bp.route('/events/<int:event_id>/edit', methods=['POST'])
@login_required
def edit_event(event_id):
    """Edit an existing event"""
    event = Event.query.get_or_404(event_id)
    
    # Only the event creator can edit
    if event.created_by_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        guest_ids_json = request.form.get('guest_ids')
        
        # Validation
        if not title:
            return jsonify({'success': False, 'error': 'Event title is required'})
        
        if not date_str or not start_time_str or not end_time_str:
            return jsonify({'success': False, 'error': 'Date and time are required'})
        
        # Parse date and times
        event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate times
        if start_time >= end_time:
            return jsonify({'success': False, 'error': 'Start time must be before end time'})
        
        # Update event
        event.title = title
        event.location = location if location else None
        event.description = description if description else None
        event.date = event_date
        event.start_time = start_time
        event.end_time = end_time
        event.updated_at = datetime.utcnow()
        
        # Handle guest updates if provided
        if guest_ids_json:
            try:
                import json
                guest_ids = json.loads(guest_ids_json)
                
                # Ensure current user is always included
                if current_user.id not in guest_ids:
                    guest_ids.append(current_user.id)
                
                # Get current attendees and invitations
                current_attendees = [user.id for user in event.attendees]
                current_invitations = EventInvitation.query.filter_by(event_id=event.id).all()
                current_invitees = [inv.invitee_id for inv in current_invitations]
                
                # Determine who to add and remove
                all_current = set(current_attendees + current_invitees)
                new_guests = set(guest_ids)
                
                to_add = new_guests - all_current
                to_remove = all_current - new_guests
                
                # Remove users (delete invitations, remove from attendees)
                for user_id in to_remove:
                    if user_id != current_user.id:  # Don't remove the creator
                        # Remove from attendees
                        user_to_remove = User.query.get(user_id)
                        if user_to_remove and user_to_remove in event.attendees:
                            event.attendees.remove(user_to_remove)
                        
                        # Delete invitations
                        EventInvitation.query.filter_by(
                            event_id=event.id, 
                            invitee_id=user_id
                        ).delete()
                
                # Add new users (create invitations)
                new_invitees = []
                for user_id in to_add:
                    if user_id != current_user.id:  # Don't invite the creator
                        user_to_add = User.query.get(user_id)
                        if user_to_add:
                            # Create invitation
                            invitation = EventInvitation(
                                event_id=event.id,
                                invitee_id=user_id,
                                status='pending'
                            )
                            db.session.add(invitation)
                            new_invitees.append(user_to_add)
                            
                            # Create notification for the invited user
                            try:
                                Notification.create_event_invited_notification(
                                    user_id=user_id,
                                    from_user_id=current_user.id,
                                    event_id=event.id
                                )
                                logger.info(f"Created event edit notification for user {user_id} for event {event.id}")
                            except Exception as e:
                                logger.error(f"Failed to create event edit notification: {str(e)}")
                                # Don't fail the event update if notification fails
                
                # Commit changes first
                db.session.commit()
                
                # Send SMS invitations to new invitees
                if new_invitees:
                    try:
                        from app.services.sms_service import sms_service
                        if sms_service.is_configured():
                            stats = sms_service.send_event_invitations(event, new_invitees, current_user)
                            logger.info(f"SMS invitation stats for event edit: {stats}")
                    except Exception as e:
                        logger.error(f"Failed to send SMS invitations for event edit: {str(e)}")
                        # Don't fail the event update if SMS fails
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing guest_ids: {str(e)}")
                # Continue without guest updates if JSON is invalid
        else:
            # If no guest updates, still commit the event changes
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event updated successfully!'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating event {event_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update event'}), 500

@bp.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an event"""
    event = Event.query.get_or_404(event_id)
    
    # Only the event creator can delete
    if event.created_by_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        # Delete all related invitations first
        EventInvitation.query.filter_by(event_id=event_id).delete()
        
        # Delete the event (this will also remove attendee relationships)
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event deleted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting event {event_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to delete event'}), 500

@bp.route('/events/<int:event_id>/group-chat', methods=['POST'])
@login_required
def create_group_chat(event_id):
    """Send group SMS to all event attendees"""
    event = Event.query.get_or_404(event_id)
    
    # Check if user is part of the event (either creator or attendee)
    if not (event.created_by_id == current_user.id or current_user in event.attendees):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        from app.services.sms_service import sms_service
        
        # Check if SMS is configured
        if not sms_service.is_configured():
            return jsonify({'success': False, 'error': 'SMS service not configured'}), 400
        
        # Get all attendees with phone numbers (including creator)
        recipients = []
        
        # Add event creator
        if event.created_by.phone:
            recipients.append(event.created_by)
        
        # Add all attendees
        for attendee in event.attendees:
            if attendee.phone and attendee not in recipients:
                recipients.append(attendee)
        
        if not recipients:
            return jsonify({'success': False, 'error': 'No attendees have phone numbers'}), 400
        
        # Send group SMS
        stats = sms_service.send_event_group_chat(event, recipients, current_user)
        
        if stats['sent'] > 0:
            return jsonify({
                'success': True,
                'message': f'Group chat messages sent to {stats["sent"]} attendees!'
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'Failed to send messages. {stats["failed"]} failed, {stats["skipped"]} skipped.'
            })
        
    except ImportError:
        return jsonify({'success': False, 'error': 'SMS service not available'}), 500
    except Exception as e:
        logger.error(f"Error sending group chat for event {event_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send group messages'}), 500

@bp.route('/events/<int:event_id>/send-reminders', methods=['POST'])
@login_required
def send_rsvp_reminders(event_id):
    """Send RSVP reminder SMS to users who haven't responded"""
    event = Event.query.get_or_404(event_id)
    
    # Only the event creator can send reminders
    if event.created_by_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        from app.services.sms_service import sms_service
        
        # Check if SMS is configured
        if not sms_service.is_configured():
            return jsonify({'success': False, 'error': 'SMS service not configured'}), 400
        
        # Get all pending invitations for this event
        pending_invitations = EventInvitation.query.filter_by(
            event_id=event_id,
            status='pending'
        ).all()
        
        if not pending_invitations:
            return jsonify({
                'success': True,
                'message': 'No pending RSVPs to remind!'
            })
        
        # Get users who haven't responded
        pending_users = [invitation.invitee for invitation in pending_invitations if invitation.invitee.phone]
        
        if not pending_users:
            return jsonify({
                'success': False,
                'error': 'No pending invitees have phone numbers'
            })
        
        # Send RSVP reminders
        stats = sms_service.send_rsvp_reminders(event, pending_users, current_user)
        
        if stats['sent'] > 0:
            return jsonify({
                'success': True,
                'message': f'RSVP reminders sent to {stats["sent"]} people!'
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'Failed to send reminders. {stats["failed"]} failed, {stats["skipped"]} skipped.'
            })
        
    except ImportError:
        return jsonify({'success': False, 'error': 'SMS service not available'}), 500
    except Exception as e:
        logger.error(f"Error sending RSVP reminders for event {event_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send reminders'}), 500

@bp.route('/events/create', methods=['POST'])
@login_required
def create():
    """Create a new event"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Event title is required'}), 400
        
        if not data.get('date'):
            return jsonify({'success': False, 'error': 'Event date is required'}), 400
        
        if not data.get('start_time') or not data.get('end_time'):
            return jsonify({'success': False, 'error': 'Start and end times are required'}), 400
        
        if not data.get('attendee_ids') or len(data.get('attendee_ids', [])) < 2:
            return jsonify({'success': False, 'error': 'At least 2 attendees are required'}), 400
        
        # Parse date and times
        event_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        # Validate attendees exist and include current user
        attendee_ids = data['attendee_ids']
        if current_user.id not in attendee_ids:
            attendee_ids.append(current_user.id)
        
        attendees = User.query.filter(User.id.in_(attendee_ids)).all()
        if len(attendees) != len(attendee_ids):
            return jsonify({'success': False, 'error': 'Some attendees were not found'}), 400
        
        # Create the event
        event = Event(
            title=data['title'],
            location=data.get('location', ''),
            description=data.get('description', ''),
            date=event_date,
            start_time=start_time,
            end_time=end_time,
            created_by_id=current_user.id
        )
        
        # Add only the creator as an attendee initially
        event.attendees = [current_user]
        
        db.session.add(event)
        db.session.flush()  # Flush to get the event ID
        
        # Create invitations for other attendees (excluding the creator)
        other_attendees = [user for user in attendees if user.id != current_user.id]
        for attendee in other_attendees:
            invitation = EventInvitation(
                event_id=event.id,
                invitee_id=attendee.id,
                status='pending'
            )
            db.session.add(invitation)
            
            # Create notification for the invited user
            try:
                Notification.create_event_invited_notification(
                    user_id=attendee.id,
                    from_user_id=current_user.id,
                    event_id=event.id
                )
                logger.info(f"Created event notification for user {attendee.id} for event {event.id}")
            except Exception as e:
                logger.error(f"Failed to create event notification: {str(e)}")
                # Don't fail the event creation if notification fails
        
        db.session.commit()
        
        # Send SMS invitations to other attendees
        try:
            from app.services.sms_service import sms_service
            if sms_service.is_configured() and other_attendees:
                stats = sms_service.send_event_invitations(event, other_attendees, current_user)
                logger.info(f"SMS invitation stats: {stats}")
        except Exception as e:
            logger.error(f"Failed to send SMS invitations: {str(e)}")
            # Don't fail the event creation if SMS fails
        
        # Try to add event to creator's Google Calendar if enabled
        try:
            _add_event_to_google_calendar(current_user, event)
        except Exception as e:
            logger.error(f"Failed to add event to Google Calendar: {str(e)}")
            # Don't fail the event creation if calendar integration fails
        
        # Try to add event to creator's Outlook Calendar if enabled
        try:
            _add_event_to_outlook_calendar(current_user, event)
        except Exception as e:
            logger.error(f"Failed to add event to Outlook Calendar: {str(e)}")
            # Don't fail the event creation if calendar integration fails
        
        return jsonify({
            'success': True, 
            'message': 'Event created and invitations sent!',
            'event_id': event.id
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def _add_event_to_google_calendar(user, event):
    """Helper function to add an event to user's Google Calendar"""
    try:
        # Check if user has Google Calendar connected and auto-add enabled
        sync_record = GoogleCalendarSync.query.filter_by(user_id=user.id).first()
        if not sync_record or not sync_record.auto_add_events:
            return False
        
        # Create Google Calendar event data
        google_event = {
            'summary': event.title,
            'description': f"{event.description}\n\nCreated via Gatherly",
            'start': {
                'dateTime': f"{event.date}T{event.start_time}",
                'timeZone': user.timezone or 'America/New_York'
            },
            'end': {
                'dateTime': f"{event.date}T{event.end_time}",
                'timeZone': user.timezone or 'America/New_York'
            },
            'attendees': [
                {'email': attendee.email, 'displayName': attendee.get_full_name()} 
                for attendee in event.attendees
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'email', 'minutes': 60}
                ]
            },
            'source': {
                'title': 'Gatherly',
                'url': 'http://localhost:5006'  # Update with actual domain
            }
        }
        
        # Add to Google Calendar
        google_event_id = google_calendar_service.create_event(user.id, google_event)
        
        if google_event_id:
            logger.info(f"Added event {event.id} to Google Calendar for user {user.id}: {google_event_id}")
            return True
        else:
            logger.warning(f"Failed to add event {event.id} to Google Calendar for user {user.id}")
            return False
            
    except Exception as e:
        logger.error(f"Error adding event {event.id} to Google Calendar for user {user.id}: {str(e)}")
        return False

def _add_event_to_outlook_calendar(user, event):
    """Helper function to add an event to user's Outlook Calendar"""
    try:
        from app.services.outlook_calendar_service import outlook_calendar_service
        from app.models.outlook_calendar_sync import OutlookCalendarSync
        
        # Check if user has Outlook Calendar connected and auto-add enabled
        sync_record = OutlookCalendarSync.query.filter_by(user_id=user.id).first()
        if not sync_record or not sync_record.auto_add_events:
            return False
        
        # Create Outlook Calendar event data
        outlook_event = {
            'subject': event.title,
            'body': {
                'contentType': 'text',
                'content': f"{event.description}\n\nCreated via Gatherly"
            },
            'start': {
                'dateTime': f"{event.date}T{event.start_time}",
                'timeZone': user.timezone or 'America/New_York'
            },
            'end': {
                'dateTime': f"{event.date}T{event.end_time}",
                'timeZone': user.timezone or 'America/New_York'
            },
            'attendees': [
                {
                    'emailAddress': {
                        'address': attendee.email,
                        'name': attendee.get_full_name()
                    },
                    'type': 'required'
                } 
                for attendee in event.attendees
            ],
            'reminderMinutesBeforeStart': 30,
            'isReminderOn': True
        }
        
        # Add location if provided
        if event.location:
            outlook_event['location'] = {
                'displayName': event.location
            }
        
        # Add to Outlook Calendar
        success = outlook_calendar_service.create_event(user.id, outlook_event)
        
        if success:
            logger.info(f"Added event {event.id} to Outlook Calendar for user {user.id}")
            return True
        else:
            logger.warning(f"Failed to add event {event.id} to Outlook Calendar for user {user.id}")
            return False
    except Exception as e:
        logger.error(f"Error adding event {event.id} to Outlook Calendar for user {user.id}: {str(e)}")
        return False

@bp.route('/events/invitation/<int:invitation_id>/accept', methods=['POST'])
@login_required
def accept_invitation(invitation_id):
    """Accept an event invitation"""
    try:
        invitation = EventInvitation.query.get_or_404(invitation_id)
        
        # Verify the invitation belongs to the current user
        if invitation.invitee_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if invitation.accept():
            db.session.commit()
            
            # Try to add event to user's Google Calendar if enabled
            _add_event_to_google_calendar(current_user, invitation.event)
            
            # Try to add event to user's Outlook Calendar if enabled
            _add_event_to_outlook_calendar(current_user, invitation.event)
            
            # Send SMS notification to event creator
            _send_rsvp_notification(invitation.event.created_by, invitation, 'accepted')
            
            return jsonify({
                'success': True, 
                'message': 'Invitation accepted successfully!'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Invitation has already been responded to'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/events/invitation/<int:invitation_id>/decline', methods=['POST'])
@login_required
def decline_invitation(invitation_id):
    """Decline an event invitation"""
    try:
        invitation = EventInvitation.query.get_or_404(invitation_id)
        
        # Verify the invitation belongs to the current user
        if invitation.invitee_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if invitation.decline():
            db.session.commit()
            
            # Send SMS notification to event creator
            _send_rsvp_notification(invitation.event.created_by, invitation, 'declined')
            
            return jsonify({
                'success': True, 
                'message': 'Invitation declined'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Invitation has already been responded to'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def _send_rsvp_notification(event_creator, invitation, action):
    """Send SMS notification to event creator when someone RSVPs"""
    try:
        logger.info(f"Attempting to send RSVP notification for invitation {invitation.id}, action: {action}")
        
        # Don't send notification if creator is responding to their own event
        if event_creator.id == invitation.invitee_id:
            logger.info("Skipping notification - creator is responding to their own event")
            return
            
        # Check if creator has a phone number
        if not event_creator.phone:
            logger.warning(f"Event creator {event_creator.id} has no phone number for RSVP notification")
            return
        
        # Format the event date and time
        event = invitation.event
        event_date = event.date.strftime('%B %d, %Y')
        start_time_str = event.start_time.strftime('%I:%M %p').lstrip('0')
        end_time_str = event.end_time.strftime('%I:%M %p').lstrip('0')
        event_time = f"{start_time_str} - {end_time_str}"
        
        # Create the notification message
        responder_name = invitation.invitee.get_full_name()
        action_text = "accepted" if action == 'accepted' else "declined"
        emoji = "✅" if action == 'accepted' else "❌"
        
        message = f"{emoji} RSVP Update: {responder_name} has {action_text} your event invitation for '{event.title}' on {event_date} at {event_time}."
        
        logger.info(f"Sending SMS to {event_creator.phone}: {message}")
        
        # Send the SMS
        sms_service = SMSService()
        success = sms_service.send_sms(event_creator.phone, message)
        
        if success:
            logger.info(f"RSVP notification sent to event creator {event_creator.id} for invitation {invitation.id}")
        else:
            logger.error(f"Failed to send RSVP notification to event creator {event_creator.id}")
            
    except Exception as e:
        logger.error(f"Error sending RSVP notification: {str(e)}")
