import os
from datetime import timedelta
from dotenv import load_dotenv

# Ensure environment variables are loaded from .env
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv(os.path.join(_root_dir, '.env'))
load_dotenv(os.path.join(_backend_dir, '.env'))
load_dotenv()  # Fallback to current working directory

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'disaster-shield-ai-super-secret-key-1337')
    
    # Database Fallback: MySQL, PostgreSQL, or SQLite
    # PyMySQL connector is used for MySQL backend
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        # Fix SQLAlchemy dialect prefix for PostgreSQL (common on Render / Heroku)
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    if not database_url:
        # Check if local mysql is running and accessible
        # If not, default to sqlite
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'disaster_shield.db'))
        database_url = f'sqlite:///{db_path}'
        
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configs
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-token-disaster-shield-99')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_TOKEN_LOCATION = ['cookies', 'headers']
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    JWT_COOKIE_CSRF_PROTECT = False  # Enable in production
    
    # File Paths
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'reports'))
    
    # Services Configurations (e.g. Gemini API Key)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
