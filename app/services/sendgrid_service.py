import os
import logging
from flask import current_app, render_template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

class SendGridService:
    def __init__(self):
        self.api_key = None
        self.from_email = None
        self.client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize SendGrid client with API key"""
        try:
            self.api_key = os.environ.get('SENDGRID_API_KEY')
            self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', os.environ.get('MAIL_DEFAULT_SENDER'))
            
            if self.api_key:
                self.client = SendGridAPIClient(api_key=self.api_key)
                logger.info("SendGrid service initialized successfully")
            else:
                logger.warning("SendGrid API key not found in environment variables")
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid service: {str(e)}")
    
    def is_configured(self):
        """Check if SendGrid is properly configured"""
        return bool(self.api_key and self.from_email and self.client)
    
    def send_email(self, to_email, subject, html_content):
        """Send an email using SendGrid"""
        if not self.is_configured():
            logger.error("SendGrid not configured. Cannot send email.")
            return False
        
        try:
            logger.info(f"Sending email via SendGrid to {to_email} with subject: {subject}")
            
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API returned status code: {response.status_code}")
                logger.error(f"Response body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid to {to_email}: {str(e)}")
            import traceback
            logger.error(f"SendGrid error traceback: {traceback.format_exc()}")
            return False
    
    def send_template_email(self, to_email, template_id, dynamic_template_data):
        """Send an email using SendGrid Dynamic Template"""
        if not self.is_configured():
            logger.error("SendGrid is not configured")
            return False
        
        try:
            logger.info(f"Sending template email via SendGrid to {to_email} with template: {template_id}")
            
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email
            )
            
            # Set the template ID
            message.template_id = template_id
            
            # Add dynamic template data
            message.dynamic_template_data = dynamic_template_data
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Template email sent successfully via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API returned status code: {response.status_code}")
                logger.error(f"Response body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send template email via SendGrid to {to_email}: {str(e)}")
            import traceback
            logger.error(f"SendGrid template error traceback: {traceback.format_exc()}")
            return False
    
    def send_password_reset_email(self, user):
        """Send password reset email using SendGrid Dynamic Template"""
        try:
            # Generate reset token
            token = user.generate_reset_token()
            
            # Build reset URL
            base_url = os.environ.get('APP_BASE_URL', 'https://trygatherly.com')
            reset_url = f"{base_url}/auth/reset-password/{token}"
            
            # Use dynamic template if configured, otherwise fall back to HTML
            template_id = os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID')
            
            if template_id:
                # Send using dynamic template
                success = self.send_template_email(
                    to_email=user.email,
                    template_id=template_id,
                    dynamic_template_data={
                        'user_name': user.get_full_name(),
                        'reset_url': reset_url,
                        'app_name': 'Gatherly'
                    }
                )
            else:
                # Fallback to HTML template
                html_content = render_template(
                    'email/password_reset.html',
                    user=user,
                    reset_url=reset_url,
                    token=token
                )
                
                success = self.send_email(
                    to_email=user.email,
                    subject='Reset Your Gatherly Password',
                    html_content=html_content
                )
            
            if success:
                logger.info(f"Password reset email sent successfully to {user.email}")
                return True
            else:
                logger.error(f"Failed to send password reset email to {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Error in send_password_reset_email: {str(e)}")
            return False

# Global instance
sendgrid_service = SendGridService()
