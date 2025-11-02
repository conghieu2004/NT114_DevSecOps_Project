from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import text
import os
from flask import request, abort
from app.config import get_config
from app.models import db
from app.logger import setup_logger
from app.api.exercises import exercises_blueprint

def create_app():
    # Setup logging first
    setup_logger()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(get_config())
    
    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    # Restrict CORS: only allow explicit origins, headers, and methods
    origins_env = os.environ.get("CORS_ORIGINS")
    allowed_origins = (
        [o.strip() for o in origins_env.split(",") if o.strip()]
        if origins_env
        else ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"]
    )
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "supports_credentials": False,
                "allow_headers": ["Authorization", "Content-Type"],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            }
        },
    )
    # CSRF guard for stateless API:
    # - Chỉ áp dụng cho phương thức "unsafe"
    # - Nếu có Origin header, phải thuộc allowed_origins
    # - Yêu cầu Authorization header cho API thay đổi trạng thái (trừ các endpoint được whitelist)
    app.config.setdefault("AUTH_OPTIONAL_PATHS", {"/api/exercises/validate_code"})
    @app.before_request
    def _csrf_like_guard_for_api():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and origin not in allowed_origins:
                return abort(403)
            # Chỉ yêu cầu auth với các API thay đổi trạng thái, ngoại trừ whitelist
            if (
                request.path.startswith("/api/")
                and request.path not in app.config["AUTH_OPTIONAL_PATHS"]
                and not request.headers.get("Authorization")
            ):
                return abort(401)
    
    # Register blueprints
    app.register_blueprint(exercises_blueprint, url_prefix="/api/exercises")
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return {"status": "healthy", "service": "exercises-service", "database": "connected"}, 200
        except Exception as e:
            return {"status": "unhealthy", "service": "exercises-service", "database": "disconnected", "error": str(e)}, 503
    
    # Create tables with error handling
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Database connection failed: {e}")
            # Don't fail app startup if DB is not ready yet
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)