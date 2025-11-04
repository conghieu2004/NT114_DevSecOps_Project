from flask import Blueprint, jsonify, request
from sqlalchemy import exc, or_
from app.models import User, db, bcrypt
from app.utils import authenticate, admin_required
from app.logger import get_logger

# Get logger for this module
logger = get_logger('auth_api')

# Constants
FULL_TRACEBACK_MSG = "Full traceback:"

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/register", methods=["POST"])
def register_user():
    logger.info("User registration attempt")
    
    # get post data
    post_data = request.get_json()
    response_object = {"status": "fail", "message": "Invalid payload."}
    
    if not post_data:
        logger.warning("Registration attempt with empty payload")
        return jsonify(response_object), 400
        
    username = post_data.get("username")
    email = post_data.get("email")
    password = post_data.get("password")
    
    # Validate required fields
    if not all([username, email, password]):
        logger.warning(f"Registration attempt with missing fields - username: {bool(username)}, email: {bool(email)}, password: {bool(password)}")
        return jsonify(response_object), 400
    
    logger.debug(f"Registration attempt for username: {username}, email: {email}")
    
    try:
        # check for existing user
        user = User.query.filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if not user:
            # add new user to db
            logger.info(f"Creating new user: {username} ({email})")
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            
            # generate auth token
            auth_token = new_user.encode_auth_token(new_user.id)
            logger.info(f"User {username} registered successfully with ID: {new_user.id}")
            
            response_object["status"] = "success"
            response_object["message"] = "Successfully registered."
            response_object["auth_token"] = auth_token
            response_object["data"] = new_user.to_json()
            return jsonify(response_object), 201
        else:
            logger.warning(f"Registration failed - user already exists: username={username}, email={email}")
            response_object["message"] = "Sorry. That user already exists."
            return jsonify(response_object), 400
            
    # handler errors
    except (exc.IntegrityError, ValueError) as e:
        logger.error(f"Database error during registration for {email}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        db.session.rollback()
        return jsonify(response_object), 400
    except Exception as e:
        logger.error(f"Unexpected error during registration for {email}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        db.session.rollback()
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@auth_blueprint.route("/login", methods=["POST"])
def login_user():
    logger.info("User login attempt")
    
    # get post data
    post_data = request.get_json()
    response_object = {"status": "fail", "message": "Invalid payload."}
    
    if not post_data:
        logger.warning("Login attempt with empty payload")
        return jsonify(response_object), 400
        
    email = post_data.get("email")
    password = post_data.get("password")
    
    if not all([email, password]):
        logger.warning(f"Login attempt with missing fields - email: {bool(email)}, password: {bool(password)}")
        return jsonify(response_object), 400
    
    logger.debug(f"Login attempt for email: {email}")
    
    try:
        # fetch the user data
        user = User.query.filter_by(email=email).first()
        
        if user:
            if not user.active:
                logger.warning(f"Login attempt for inactive user: {email}")
                response_object["message"] = "User account is inactive."
                return jsonify(response_object), 401
                
            if bcrypt.check_password_hash(user.password, password):
                auth_token = user.encode_auth_token(user.id)
                if auth_token:
                    logger.info(f"User {user.username} ({email}) logged in successfully")
                    response_object["status"] = "success"
                    response_object["message"] = "Successfully logged in."
                    response_object["auth_token"] = auth_token
                    response_object["data"] = user.to_json()
                    return jsonify(response_object), 200
                else:
                    logger.error(f"Failed to generate auth token for user: {email}")
                    response_object["message"] = "Authentication failed."
                    return jsonify(response_object), 500
            else:
                logger.warning(f"Invalid password for user: {email}")
                response_object["message"] = "Invalid credentials."
                return jsonify(response_object), 401
        else:
            logger.warning(f"Login attempt for non-existent user: {email}")
            response_object["message"] = "User does not exist."
            return jsonify(response_object), 404
            
    except Exception as e:
        logger.error(f"Error during login for {email}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        response_object["message"] = "Try again."
        return jsonify(response_object), 500


@auth_blueprint.route("/logout", methods=["GET"])
@authenticate
def logout_user(resp):
    logger.info(f"User logout - user_id: {resp}")
    
    try:
        # Get user info for logging
        user = User.query.filter_by(id=resp).first()
        if user:
            logger.info(f"User {user.username} ({user.email}) logged out successfully")
        else:
            logger.warning(f"Logout for unknown user_id: {resp}")
            
        response_object = {"status": "success", "message": "Successfully logged out."}
        return jsonify(response_object), 200
        
    except Exception as e:
        logger.error(f"Error during logout for user_id {resp}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        response_object = {"status": "success", "message": "Successfully logged out."}
        return jsonify(response_object), 200  # Still return success for logout


@auth_blueprint.route("/status", methods=["GET"])
@authenticate
def get_user_status(resp):
    logger.debug(f"Getting user status for user_id: {resp}")
    
    try:
        user = User.query.filter_by(id=resp).first()
        
        if not user:
            logger.error(f"User status requested for non-existent user_id: {resp}")
            response_object = {
                "status": "fail",
                "message": "User not found"
            }
            return jsonify(response_object), 404
            
        if not user.active:
            logger.warning(f"Status requested for inactive user: {user.username} ({user.email})")
            response_object = {
                "status": "fail",
                "message": "User account is inactive"
            }
            return jsonify(response_object), 401
            
        logger.debug(f"Successfully retrieved status for user: {user.username}")
        response_object = {
            "status": "success",
            "message": "success",
            "data": user.to_json(),
        }
        return jsonify(response_object), 200
        
    except Exception as e:
        logger.error(f"Error getting user status for user_id {resp}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        response_object = {
            "status": "error",
            "message": "Internal server error"
        }
        return jsonify(response_object), 500

@auth_blueprint.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "success",
        "message": "Auth service is healthy"
    }), 200