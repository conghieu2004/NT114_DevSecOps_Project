from flask import Flask, request, jsonify, g
from flask_cors import CORS
import logging
import sys
from config import Config
from services import UserManagementServiceClient, ExercisesServiceClient, ScoresServiceClient
from middleware import AuthMiddleware, RequestLoggingMiddleware, require_auth, require_admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

INVALID_PAYLOAD_MSG = "Invalid payload"

def get_json_or_fail():
    if not request.is_json:
        return None, jsonify({"status": "fail", "message": INVALID_PAYLOAD_MSG}), 400
    data = request.get_json(silent=True)
    if data is None:
        return None, jsonify({"status": "fail", "message": INVALID_PAYLOAD_MSG}), 400
    return data, None, None

def _check_service_health(client):
    try:
        _, status_code = client.health_check()
    except Exception:
        status_code = 503
    return {
        "status": "healthy" if status_code == 200 else "unhealthy",
        "response_code": status_code
    }

def register_middlewares(app):
    @app.before_request
    def before_request():
        RequestLoggingMiddleware.log_request()
    @app.after_request
    def after_request(response):
        return RequestLoggingMiddleware.log_response(response)

def register_error_handlers(app, logger):
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"status": "fail", "message": "Endpoint not found"}), 404
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"status": "fail", "message": "Method not allowed"}), 405
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

def register_health_route(app, user_management_client, exercises_client, scores_client):
    @app.route('/health', methods=['GET'])
    def health_check():
        statuses = [
            _check_service_health(user_management_client),
            _check_service_health(exercises_client),
            _check_service_health(scores_client)
        ]
        overall_status = 200 if all(s["response_code"] == 200 for s in statuses) else 503
        gateway_status = {
            "status": "healthy" if overall_status == 200 else "unhealthy",
            "services": {
                "user_management_service": statuses[0],
                "exercises_service": statuses[1],
                "scores_service": statuses[2]
            }
        }
        return jsonify(gateway_status), overall_status

def register_auth_routes(app, user_management_client, auth_middleware):
    @app.route('/auth/register', methods=['POST'])
    def register():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        response, status_code = user_management_client.register(data)
        return jsonify(response), status_code

    @app.route('/auth/login', methods=['POST'])
    def login():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        response, status_code = user_management_client.login(data)
        return jsonify(response), status_code

    @app.route('/auth/logout', methods=['GET'])
    @require_auth(auth_middleware)
    def logout():
        headers = dict(request.headers)
        response, status_code = user_management_client.logout(headers)
        return jsonify(response), status_code

    @app.route('/auth/status', methods=['GET'])
    @require_auth(auth_middleware)
    def get_user_status():
        headers = dict(request.headers)
        response, status_code = user_management_client.get_user_status(headers)
        return jsonify(response), status_code

def register_users_routes(app, user_management_client, auth_middleware):
    @app.route('/users/', methods=['GET'])
    @require_auth(auth_middleware)
    def get_all_users():
        headers = dict(request.headers)
        response, status_code = user_management_client.get_all_users(headers)
        return jsonify(response), status_code

    @app.route('/users/<int:user_id>', methods=['GET'])
    @require_auth(auth_middleware)
    def get_single_user(user_id):
        headers = dict(request.headers)
        response, status_code = user_management_client.get_single_user(user_id, headers)
        return jsonify(response), status_code

    @app.route('/users/', methods=['POST'])
    @require_auth(auth_middleware)
    def add_user():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = user_management_client.add_user(data, headers)
        return jsonify(response), status_code

    @app.route('/users/admin_create', methods=['POST'])
    @require_auth(auth_middleware)
    def admin_create_user():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = user_management_client.admin_create_user(data, headers)
        return jsonify(response), status_code

def register_exercises_routes(app, exercises_client, auth_middleware):
    @app.route('/exercises/', methods=['GET'])
    @require_auth(auth_middleware)
    def get_all_exercises():
        headers = dict(request.headers)
        response, status_code = exercises_client.get_all_exercises(headers)
        return jsonify(response), status_code

    @app.route('/exercises/<int:exercise_id>', methods=['GET'])
    @require_auth(auth_middleware)
    def get_single_exercise(exercise_id):
        headers = dict(request.headers)
        response, status_code = exercises_client.get_single_exercise(exercise_id, headers)
        return jsonify(response), status_code

    @app.route('/exercises/', methods=['POST'])
    @require_admin(auth_middleware)
    def create_exercise():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = exercises_client.create_exercise(data, headers)
        return jsonify(response), status_code

    @app.route('/exercises/<int:exercise_id>', methods=['PUT'])
    @require_admin(auth_middleware)
    def update_exercise(exercise_id):
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = exercises_client.update_exercise(exercise_id, data, headers)
        return jsonify(response), status_code

    @app.route('/exercises/<int:exercise_id>', methods=['DELETE'])
    @require_admin(auth_middleware)
    def delete_exercise(exercise_id):
        headers = dict(request.headers)
        response, status_code = exercises_client.delete_exercise(exercise_id, headers)
        return jsonify(response), status_code

    @app.route('/exercises/validate_code', methods=['POST'])
    @require_auth(auth_middleware)
    def validate_code():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = exercises_client.validate_code(data, headers)
        return jsonify(response), status_code

def register_scores_routes(app, scores_client, auth_middleware):
    @app.route('/scores/', methods=['GET'])
    @require_auth(auth_middleware)
    def get_all_scores():
        headers = dict(request.headers)
        response, status_code = scores_client.get_all_scores(headers)
        return jsonify(response), status_code

    @app.route('/scores/user', methods=['GET'])
    @require_auth(auth_middleware)
    def get_scores_by_user():
        headers = dict(request.headers)
        response, status_code = scores_client.get_scores_by_user(headers)
        return jsonify(response), status_code

    @app.route('/scores/user/<int:score_id>', methods=['GET'])
    @require_auth(auth_middleware)
    def get_single_score_by_user(score_id):
        headers = dict(request.headers)
        response, status_code = scores_client.get_single_score_by_user(score_id, headers)
        return jsonify(response), status_code

    @app.route('/scores/', methods=['POST'])
    @require_auth(auth_middleware)
    def create_score():
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = scores_client.create_score(data, headers)
        return jsonify(response), status_code

    @app.route('/scores/<int:exercise_id>', methods=['PUT'])
    @require_auth(auth_middleware)
    def update_score(exercise_id):
        data, error_response, error_code = get_json_or_fail()
        if error_response:
            return error_response, error_code
        headers = dict(request.headers)
        response, status_code = scores_client.update_score(exercise_id, data, headers)
        return jsonify(response), status_code

def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(Config)
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         supports_credentials=True)
    user_management_client = UserManagementServiceClient(
        app.config['USER_MANAGEMENT_SERVICE_URL'], 
        timeout=app.config.get('REQUEST_TIMEOUT', 30)
    )
    exercises_client = ExercisesServiceClient(
        app.config['EXERCISES_SERVICE_URL'],
        timeout=app.config.get('REQUEST_TIMEOUT', 30)
    )
    scores_client = ScoresServiceClient(
        app.config['SCORES_SERVICE_URL'],
        timeout=app.config.get('REQUEST_TIMEOUT', 30)
    )
    auth_middleware = AuthMiddleware(user_management_client)
    register_middlewares(app)
    register_error_handlers(app, logger)
    register_health_route(app, user_management_client, exercises_client, scores_client)
    register_auth_routes(app, user_management_client, auth_middleware)
    register_users_routes(app, user_management_client, auth_middleware)
    register_exercises_routes(app, exercises_client, auth_middleware)
    register_scores_routes(app, scores_client, auth_middleware)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)