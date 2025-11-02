from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import text
from app.config import get_config
from app.models import db
from app.logger import setup_logger
from app.api.scores import scores_blueprint
from app.api import scores as scores_api

def create_app():
    # Setup logging first
    setup_logger()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(get_config())
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(scores_blueprint, url_prefix="/api/scores")

    # Alias v1 cho các route cần thiết trong test
    @app.route("/api/v1/scores/progress/<int:user_id>", methods=["GET"])
    def scores_progress_v1_int(user_id: int):
        # Giữ route cũ cho số dương
        return scores_api.get_user_progress(user_id)

    # Bổ sung alias chấp nhận cả số âm bằng string converter
    @app.route("/api/v1/scores/progress/<user_id>", methods=["GET"])
    def scores_progress_v1(user_id: str):
        try:
            uid = int(user_id)
        except ValueError:
            return jsonify({"status": "fail", "message": "invalid user_id"}), 400
        return scores_api.get_user_progress(uid)

    @app.route("/api/v1/scores/submit", methods=["POST"])
    def scores_submit_v1():
        return scores_api.submit_score()

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return {"status": "healthy", "service": "scores-service", "database": "connected"}, 200
        except Exception as e:
            return {"status": "unhealthy", "service": "scores-service", "database": "disconnected", "error": str(e)}, 503
    
    # Create tables with error handling
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Database connection failed: {e}")
            # Don't fail app startup if DB is not ready yet
    
    return app

# Module-level app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)