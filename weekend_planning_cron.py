#!/usr/bin/env python3
"""
Weekend Planning Reminder Cron Job

This script should be run every Wednesday at 5 PM to send weekend planning reminders.

Usage:
    python weekend_planning_cron.py

Cron entry example:
    0 17 * * 3 cd /path/to/your/app && python weekend_planning_cron.py
"""

import os
import sys
import logging
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.tasks.sms_scheduler import sms_scheduler

def setup_logging():
    """Set up logging for the cron job"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/weekend_planning_cron.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function to run the weekend planning reminder job"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting weekend planning reminder cron job")
    
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Run the weekend planning reminder job
            stats = sms_scheduler.send_weekend_planning_reminders()
            
            if stats:
                logger.info(f"Weekend planning reminders completed successfully: {stats}")
                print(f"✅ Weekend planning reminders sent. Stats: {stats}")
            else:
                logger.warning("Weekend planning reminders completed but no stats returned")
                print("⚠️  Weekend planning reminders completed but no stats returned")
                
    except Exception as e:
        logger.error(f"Error running weekend planning reminder cron job: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    
    logger.info("Weekend planning reminder cron job completed successfully")
    print("🎉 Weekend planning reminder cron job completed successfully")

if __name__ == "__main__":
    main()
