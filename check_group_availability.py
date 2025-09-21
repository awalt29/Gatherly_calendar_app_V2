#!/usr/bin/env python3
"""
Scheduled script to check group availability and send SMS alerts.
This script should be run daily to check for new group availability matches.

Example cron job (runs daily at 10 AM):
0 10 * * * cd /path/to/gatherly && python3 check_group_availability.py

Or run manually for testing:
python3 check_group_availability.py
"""

import os
import sys
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import create_app, db
from app.services.group_availability_service import check_group_availability, cleanup_old_group_alerts
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('group_availability.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to check group availability"""
    logger.info("Starting group availability check...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Check group availability and send alerts
            alerts_sent = check_group_availability()
            logger.info(f"Group availability check completed. {alerts_sent} alerts sent.")
            
            # Cleanup old alerts (run once per day)
            current_hour = datetime.now().hour
            if current_hour == 2:  # Run cleanup at 2 AM
                cleaned_up = cleanup_old_group_alerts()
                logger.info(f"Cleaned up {cleaned_up} old alert records.")
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error in group availability check: {str(e)}")
            return 0

if __name__ == '__main__':
    alerts_sent = main()
    print(f"Group availability check completed. {alerts_sent} alerts sent.")
    sys.exit(0)
