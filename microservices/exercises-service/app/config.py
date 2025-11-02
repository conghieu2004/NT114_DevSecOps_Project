import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exercises-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        DB_USER = os.environ.get('DB_USER', 'postgres')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_PORT = os.environ.get('DB_PORT', '5432')
        DB_NAME = os.environ.get('DB_NAME', 'exercises_db')
        SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"]

def get_config():
    return Config

# New: small helpers to fully cover env-driven branches in tests
def compute_database_uri(env=None):
    """Return SQLAlchemy URI from environment mapping similar to Config logic."""
    env = env or os.environ
    if env.get("DATABASE_URL"):
        return env["DATABASE_URL"]
    user = env.get("DB_USER", "postgres")
    pwd = env.get("DB_PASSWORD", "postgres")
    host = env.get("DB_HOST", "localhost")
    port = env.get("DB_PORT", "5432")
    name = env.get("DB_NAME", "exercises_db")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"

def parse_cors_origins(env=None):
    """Parse CORS_ORIGINS from env comma-separated string if present, else default Config list."""
    env = env or os.environ
    raw = env.get("CORS_ORIGINS")
    if not raw:
        return list(Config.CORS_ORIGINS)
    return [x.strip() for x in raw.split(",") if x.strip()]

def get_bool_env(key, default=False, env=None):
    """Parse boolean-like env values: '1', 'true', 'yes' => True; '0','false','no' => False."""
    env = env or os.environ
    val = env.get(key)
    if val is None:
        return bool(default)
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return bool(default)