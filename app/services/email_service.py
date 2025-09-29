from flask import current_app, render_template
from flask_mail import Message
from app import mail
import logging

logger = logging.getLogger(__name__)

def send_email(to, subject, template, **kwargs):
    """Send an email using Flask-Mail"""
    try:
        logger.info(f"Attempting to send email to {to} with subject: {subject}")
        msg = Message(
            subject=subject,
            recipients=[to],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        logger.info("Message object created, rendering template...")
        msg.html = render_template(template, **kwargs)
        logger.info("Template rendered, sending email...")
        
        # Add timeout handling
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Email sending timed out after 15 seconds")
        
        # Set timeout for email sending
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)  # 15 second timeout
        
        try:
            mail.send(msg)
            signal.alarm(0)  # Cancel timeout
            logger.info(f"Email sent successfully to {to}")
            return True
        except TimeoutError as te:
            signal.alarm(0)  # Cancel timeout
            logger.error(f"Email sending timed out for {to}: {str(te)}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Email error traceback: {traceback.format_exc()}")
        return False

def send_password_reset_email(user):
    """Send password reset email to user"""
    try:
        token = user.generate_reset_token()
        
        # Use the appropriate domain based on environment
        import os
        base_url = os.environ.get('APP_BASE_URL', 'https://trygatherly.com')
        reset_url = f"{base_url}/auth/reset-password/{token}"
        
        return send_email(
            to=user.email,
            subject='Reset Your Gatherly Password',
            template='email/password_reset.html',
            user=user,
            reset_url=reset_url,
            token=token
        )
    except Exception as e:
        logger.error(f"Error in send_password_reset_email: {str(e)}")
        return False

def is_email_configured():
    """Check if email is properly configured"""
    return bool(
        current_app.config.get('MAIL_USERNAME') and 
        current_app.config.get('MAIL_PASSWORD')
    )
