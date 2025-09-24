#!/bin/bash
# Railway Cron Job Runner
# This script handles all scheduled tasks for Gatherly

# Set environment
export FLASK_APP=run.py

# Get current time info
HOUR=$(date +%H)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday

echo "Running cron jobs at $(date)"

# Google Calendar Auto-Sync (every 3 hours: 0, 3, 6, 9, 12, 15, 18, 21)
if [ $((HOUR % 3)) -eq 0 ]; then
    echo "Running Google Calendar auto-sync..."
    python sync_google_calendars.py
fi

# Weekly SMS Reminders (Sundays at 6 PM)
if [ "$DAY_OF_WEEK" -eq 7 ] && [ "$HOUR" -eq 18 ]; then
    echo "Running weekly SMS reminders..."
    python send_weekly_reminders.py
fi

# Group Availability Alerts (daily at 10 AM)
if [ "$HOUR" -eq 10 ]; then
    echo "Running group availability check..."
    python check_group_availability.py
fi

echo "Cron job run completed at $(date)"
