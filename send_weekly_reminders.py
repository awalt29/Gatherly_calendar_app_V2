#!/usr/bin/env python3
"""
Weekly SMS Reminder Script

This script should be run every Sunday to send availability reminders to users.
Can be added to crontab like this:

# Send SMS reminders every Sunday at 6 PM
0 18 * * 0 /path/to/your/project/venv/bin/python /path/to/your/project/send_weekly_reminders.py

"""
import os
import sys
import logging
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment
os.environ.setdefault('FLASK_APP', 'run.py')

from app import create_app, db
from app.tasks.sms_scheduler import sms_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sms_reminders.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run the weekly SMS reminder job"""
    logger.info("=== Starting Weekly SMS Reminder Job ===")
    logger.info(f"Current time: {datetime.now()}")
    
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Run the SMS reminder job
            stats = sms_scheduler.send_weekly_availability_reminders()
            
            if stats:
                logger.info(f"Job completed successfully. Stats: {stats}")
                print(f"✅ SMS reminders sent successfully!")
                print(f"   Total users: {stats['total']}")
                print(f"   Messages sent: {stats['sent']}")
                print(f"   Failed: {stats['failed']}")
                print(f"   Skipped: {stats['skipped']}")
            else:
                logger.warning("Job completed but no stats returned")
                print("⚠️  Job completed but no stats available")
                
    except Exception as e:
        logger.error(f"Error running weekly SMS reminder job: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    
    logger.info("=== Weekly SMS Reminder Job Completed ===")

if __name__ == '__main__':
    main()
