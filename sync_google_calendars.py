#!/usr/bin/env python3
"""
Google Calendar Sync Cron Job

This script should be run periodically (every 2-4 hours) to sync availability
from Google Calendar for all users who have auto-sync enabled.

Add to crontab:
# Sync Google Calendar availability every 3 hours
0 */3 * * * cd /path/to/your/app && python sync_google_calendars.py

Or for Railway deployment, use Railway's cron jobs or a scheduler service.
"""

import os
import sys
import logging
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_calendar_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run the Google Calendar sync job"""
    try:
        # Import here to avoid issues with app context
        from app import create_app
        from app.tasks.google_calendar_scheduler import google_calendar_scheduler
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            logger.info("=" * 50)
            logger.info(f"Starting Google Calendar sync job at {datetime.now()}")
            
            # Run the sync job
            stats = google_calendar_scheduler.sync_all_users_availability()
            
            logger.info(f"Google Calendar sync job completed. Stats: {stats}")
            logger.info("=" * 50)
            
    except Exception as e:
        logger.error(f"Error running Google Calendar sync job: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
