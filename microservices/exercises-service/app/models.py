from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import JSON
from app.logger import get_logger
from app.constants import FULL_TRACEBACK_MSG

# Get logger for this module
logger = get_logger("models")

# Initialize extensions
db = SQLAlchemy()

class Exercise(db.Model):
    __tablename__ = "exercises"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.String, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    test_cases = db.Column(JSON, nullable=False)
    solutions = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, title, body, difficulty, test_cases, solutions):
        logger.debug(
            f"Creating Exercise: title={title}, body length={len(body)}, difficulty={difficulty}, test_cases count={len(test_cases) if test_cases else 0}"
        )
        self.title = title
        self.body = body
        self.difficulty = difficulty
        self.test_cases = test_cases
        self.solutions = solutions

    def to_json(self):
        logger.debug(f"Converting Exercise {self.id} to JSON")
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "difficulty": self.difficulty,
            "test_cases": self.test_cases,
            "solutions": self.solutions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    # New: nicer repr for debugging/testing
    def __repr__(self):
        return f"<Exercise id={getattr(self, 'id', None)} title={self.title!r} difficulty={self.difficulty}>"

    # New: helper to construct instance from dict (no DB side effects)
    @staticmethod
    def from_json(data):
        return Exercise(
            title=data.get("title", ""),
            body=data.get("body", ""),
            difficulty=data.get("difficulty", 0),
            test_cases=data.get("test_cases", []),
            solutions=data.get("solutions", []),
        )

    @classmethod
    def create_exercise(cls, title, body, difficulty, test_cases, solutions):
        """Create exercise with logging"""
        logger.info(f"Creating new exercise with title: {title}")

        try:
            exercise = cls(
                title=title,
                body=body,
                difficulty=difficulty,
                test_cases=test_cases,
                solutions=solutions,
            )
            db.session.add(exercise)
            db.session.commit()
            logger.info(f"Exercise {exercise.id} created successfully")
            return exercise
        except Exception as e:
            logger.error(f"Failed to create exercise: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            db.session.rollback()
            raise e

    def update_exercise(self, **kwargs):
        """Update exercise with logging"""
        logger.info(f"Updating exercise {self.id}")

        try:
            for key, value in kwargs.items():
                if hasattr(self, key) and value is not None:
                    setattr(self, key, value)
                    logger.debug(f"Updated {key} for exercise {self.id}")

            db.session.commit()
            logger.info(f"Exercise {self.id} updated successfully")
        except Exception as e:
            logger.error(f"Failed to update exercise {self.id}: {str(e)}")
            logger.exception(FULL_TRACEBACK_MSG)
            db.session.rollback()
            raise e