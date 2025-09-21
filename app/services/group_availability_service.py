"""
Service for monitoring group availability and sending SMS alerts
when all members of a group are free at the same time.
"""

from datetime import datetime, timedelta, time, date
from app import db
from app.models.group import Group, GroupMembership, GroupAvailabilityAlert
from app.models.availability import Availability
from app.models.user import User
from app.services.sms_service import sms_service
import logging
import os

logger = logging.getLogger(__name__)

class GroupAvailabilityService:
    
    @staticmethod
    def check_all_groups():
        """Check availability for all active groups and send alerts if needed"""
        try:
            # Get all groups with notifications enabled
            groups = Group.query.filter_by(notifications_enabled=True).all()
            
            total_alerts_sent = 0
            for group in groups:
                alerts_sent = GroupAvailabilityService.check_group_availability(group)
                total_alerts_sent += alerts_sent
            
            logger.info(f"Group availability check completed. {total_alerts_sent} alerts sent across {len(groups)} groups.")
            return total_alerts_sent
            
        except Exception as e:
            logger.error(f"Error checking group availability: {str(e)}")
            return 0
    
    @staticmethod
    def check_group_availability(group):
        """Check availability for a specific group and send alerts if everyone is free"""
        try:
            logger.info(f"Checking availability for group: {group.name} (ID: {group.id})")
            
            # Get all active members
            members = group.get_members()
            if len(members) < 2:
                logger.info(f"Group {group.name} has fewer than 2 members, skipping")
                return 0
            
            # Check availability for the next 7 days
            today = date.today()
            available_dates = []
            
            # Find all days in the next week where everyone is available
            for days_ahead in range(7):  # Check next 7 days
                check_date = today + timedelta(days=days_ahead)
                
                # Check if all members are available on this day
                if GroupAvailabilityService._all_members_available_on_date(members, check_date):
                    # Only include dates we haven't already alerted about
                    if not GroupAvailabilityService._already_alerted_for_date(group.id, check_date):
                        available_dates.append(check_date)
            
            alerts_sent = 0
            # Send one comprehensive alert if there are new available dates
            if available_dates:
                if GroupAvailabilityService._send_group_alert(group, members, available_dates):
                    alerts_sent = 1
                    
                    # Record that we sent alerts for all these dates
                    for alert_date in available_dates:
                        alert_record = GroupAvailabilityAlert(
                            group_id=group.id,
                            date=alert_date
                        )
                        db.session.add(alert_record)
            
            db.session.commit()
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error checking availability for group {group.id}: {str(e)}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def _already_alerted_for_date(group_id, check_date):
        """Check if we already sent an alert for this group and date"""
        return GroupAvailabilityAlert.query.filter_by(
            group_id=group_id,
            date=check_date
        ).first() is not None
    
    @staticmethod
    def _all_members_available_on_date(members, check_date):
        """Check if all group members are available on the given date"""
        try:
            # Get the week start for this date
            week_start = Availability.get_week_start(check_date)
            day_name = check_date.strftime('%A').lower()
            
            # Check availability for all members for this week
            for member in members:
                availability = Availability.query.filter_by(
                    user_id=member.id,
                    week_start_date=week_start
                ).first()
                
                if not availability:
                    # If any member has no availability set, group is not available
                    return False
                
                availability_data = availability.get_availability_data()
                day_availability = availability_data.get(day_name, {})
                
                if not day_availability.get('available', False):
                    # If any member is not available, group is not available
                    return False
            
            # If we get here, all members are available on this date
            return True
            
        except Exception as e:
            logger.error(f"Error checking group availability for date: {str(e)}")
            return False
    
    
    @staticmethod
    def _send_group_alert(group, members, available_dates):
        """Send SMS alert to group creator about the group availability"""
        try:
            creator = User.query.get(group.created_by_id)
            if not creator or not creator.phone or not creator.sms_notifications:
                logger.info(f"Group creator {group.created_by_id} not available for SMS or has SMS disabled")
                return False
            
            # Format the alert message
            member_names = [m.get_full_name() for m in members]
            
            # Format the dates
            if len(available_dates) == 1:
                date_str = available_dates[0].strftime('%A, %B %d')
                message_start = f"🎉 Your group '{group.name}' is all free on {date_str}!"
            else:
                # Format multiple dates nicely
                date_strings = [d.strftime('%A, %B %d') for d in available_dates]
                if len(date_strings) == 2:
                    dates_formatted = f"{date_strings[0]} and {date_strings[1]}"
                else:
                    dates_formatted = ', '.join(date_strings[:-1]) + f", and {date_strings[-1]}"
                message_start = f"🎉 Your group '{group.name}' is all free on {dates_formatted}!"
            
            # Get app base URL for calendar link
            base_url = os.environ.get('APP_BASE_URL', 'http://localhost:5004')
            calendar_url = f"{base_url}/"
            
            # Create the full message
            member_list = ', '.join(member_names[:3]) + ('...' if len(member_names) > 3 else '')
            message = f"{message_start}\n\nMembers: {member_list}\n\n📅 View calendar: {calendar_url}"
            
            # Send SMS
            success = sms_service.send_sms(creator.phone, message)
            
            if success:
                logger.info(f"Group availability alert sent to {creator.phone} for group '{group.name}'")
                return True
            else:
                logger.error(f"Failed to send group availability alert to {creator.phone}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending group alert: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_old_alerts(days_old=30):
        """Clean up old alert records to prevent database bloat"""
        try:
            cutoff_date = date.today() - timedelta(days=days_old)
            old_alerts = GroupAvailabilityAlert.query.filter(
                GroupAvailabilityAlert.date < cutoff_date
            ).all()
            
            count = len(old_alerts)
            for alert in old_alerts:
                db.session.delete(alert)
            
            db.session.commit()
            logger.info(f"Cleaned up {count} old group availability alerts")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {str(e)}")
            db.session.rollback()
            return 0


# Convenience function for external use
def check_group_availability():
    """Main function to check all group availability - used by scheduler"""
    return GroupAvailabilityService.check_all_groups()


def cleanup_old_group_alerts():
    """Cleanup function for old alerts - used by scheduler"""
    return GroupAvailabilityService.cleanup_old_alerts()
