"""
SMS Scheduler for weekly availability reminders
"""
import logging
from datetime import datetime, timedelta
from app.models.user import User
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)

class SMSScheduler:
    """Handles scheduling and sending of SMS reminders"""
    
    @staticmethod
    def send_weekly_availability_reminders():
        """
        Send weekly availability reminders to all users who have SMS enabled
        This should be called every Sunday at 6 PM
        """
        logger.info("Starting weekly SMS availability reminder job")
        
        if not sms_service.is_configured():
            logger.error("SMS service not configured. Skipping reminder job.")
            return
        
        try:
            # Get all users who have SMS notifications enabled and have phone numbers
            users_to_notify = User.query.filter(
                User.sms_notifications == True,
                User.phone.isnot(None),
                User.phone != '',
                User.is_active == True
            ).all()
            
            logger.info(f"Found {len(users_to_notify)} users eligible for SMS reminders")
            
            if not users_to_notify:
                logger.info("No users to notify. Job completed.")
                return
            
            # Send reminders for next week (week offset 1)
            stats = sms_service.send_bulk_availability_reminders(users_to_notify, week_offset=1)
            
            logger.info(f"Weekly SMS reminder job completed. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in weekly SMS reminder job: {str(e)}")
            raise
    
    @staticmethod
    def send_test_reminder(user_id):
        """
        Send a test SMS reminder to a specific user
        Useful for testing the SMS functionality
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            if not user.phone:
                logger.error(f"User {user_id} has no phone number")
                return False
            
            # Temporarily enable SMS for testing if disabled
            original_sms_setting = user.sms_notifications
            if not original_sms_setting:
                logger.info(f"Temporarily enabling SMS for user {user_id} for testing")
            
            success = sms_service.send_availability_reminder(user, week_offset=1)
            
            logger.info(f"Test SMS reminder sent to user {user_id}: {'Success' if success else 'Failed'}")
            return success
            
        except Exception as e:
            logger.error(f"Error sending test SMS to user {user_id}: {str(e)}")
            return False

# Global instance
sms_scheduler = SMSScheduler()
