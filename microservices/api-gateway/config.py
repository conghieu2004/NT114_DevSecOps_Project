import os

class Config:
    # API Gateway Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Service URLs
    USER_MANAGEMENT_SERVICE_URL = os.environ.get('USER_SERVICE_URL', os.environ.get('USER_MANAGEMENT_SERVICE_URL', 'http://localhost:5001'))
    EXERCISES_SERVICE_URL = os.environ.get('EXERCISES_SERVICE_URL', 'http://localhost:5002')
    SCORES_SERVICE_URL = os.environ.get('SCORES_SERVICE_URL', 'http://localhost:5003')
    
    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://localhost:31184", "http://127.0.0.1:31184"]
    
    # Rate limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '100'))
    
    # Request timeout (seconds)
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))