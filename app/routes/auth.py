from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User
from app.services.email_service import send_password_reset_email, is_email_configured
from app.services.sendgrid_service import sendgrid_service
import logging
import os

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('calendar.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('calendar.index')
            return redirect(next_page)
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('calendar.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        
        # Validate required fields
        if not email or not password or not confirm_password or not first_name or not last_name or not phone:
            flash('All fields are required', 'error')
            return render_template('auth/signup.html')
        
        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/signup.html')
        
        # Validate password length
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/signup.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/signup.html')
            
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered', 'error')
            return render_template('auth/signup.html')
        
        # Create new user (no username required, phone required)
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/test-email-config')
def test_email_config():
    """Test endpoint to check email configuration"""
    try:
        config_status = {
            'is_configured': is_email_configured(),
            'mail_server': current_app.config.get('MAIL_SERVER'),
            'mail_port': current_app.config.get('MAIL_PORT'),
            'mail_use_tls': current_app.config.get('MAIL_USE_TLS'),
            'mail_username': current_app.config.get('MAIL_USERNAME'),
            'mail_default_sender': current_app.config.get('MAIL_DEFAULT_SENDER'),
            'has_mail_password': bool(current_app.config.get('MAIL_PASSWORD'))
        }
        return f"<pre>{config_status}</pre>"
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>"

@bp.route('/test-send-email')
def test_send_email():
    """Test endpoint to try sending a simple email"""
    try:
        from app.services.email_service import send_email
        
        # Try to send a simple test email
        success = send_email(
            to=current_app.config.get('MAIL_USERNAME'),  # Send to self
            subject='Gatherly Email Test',
            template='email/test_email.html',
            test_message='This is a test email from Gatherly'
        )
        
        return f"<h1>Email Test</h1><p>Success: {success}</p><p>Check logs for details</p>"
    except Exception as e:
        import traceback
        return f"<h1>Email Test Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

@bp.route('/test-sendgrid')
def test_sendgrid():
    """Test SendGrid email service"""
    try:
        config_status = {
            'is_configured': sendgrid_service.is_configured(),
            'has_api_key': bool(sendgrid_service.api_key),
            'from_email': sendgrid_service.from_email,
            'api_key_preview': sendgrid_service.api_key[:10] + '...' if sendgrid_service.api_key else None
        }
        
        # Try sending a test email if configured
        if sendgrid_service.is_configured():
            test_email = sendgrid_service.from_email
            html_content = "<h1>SendGrid Test</h1><p>This is a test email from Gatherly using SendGrid!</p>"
            
            success = sendgrid_service.send_email(
                to_email=test_email,
                subject='Gatherly SendGrid Test',
                html_content=html_content
            )
            
            config_status['test_email_sent'] = success
        
        return f"<h1>SendGrid Test</h1><pre>{config_status}</pre>"
    except Exception as e:
        import traceback
        return f"<h1>SendGrid Test Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('calendar.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        try:
            logger.info(f"Password reset form submitted for email: {email}")
            
            user = User.query.filter_by(email=email).first()
            logger.info(f"Password reset requested for email: {email}, user found: {bool(user)}")
            
            if user:
                logger.info(f"Generating reset token for user {user.id}")
                
                # Try SendGrid first, then fall back to SMTP
                if sendgrid_service.is_configured():
                    logger.info("Using SendGrid for password reset email")
                    email_sent = sendgrid_service.send_password_reset_email(user)
                    
                    if email_sent:
                        db.session.commit()  # Save the reset token
                        flash('Password reset instructions have been sent to your email.', 'success')
                        logger.info(f"Password reset email sent successfully via SendGrid to {email}")
                    else:
                        # SendGrid failed, try SMTP fallback if available
                        logger.warning(f"SendGrid failed for {email}, trying SMTP fallback")
                        if is_email_configured():
                            logger.info("Falling back to SMTP for password reset email")
                            token = user.generate_reset_token()
                            db.session.commit()
                            
                            email_sent = send_password_reset_email(user)
                            if email_sent:
                                flash('Password reset instructions have been sent to your email.', 'success')
                                logger.info(f"Password reset email sent successfully via SMTP fallback to {email}")
                            else:
                                flash('Email service is temporarily unavailable. Please contact support for assistance.', 'error')
                                logger.error(f"Both SendGrid and SMTP failed for {email}")
                        else:
                            flash('Email service is temporarily unavailable. Please contact support for assistance.', 'error')
                            logger.error(f"SendGrid failed and no SMTP fallback configured for {email}")
                        
                elif is_email_configured():
                    logger.info("Using SMTP for password reset email")
                    # Generate token and save to database
                    token = user.generate_reset_token()
                    db.session.commit()
                    
                    email_sent = send_password_reset_email(user)
                    if email_sent:
                        flash('Password reset instructions have been sent to your email.', 'success')
                        logger.info(f"Password reset email sent successfully via SMTP to {email}")
                    else:
                        flash('Failed to send reset email. Please try again later.', 'error')
                        logger.error(f"Failed to send password reset email via SMTP to {email}")
                else:
                    flash('Email service is not configured. Please contact support for assistance.', 'error')
                    logger.error("Neither SendGrid nor SMTP email service is configured")
            else:
                # For security, don't reveal if email exists or not
                flash('If an account with that email exists, password reset instructions would be provided.', 'info')
                logger.info(f"Password reset requested for non-existent email: {email}")
                
        except Exception as e:
            logger.error(f"Error in forgot password: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            flash('An error occurred. Please try again later.', 'error')
            return render_template('auth/forgot_password.html')
        
        return render_template('auth/forgot_password.html')
    
    return render_template('auth/forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('calendar.index'))
    
    # Find user with this reset token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password and clear reset token
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()
        
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@bp.route('/debug-reset/<email>')
def debug_reset(email):
    """Temporary debug endpoint to generate reset token manually"""
    # Temporarily allow in production for debugging
    # if not current_app.debug:
    #     return "Not available in production", 404
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return f"User with email {email} not found", 404
    
    token = user.generate_reset_token()
    db.session.commit()
    
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    return f"""
    <h1>Debug Password Reset</h1>
    <p>Reset token generated for: {email}</p>
    <p><a href="{reset_url}">Click here to reset password</a></p>
    <p>Or go to: {reset_url}</p>
    """

@bp.route('/test-template/<email>')
def test_template(email):
    """Test SendGrid template functionality"""
    # Temporarily allow in production for debugging
    # if not current_app.debug:
    #     return "Not available in production", 404
    
    from app.services.sendgrid_service import SendGridService
    import os
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return f"User with email {email} not found", 404
    
    sendgrid_service = SendGridService()
    
    # Check configuration
    config_info = {
        'is_configured': sendgrid_service.is_configured(),
        'from_email': sendgrid_service.from_email,
        'template_id': os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID'),
        'api_key_set': bool(os.environ.get('SENDGRID_API_KEY')),
    }
    
    # Try to send template email
    template_id = os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID')
    if template_id:
        reset_url = url_for('auth.reset_password', token='test-token-123', _external=True)
        success = sendgrid_service.send_template_email(
            to_email=email,
            template_id=template_id,
            dynamic_template_data={
                'user_name': user.get_full_name(),
                'reset_url': reset_url,
                'app_name': 'Gatherly'
            }
        )
        result = 'SUCCESS' if success else 'FAILED'
    else:
        result = 'NO_TEMPLATE_ID'
    
    return f"""
    <h1>SendGrid Template Test</h1>
    <h2>Configuration:</h2>
    <pre>{config_info}</pre>
    <h2>Test Result:</h2>
    <p><strong>{result}</strong></p>
    <p>Check the Railway logs for detailed error information.</p>
    """
