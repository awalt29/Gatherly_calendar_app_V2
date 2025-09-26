from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User
from app.services.email_service import send_password_reset_email, is_email_configured
import logging

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
            # Check if email is configured
            if not is_email_configured():
                flash('Email service is not configured. Please add email settings to Railway.', 'error')
                logger.error("Email service not configured - missing MAIL_USERNAME or MAIL_PASSWORD")
                return render_template('auth/forgot_password.html')
            
            user = User.query.filter_by(email=email).first()
            logger.info(f"Password reset requested for email: {email}, user found: {bool(user)}")
            
            if user:
                # Send password reset email
                if send_password_reset_email(user):
                    db.session.commit()  # Save the reset token
                    flash('Password reset instructions have been sent to your email.', 'success')
                    logger.info(f"Password reset email sent successfully to {email}")
                else:
                    flash('Failed to send reset email. Please try again later.', 'error')
                    logger.error(f"Failed to send password reset email to {email}")
            else:
                # For security, don't reveal if email exists or not
                flash('If an account with that email exists, password reset instructions have been sent.', 'info')
                logger.info(f"Password reset requested for non-existent email: {email}")
        except Exception as e:
            logger.error(f"Error in forgot password: {str(e)}")
            flash('An error occurred. Please try again later.', 'error')
            return render_template('auth/forgot_password.html')
        
        return redirect(url_for('auth.login'))
    
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
