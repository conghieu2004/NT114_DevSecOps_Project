import requests
import os
from functools import wraps
from flask import request, jsonify
from app.logger import get_logger

# Get logger for this module
logger = get_logger("exercises_utils")

# Mặc định dùng HTTPS; có thể override qua env trong môi trường dev/test
USER_MANAGEMENT_SERVICE_URL = os.environ.get('USER_MANAGEMENT_SERVICE_URL', 'https://host.docker.internal:5001')

def _get_user_service_url():
    """Trả về URL user-service; nếu production mà dùng http -> tự động chuyển sang https."""
    url = os.environ.get('USER_MANAGEMENT_SERVICE_URL', USER_MANAGEMENT_SERVICE_URL)
    if os.environ.get("FLASK_ENV") == "production" and url.startswith("http://"):
        logger.warning("Insecure USER_MANAGEMENT_SERVICE_URL in production; switching to HTTPS")
        url = "https://" + url[len("http://"):]
    return url

def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Authentication check for endpoint: {f.__name__}")

        response_object = {
            "status": "fail",
            "message": "Something went wrong. Please contact us.",
        }
        code = 401

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header for {f.__name__}")
            response_object["message"] = "Provide a valid auth token."
            code = 403
            return jsonify(response_object), code

        try:
            auth_token = auth_header.split(" ")[1]
            logger.debug("Validating auth token")
        except IndexError:
            logger.warning("Invalid Authorization header format")
            response_object["message"] = "Invalid token format."
            return jsonify(response_object), code

        user_data = verify_token_with_user_service(auth_token)
        if not user_data:
            logger.warning("Invalid or expired auth token")
            response_object["message"] = "Invalid token. Please log in again."
            return jsonify(response_object), code

        logger.debug(f"Authentication successful for user: {user_data.get('username')}")
        return f(user_data, *args, **kwargs)

    return decorated_function

def verify_token_with_user_service(token):
    """Call user-management service to verify token and return user data or None."""
    try:
        url = f"{_get_user_service_url()}/verify"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code != 200:
            logger.warning(f"verify_token_with_user_service: non-200 {resp.status_code}")
            return None
        body = resp.json() or {}
        # expect {"status":"success","data":{...}}
        if isinstance(body, dict) and body.get("status") == "success" and isinstance(body.get("data"), dict):
            return body.get("data")
        return None
    except Exception as e:
        logger.exception(f"Error verifying token: {e}")
        return None

def is_admin(user_data):
    """Return True if user_data indicates admin, else False."""
    try:
        return bool(user_data and user_data.get("admin") is True)
    except Exception:
        return False