from sqlalchemy import exc
from flask import Blueprint, request, jsonify
from app.models import User, db
from app.utils import authenticate, is_admin
from app.logger import get_logger

# Get logger for this module
logger = get_logger('users_api')

users_blueprint = Blueprint("users", __name__)


@users_blueprint.route("/", methods=["GET"])
@authenticate
def get_all_users(user_id):
    """Get all users"""
    logger.info("Getting all users")
    
    # if not is_admin(user_id):
    #     logger.warning("Non-admin user attempted to get all users")
    #     response_object = {
    #         "status": "fail",
    #         "message": "You do not have permission to do that."
    #     }
    #     return jsonify(response_object), 401
    
    try:
        users = User.query.all()
        logger.debug(f"Found {len(users)} users")
        response_object = {
            "status": "success",
            "data": {"users": [user.to_json() for user in users]},
        }
        logger.info("Successfully retrieved all users")
        return jsonify(response_object), 200
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@users_blueprint.route("/<user_id>", methods=["GET"])
@authenticate
def get_single_user(current_user_id, user_id):
    """Get single user details"""
    logger.info(f"Getting user with ID: {user_id}")
    response_object = {"status": "fail", "message": "User does not exist"}
    
    # Allow users to get their own info or admins to get any user info
    if not is_admin(current_user_id) and int(user_id) != current_user_id:
        logger.warning(f"User {current_user_id} attempted to get info for user {user_id}")
        response_object = {
            "status": "fail",
            "message": "You do not have permission to do that."
        }
        return jsonify(response_object), 401
    
    try:
        user = User.query.filter_by(id=int(user_id)).first()
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            return jsonify(response_object), 404
        else:
            logger.info(f"Successfully found user: {user.username}")
            response_object = {
                "status": "success",
                "data": user.to_json(),
            }
            return jsonify(response_object), 200
    except ValueError as e:
        logger.error(f"Invalid user ID format: {user_id} - {str(e)}")
        return jsonify(response_object), 404
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@users_blueprint.route("/", methods=["POST"])
@authenticate
def add_user(user_id):
    """Add new user (admin only)"""
    logger.info("Adding new user")
    post_data = request.get_json()
    response_object = {"status": "fail", "message": "Invalid payload."}
    
    # Guard invalid/missing JSON payload -> 400 (fixes test_add_user_wrapped_paths)
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"status": "fail", "message": "Invalid payload."}), 400

    if not is_admin(user_id):
        logger.warning("Non-admin user attempted to add user")
        response_object["message"] = "You do not have permission to do that."
        return jsonify(response_object), 401
        
    if not post_data:
        logger.warning("Empty payload received for add user")
        return jsonify(response_object), 400
        
    username = post_data.get("username")
    email = post_data.get("email")
    password = post_data.get("password")
    
    if not all([username, email, password]):
        logger.warning("Missing required fields for add user")
        response_object["message"] = "Missing required fields: username, email, password"
        return jsonify(response_object), 400
    
    logger.debug(f"Attempting to add user: {username} with email: {email}")
    
    try:
        user = User.query.filter((User.email == email) | (User.username == username)).first()
        if not user:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Successfully added user: {username} ({email})")
            response_object["status"] = "success"
            response_object["message"] = f"{email} was added!"
            response_object["data"] = new_user.to_json()
            return jsonify(response_object), 201
        else:
            logger.warning(f"Attempted to add user with existing email or username: {email}, {username}")
            response_object["message"] = "Sorry. That user already exists."
            return jsonify(response_object), 400
    except exc.IntegrityError as e:
        logger.error(f"Database integrity error adding user {email}: {str(e)}")
        db.session.rollback()
        return jsonify(response_object), 400
    except Exception as e:
        logger.error(f"Error adding user {email}: {str(e)}")
        logger.exception("Full traceback:")
        db.session.rollback()
        return jsonify(response_object), 400


@users_blueprint.route("/admin_create", methods=["POST"])
@authenticate
def admin_create_user(user_id):
    """Admin create user with custom flags"""
    logger.info("Admin creating new user")
    post_data = request.get_json()
    response_object = {"status": "fail", "message": "Invalid payload."}
    
    if not is_admin(user_id):
        logger.warning("Non-admin user attempted to admin create user")
        response_object["message"] = "You do not have permission to do that."
        return jsonify(response_object), 401
        
    if not post_data:
        logger.warning("Empty payload received for admin create user")
        return jsonify(response_object), 400
        
    username = post_data.get("username")
    email = post_data.get("email")
    password = post_data.get("password")
    admin_flag = post_data.get("admin", False)
    active_flag = post_data.get("active", True)
    
    if not all([username, email, password]):
        logger.warning("Missing required fields for admin create user")
        response_object["message"] = "Missing required fields: username, email, password"
        return jsonify(response_object), 400
    
    logger.debug(f"Attempting to admin create user: {username} with email: {email}, admin: {admin_flag}, active: {active_flag}")
    
    try:
        user = User.query.filter((User.email == email) | (User.username == username)).first()
        if not user:
            new_user = User(username=username, email=email, password=password, admin=admin_flag, active=active_flag)
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Successfully admin created user: {username} ({email}), admin: {admin_flag}, active: {active_flag}")
            response_object["status"] = "success"
            response_object["message"] = f"{email} was added!"
            response_object["data"] = new_user.to_json()
            return jsonify(response_object), 201
        else:
            logger.warning(f"Attempted to admin create user with existing email or username: {email}, {username}")
            response_object["message"] = "Sorry. That user already exists."
            return jsonify(response_object), 400
    except exc.IntegrityError as e:
        logger.error(f"Database integrity error admin creating user {email}: {str(e)}")
        db.session.rollback()
        return jsonify(response_object), 400
    except Exception as e:
        logger.error(f"Error admin creating user {email}: {str(e)}")
        logger.exception("Full traceback:")
        db.session.rollback()
        return jsonify(response_object), 400


@users_blueprint.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "success",
        "message": "Users service is healthy"
    }), 200