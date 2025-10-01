"""
Railway Cron Jobs

This file contains cron job functions that can be called by Railway's cron service.
"""

import os
import logging
from flask import Flask
from app import create_app
from app.tasks.sms_scheduler import sms_scheduler
from app.tasks.calendar_scheduler import CalendarScheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def weekend_planning_reminder():
    """
    Weekend planning reminder cron job
    Should be called every Wednesday at 5 PM
    """
    logger.info("Starting weekend planning reminder cron job")
    
    try:
        app = create_app()
        with app.app_context():
            stats = sms_scheduler.send_weekend_planning_reminders()
            logger.info(f"Weekend planning reminders completed: {stats}")
            return stats
    except Exception as e:
        logger.error(f"Error in weekend planning reminder cron job: {str(e)}")
        raise

def weekly_availability_reminder():
    """
    Weekly availability reminder cron job  
    Should be called every Sunday at 6 PM
    """
    logger.info("Starting weekly availability reminder cron job")
    
    try:
        app = create_app()
        with app.app_context():
            stats = sms_scheduler.send_weekly_availability_reminders()
            logger.info(f"Weekly availability reminders completed: {stats}")
            return stats
    except Exception as e:
        logger.error(f"Error in weekly availability reminder cron job: {str(e)}")
        raise

def calendar_sync():
    """
    Calendar sync cron job (Google + Outlook)
    Should be called every 2 hours to sync availability from all connected calendars
    """
    logger.info("Starting calendar availability sync cron job (Google + Outlook)")
    
    try:
        app = create_app()
        with app.app_context():
            stats = CalendarScheduler.sync_all_users_availability()
            logger.info(f"Calendar sync completed: {stats}")
            return stats
    except Exception as e:
        logger.error(f"Error in calendar sync cron job: {str(e)}")
        raise

if __name__ == "__main__":
    # This allows you to test the cron jobs locally
    import sys
    import os
    
    # Check for Railway environment variable to determine which job to run
    cron_job_type = os.environ.get('CRON_JOB_TYPE')
    
    if cron_job_type:
        # Running on Railway with environment variable
        if cron_job_type == "weekend_planning":
            weekend_planning_reminder()
        elif cron_job_type == "weekly_availability":
            weekly_availability_reminder()
        elif cron_job_type == "calendar_sync":
            calendar_sync()
        else:
            print(f"Unknown CRON_JOB_TYPE: {cron_job_type}")
    elif len(sys.argv) > 1:
        # Running locally with command line argument
        job_name = sys.argv[1]
        if job_name == "weekend_planning":
            weekend_planning_reminder()
        elif job_name == "weekly_availability":
            weekly_availability_reminder()
        elif job_name == "calendar_sync":
            calendar_sync()
        else:
            print("Usage: python cron_jobs.py [weekend_planning|weekly_availability|calendar_sync]")
    else:
        print("Available cron jobs:")
        print("- weekend_planning")
        print("- weekly_availability")
        print("- calendar_sync")
        print("Or set CRON_JOB_TYPE environment variable")
