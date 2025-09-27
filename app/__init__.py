from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
mail = Mail()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.calendar import bp as calendar_bp
    app.register_blueprint(calendar_bp)

    from app.routes.availability import bp as availability_bp
    app.register_blueprint(availability_bp)

    from app.routes.friends import bp as friends_bp
    app.register_blueprint(friends_bp)

    from app.routes.events import bp as events_bp
    app.register_blueprint(events_bp)

    from app.routes.preferences import bp as groups_bp
    app.register_blueprint(groups_bp)
    
    from app.routes.activities import bp as activities_bp
    app.register_blueprint(activities_bp)

    from app.routes.settings import bp as settings_bp
    app.register_blueprint(settings_bp)
    
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp)
    
    from app.routes.google_auth import bp as google_auth_bp
    app.register_blueprint(google_auth_bp)

    return app

from app import models
