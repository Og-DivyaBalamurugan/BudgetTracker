
from flask import Flask
from flask_mysqldb import MySQL
from flask_login import LoginManager
from config import Config

# Create MySQL and LoginManager objects
# We create them here but connect them to the app later
mysql = MySQL()
login_manager = LoginManager()

def create_app():
    # Create the Flask application
    app = Flask(__name__)
    
    # Load all settings from config.py
    app.config.from_object(Config)
    
    # Connect MySQL to the app
    mysql.init_app(app)
    
    # Connect LoginManager to the app
    login_manager.init_app(app)
    
    # Tell LoginManager which page to show
    # when a user tries to access a page without logging in
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    # Blueprints are like sections of your app
    # Each blueprint handles one area - auth, dashboard etc
    from app.auth import auth
    from app.dashboard import dashboard
    from app.transactions import transactions
    from app.budget import budget

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(transactions)
    app.register_blueprint(budget)
    
    
    return app