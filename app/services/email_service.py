from flask import current_app, render_template
from flask_mail import Message
from app import mail
import logging

logger = logging.getLogger(__name__)

def send_email(to, subject, template, **kwargs):
    """Send an email using Flask-Mail"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        logger.info(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        return False

def send_password_reset_email(user):
    """Send password reset email to user"""
    token = user.generate_reset_token()
    
    # For development, we'll use localhost. In production, use your domain
    reset_url = f"http://localhost:5004/auth/reset-password/{token}"
    
    return send_email(
        to=user.email,
        subject='Reset Your Gatherly Password',
        template='email/password_reset.html',
        user=user,
        reset_url=reset_url,
        token=token
    )

def is_email_configured():
    """Check if email is properly configured"""
    return bool(
        current_app.config.get('MAIL_USERNAME') and 
        current_app.config.get('MAIL_PASSWORD')
    )
