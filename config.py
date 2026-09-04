import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hospital-mgmt-system-secret-key-123!@#')
    DB_CONFIG = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", ""),
        "port": int(os.environ.get("DB_PORT", ))
    }
    
    # Multi-Provider AI Service Configuration
    AI_PROVIDER = os.environ.get('AI_PROVIDER', '')  # 'groq', 'openai', 'google', or 'mock'
    AI_API_KEY = os.environ.get('AI_API_KEY', '')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', os.environ.get('AI_API_KEY', ''))
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    AI_MODEL = os.environ.get('AI_MODEL', '')
    
    # Upload Configurations
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
