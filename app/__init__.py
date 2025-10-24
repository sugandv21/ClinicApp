import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


def create_app():
    load_dotenv()

    app = Flask(__name__, instance_relative_config=False)

    # SECURITY
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')

    # DB (SQLite in project root)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sqlite.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Mail (reuses Django-like env keys provided)
    app.config['MAIL_SERVER'] = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('EMAIL_HOST_USER')
    app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_HOST_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('DEFAULT_FROM_EMAIL', os.getenv('EMAIL_HOST_USER'))

    # NEW: allow disabling outbound mail without code changes
    app.config['MAIL_SUPPRESS_SEND'] = os.getenv('MAIL_SUPPRESS_SEND', 'False') == 'True'

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'

    # Blueprints
    from .auth import auth_bp
    from .views import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Friendly 500 so users don't see a raw error page
    @app.errorhandler(500)
    def _error_500(e):
        print("GLOBAL 500:", repr(e))
        # Reuse base layout with a simple message
        return render_template('base.html', _message="Server error. Please try again."), 500

    # Create DB tables on first run
    with app.app_context():
        from . import models  # noqa
        db.create_all()

    return app
