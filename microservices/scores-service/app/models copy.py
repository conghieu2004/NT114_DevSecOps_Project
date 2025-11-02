from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import JSON
from app.logger import get_logger

# Get logger for this module
logger = get_logger("models")

# Initialize extensions
db = SQLAlchemy()

class Score(db.Model):
    __tablename__ = "scores"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    exercise_id = db.Column(db.Integer, nullable=False)
    answer = db.Column(db.Text, nullable=True)
    results = db.Column(JSON, nullable=True)
    user_results = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, user_id, exercise_id, answer=None, results=None, user_results=None):
        logger.debug(
            f"Creating Score: user_id={user_id}, exercise_id={exercise_id}, answer length={len(answer) if answer else None}, results={results}, user_results={user_results}"
        )
        self.user_id = user_id
        self.exercise_id = exercise_id
        self.answer = answer
        self.results = results
        self.user_results = user_results

    def to_json(self):
        """Convert entity to JSON with normalized results and user_results."""
        logger.debug(f"Converting Score {self.id} to JSON")
        results_array, all_correct = self._normalize_results(self.results)
        user_results_array = self._normalize_user_results(self.user_results)

        return {
            "id": self.id,
            "user_id": self.user_id,
            "exercise_id": self.exercise_id,
            "answer": self.answer,
            "results": results_array,
            "user_results": user_results_array,
            "all_correct": all_correct,
            "created_at": self._iso_or_none(self.created_at),
            "updated_at": self._iso_or_none(self.updated_at),
        }

    @staticmethod
    def _normalize_results(results):
        """Return (results_array, all_correct) with the same semantics as before."""
        if not results:
            return [], False

        # Dict case: {"passed": bool} or {"test_results": [bool, ...]} or other dicts
        if isinstance(results, dict):
            if "passed" in results:
                passed = bool(results["passed"])
                return [passed], passed
            test_results = results.get("test_results")
            if isinstance(test_results, list):
                arr = test_results
            else:
                # Default fallback – assume single test passed
                arr = [True]
            return arr, (all(arr) if arr else False)

        # List case: already an array of booleans
        if isinstance(results, list):
            arr = results
            return arr, (all(arr) if arr else False)

        # Scalar case: coerce to boolean
        val = bool(results)
        return [val], val

    @staticmethod
    def _normalize_user_results(user_results):
        """Normalize user_results to list[str]."""
        if not user_results:
            return []
        if isinstance(user_results, dict):
            return [str(v) for v in user_results.values()]
        if isinstance(user_results, list):
            return [str(item) for item in user_results]
        return [str(user_results)]

    @staticmethod
    def _iso_or_none(dt):
        return dt.isoformat() if dt else None

    @classmethod
    def create_score(cls, user_id, exercise_id, answer=None, results=None, user_results=None):
        """Create score with logging"""
        logger.info(f"Creating new score for user {user_id}, exercise {exercise_id}")

        try:
            score = cls(
                user_id=user_id,
                exercise_id=exercise_id,
                answer=answer,
                results=results,
                user_results=user_results,
            )
            db.session.add(score)
            db.session.commit()
            logger.info(f"Score {score.id} created successfully")
            return score
        except Exception as e:
            logger.error(f"Failed to create score: {str(e)}")
            logger.exception("Full traceback:")
            db.session.rollback()
            raise e

    def update_score(self, answer=None, results=None, user_results=None):
        """Update score with logging"""
        logger.info(
            f"Updating score {self.id} for user {self.user_id}, exercise {self.exercise_id}"
        )
        
        try:
            if answer is not None:
                self.answer = answer
            if results is not None:
                self.results = results
            if user_results is not None:
                self.user_results = user_results

            db.session.commit()
            logger.info(f"Score {self.id} updated successfully")
        except Exception as e:
            logger.error(f"Failed to update score {self.id}: {str(e)}")
            logger.exception("Full traceback:")
            db.session.rollback()
            raise e