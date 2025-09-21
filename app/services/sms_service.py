"""
SMS Service for sending availability reminders via Twilio
"""
import os
from datetime import datetime, timedelta
from twilio.rest import Client
from flask import current_app, url_for
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_phone = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured. SMS functionality disabled.")
    
    def is_configured(self):
        """Check if Twilio is properly configured"""
        return self.client is not None and self.from_phone is not None
    
    def send_availability_reminder(self, user, week_offset=1):
        """
        Send weekly availability reminder to user
        
        Args:
            user: User object
            week_offset: Number of weeks from now (1 = next week)
        """
        if not self.is_configured():
            logger.error("SMS service not configured. Cannot send reminder.")
            return False
            
        if not user.phone:
            logger.warning(f"User {user.id} has no phone number. Cannot send SMS.")
            return False
            
        if not user.sms_notifications:
            logger.info(f"User {user.id} has SMS notifications disabled.")
            return False
        
        try:
            # Generate the availability URL for the specific week
            # Use a simple base URL since url_for may not work outside request context
            base_url = os.environ.get('APP_BASE_URL', 'http://localhost:5005')
            availability_url = f"{base_url}/availability/week/{week_offset}"
            
            # Create the message
            message_body = (
                f"Hi {user.first_name or user.username}! 📅\n\n"
                f"Time to fill in your availability so you don't miss out on fun plans!\n\n"
                f"Update your schedule here: {availability_url}\n\n"
                f"- Gatherly"
            )
            
            # Send the SMS
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_phone,
                to=user.phone
            )
            
            logger.info(f"SMS sent successfully to {user.phone}. Message SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {user.phone}: {str(e)}")
            return False
    
    def send_bulk_availability_reminders(self, users, week_offset=1):
        """
        Send availability reminders to multiple users
        
        Args:
            users: List of User objects
            week_offset: Number of weeks from now
            
        Returns:
            dict: Statistics about sent messages
        """
        stats = {
            'total': len(users),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for user in users:
            if not user.sms_notifications or not user.phone:
                stats['skipped'] += 1
                continue
                
            success = self.send_availability_reminder(user, week_offset)
            if success:
                stats['sent'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Bulk SMS reminder stats: {stats}")
        return stats
    
    def send_event_group_chat(self, event, recipients, sender):
        """
        Send group chat message to all event attendees as a single group SMS
        
        Args:
            event: Event object
            recipients: List of User objects to send messages to
            sender: User object who initiated the group chat
            
        Returns:
            dict: Statistics about sent messages
        """
        stats = {
            'total': len(recipients),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        if not self.is_configured():
            logger.error("SMS service not configured. Cannot send group chat.")
            return stats
        
        # Get all phone numbers
        phone_numbers = []
        attendee_names = []
        
        for recipient in recipients:
            if recipient.phone:
                phone_numbers.append(recipient.phone)
                if recipient.id == sender.id:
                    attendee_names.append(f"{recipient.get_full_name()} (started chat)")
                else:
                    attendee_names.append(recipient.get_full_name())
            else:
                stats['skipped'] += 1
                logger.info(f"Skipping {recipient.get_full_name()} - no phone number")
        
        if len(phone_numbers) < 2:
            logger.warning("Need at least 2 phone numbers for group chat")
            return stats
        
        # Format event date and time
        event_date = event.date.strftime('%A, %B %d, %Y')
        event_time = f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"
        
        # Create the group chat message
        message_body = (
            f"🎉 GROUP CHAT: {event.title}\n\n"
            f"📅 {event_date}\n"
            f"⏰ {event_time}\n"
        )
        
        if event.description:
            message_body += f"\n📝 {event.description}\n"
        
        message_body += f"\n👥 Group Members: {', '.join(attendee_names)}\n"
        message_body += f"\n💬 Reply to this message to chat with everyone!\n\n- Gatherly"
        
        try:
            # Create a single group message using Twilio's messaging service
            # Note: This creates a group conversation where everyone can see each other's numbers
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_phone,
                to=phone_numbers  # Send to multiple recipients as a group
            )
            
            stats['sent'] = len(phone_numbers)
            logger.info(f"Group chat SMS sent to {len(phone_numbers)} recipients for event '{event.title}'. Message SID: {message.sid}")
            
        except Exception as e:
            # If group messaging fails, fall back to individual messages with group context
            logger.warning(f"Group SMS failed, falling back to individual messages: {str(e)}")
            
            # Add phone numbers to message so people can create their own group
            phone_list = [f"{name}: {phone}" for name, phone in zip(attendee_names, phone_numbers)]
            fallback_message = message_body + f"\n📱 Group Numbers:\n{chr(10).join(phone_list)}"
            
            for i, phone in enumerate(phone_numbers):
                try:
                    # Personalize the message for each recipient
                    personal_message = fallback_message.replace(
                        f"{attendee_names[i]} (started chat)", "You (started chat)"
                    ).replace(
                        attendee_names[i], "You"
                    )
                    
                    message = self.client.messages.create(
                        body=personal_message,
                        from_=self.from_phone,
                        to=phone
                    )
                    
                    stats['sent'] += 1
                    logger.info(f"Fallback group chat SMS sent to {phone}. Message SID: {message.sid}")
                    
                except Exception as inner_e:
                    logger.error(f"Failed to send fallback SMS to {phone}: {str(inner_e)}")
                    stats['failed'] += 1
        
        logger.info(f"Event group chat stats for '{event.title}': {stats}")
        return stats
    
    def send_event_invitations(self, event, invitees, creator):
        """
        Send SMS invitations for a new event
        
        Args:
            event: Event object
            invitees: List of User objects to invite
            creator: User object who created the event
            
        Returns:
            dict: Statistics about sent invitations
        """
        stats = {
            'total': len(invitees),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        if not self.is_configured():
            logger.error("SMS service not configured. Cannot send invitations.")
            return stats
        
        # Format event date and time
        event_date = event.date.strftime('%A, %B %d, %Y')
        event_time = f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"
        
        # Get app base URL for RSVP link
        base_url = os.environ.get('APP_BASE_URL', 'http://localhost:5004')
        events_url = f"{base_url}/events"
        
        # Create list of all attendees (creator + invitees)
        all_attendees = [creator] + invitees
        attendee_names = [attendee.get_full_name() for attendee in all_attendees]
        
        for invitee in invitees:
            if not invitee.phone:
                stats['skipped'] += 1
                logger.info(f"Skipping {invitee.get_full_name()} - no phone number")
                continue
            
            # Create personalized invitation message
            message_body = (
                f"🎉 You're invited!\n\n"
                f"Event: {event.title}\n"
                f"📅 {event_date}\n"
                f"⏰ {event_time}\n"
            )
            
            if event.description:
                message_body += f"\n📝 {event.description}\n"
            
            # Add invitees list
            message_body += f"\n👥 Invited: {', '.join(attendee_names)}\n"
            
            message_body += (
                f"\nInvited by: {creator.get_full_name()}\n"
                f"\n📱 RSVP here: {events_url}\n"
                f"\n- Gatherly"
            )
            
            try:
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_phone,
                    to=invitee.phone
                )
                
                logger.info(f"Event invitation sent to {invitee.phone} ({invitee.get_full_name()}). Message SID: {message.sid}")
                stats['sent'] += 1
                
            except Exception as e:
                logger.error(f"Failed to send invitation SMS to {invitee.phone} ({invitee.get_full_name()}): {str(e)}")
                stats['failed'] += 1
        
        logger.info(f"Event invitation stats for '{event.title}': {stats}")
        return stats
    
    def send_rsvp_reminders(self, event, pending_invitees, creator):
        """
        Send RSVP reminder SMS to users who haven't responded
        
        Args:
            event: Event object
            pending_invitees: List of User objects who haven't responded
            creator: User object who created the event
            
        Returns:
            dict: Statistics about sent reminders
        """
        stats = {
            'total': len(pending_invitees),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        if not self.is_configured():
            logger.error("SMS service not configured. Cannot send reminders.")
            return stats
        
        # Format event date and time
        event_date = event.date.strftime('%A, %B %d, %Y')
        event_time = f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"
        
        # Get app base URL for RSVP link
        base_url = os.environ.get('APP_BASE_URL', 'http://localhost:5004')
        events_url = f"{base_url}/events"
        
        for invitee in pending_invitees:
            if not invitee.phone:
                stats['skipped'] += 1
                logger.info(f"Skipping {invitee.get_full_name()} - no phone number")
                continue
            
            # Create reminder message
            message_body = (
                f"⏰ RSVP Reminder\n\n"
                f"Event: {event.title}\n"
                f"📅 {event_date}\n"
                f"⏰ {event_time}\n"
                f"\nFrom: {creator.get_full_name()}\n"
                f"\n🙏 Please respond: {events_url}\n"
                f"\n- Gatherly"
            )
            
            try:
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_phone,
                    to=invitee.phone
                )
                
                logger.info(f"RSVP reminder sent to {invitee.phone} ({invitee.get_full_name()}). Message SID: {message.sid}")
                stats['sent'] += 1
                
            except Exception as e:
                logger.error(f"Failed to send RSVP reminder to {invitee.phone} ({invitee.get_full_name()}): {str(e)}")
                stats['failed'] += 1
        
        logger.info(f"RSVP reminder stats for '{event.title}': {stats}")
        return stats
    
    def send_sms(self, phone_number, message):
        """
        Send a generic SMS message
        
        Args:
            phone_number: Recipient's phone number
            message: Message content
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_configured():
            logger.error("SMS service not configured. Cannot send SMS.")
            return False
            
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully to {phone_number}. Message SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False

# Global instance
sms_service = SMSService()

# Convenience function for backward compatibility
def send_sms(phone_number, message):
    """Send SMS using the global SMS service instance"""
    return sms_service.send_sms(phone_number, message)
