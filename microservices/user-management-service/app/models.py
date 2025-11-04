from datetime import datetime, timezone, timedelta
import jwt
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from app.logger import get_logger

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()

# Get logger for this module
logger = get_logger("models")

# Constants
FULL_TRACEBACK_MSG = "Full traceback:"
INVALID_TOKEN_MSG = "Invalid token. Please log in again."


class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, username, email, password, admin=False, active=True):
        logger.debug(f"Creating User: username={username}, email={email}")
        self.username = username
        self.email = email
        self.admin = admin
        self.active = active

        try:
            # Hash password
            logger.debug("Hashing user password")
            self.password = bcrypt.generate_password_hash(
                password, current_app.config.get("BCRYPT_LOG_ROUNDS")
            ).decode()
            logger.debug("Password hashed successfully")
        except Exception as e:
            logger.error(f"Failed to hash password for user {username}: {str(e)}")
            raise e

    def to_json(self):
        logger.debug(f"Converting User {self.id} ({self.username}) to JSON")
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "active": self.active,
            "admin": self.admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def encode_auth_token(self, user_id):
        """Generates the auth token"""
        logger.debug(f"Encoding auth token for user_id: {user_id} (type: {type(user_id)})")

        try:
            expiration_days = current_app.config.get("TOKEN_EXPIRATION_DAYS")
            expiration_seconds = current_app.config.get("TOKEN_EXPIRATION_SECONDS")

            payload = {
                "exp": datetime.now(timezone.utc)
                + timedelta(days=expiration_days, seconds=expiration_seconds),
                "iat": datetime.now(timezone.utc),
                "sub": str(user_id),  # Convert to string for JWT compatibility
            }

            token = jwt.encode(
                payload, current_app.config.get("SECRET_KEY"), algorithm="HS256"
            )

            logger.debug(f"Auth token encoded successfully for user_id: {user_id}")
            logger.debug(f"Token expires in {expiration_days} days and {expiration_seconds} seconds")
            return token

        except Exception as e:
            logger.error(f"Failed to encode auth token for user_id {user_id}: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """Decodes the auth token"""
        logger.debug("Decoding auth token")

        try:
            payload = jwt.decode(
                auth_token,
                current_app.config.get("SECRET_KEY"),
                algorithms=["HS256"],
            )
            user_id_str = payload["sub"]
            logger.debug(f"Token payload sub: {user_id_str} (type: {type(user_id_str)})")

            # Convert string back to integer
            user_id = int(user_id_str)
            logger.debug(f"Auth token decoded successfully for user_id: {user_id} (type: {type(user_id)})")
            return user_id

        except jwt.ExpiredSignatureError:
            logger.warning("Auth token expired")
            return "Signature expired. Please log in again."

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid auth token: {str(e)}")
            return INVALID_TOKEN_MSG

        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid user_id format in token: {str(e)}")
            return INVALID_TOKEN_MSG

        except Exception as e:
            logger.error(f"Unexpected error decoding auth token: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            return INVALID_TOKEN_MSG

    def deactivate_user(self):
        """Deactivate user with logging"""
        logger.info(f"Deactivating user {self.username} ({self.email})")

        try:
            self.active = False
            db.session.commit()
            logger.info(f"User {self.username} deactivated successfully")
        except Exception as e:
            logger.error(f"Failed to deactivate user {self.username}: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            db.session.rollback()
            raise e

    def reactivate_user(self):
        """Reactivate user with logging"""
        logger.info(f"Reactivating user {self.username} ({self.email})")

        try:
            self.active = True
            db.session.commit()
            logger.info(f"User {self.username} reactivated successfully")
        except Exception as e:
            logger.error(f"Failed to reactivate user {self.username}: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            db.session.rollback()
            raise e