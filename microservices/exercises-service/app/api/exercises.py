from sqlalchemy import exc
from flask import Blueprint, jsonify, request
from app.models import Exercise, db
from app.utils import authenticate, is_admin
from app.logger import get_logger
from app.constants import (
    FULL_TRACEBACK_MSG,
    INTERNAL_SERVER_ERROR,
    INVALID_PAYLOAD_ERROR,
)

# Get logger for this module
logger = get_logger('exercises_api')

exercises_blueprint = Blueprint("exercises", __name__)

@exercises_blueprint.route("/ping", methods=["GET"])
def ping_pong():
    return jsonify({"status": "success", "message": "pong!"})

@exercises_blueprint.route("/", methods=["GET"])
def get_all_exercises():
    """Get all exercises"""
    logger.info("Getting all exercises")
    try:
        exercises = Exercise.query.all()
        logger.debug(f"Found {len(exercises)} exercises")
        response_object = {
            "status": "success",
            "data": {"exercises": [ex.to_json() for ex in exercises]},
        }
        logger.info("Successfully retrieved all exercises")
        return jsonify(response_object), 200
    except Exception as e:
        logger.error(f"Error getting all exercises: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        return jsonify({"status": "error", "message": INTERNAL_SERVER_ERROR}), 500

@exercises_blueprint.route("/<exercise_id>", methods=["GET"])
def get_single_exercise(exercise_id):
    """Get single exercise"""
    logger.info(f"Getting exercise with ID: {exercise_id}")
    response_object = {"status": "fail", "message": "Exercise does not exist"}
    
    try:
        exercise = Exercise.query.filter_by(id=int(exercise_id)).first()
        if not exercise:
            logger.warning(f"Exercise with ID {exercise_id} not found")
            return jsonify(response_object), 404
        else:
            logger.info(f"Successfully found exercise: {exercise.title}")
            response_object = {"status": "success", "data": exercise.to_json()}
            return jsonify(response_object), 200
    except ValueError as e:
        logger.error(f"Invalid exercise ID format: {exercise_id} - {str(e)}")
        return jsonify(response_object), 404
    except Exception as e:
        logger.error(f"Error getting exercise {exercise_id}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        return jsonify({"status": "error", "message": INTERNAL_SERVER_ERROR}), 500

@exercises_blueprint.route("/validate_code", methods=["POST"])
def validate_code():
    """Validate code against exercise test cases"""
    logger.info("Code validation request")
    
    data = request.get_json()
    if not data or "answer" not in data or "exercise_id" not in data:
        logger.warning("Invalid validation request - missing data")
        return jsonify({"status": "fail", "message": "Invalid data!"}), 400

    answer = data["answer"]
    exercise_id = data["exercise_id"]
    
    logger.debug(f"Validating code for exercise {exercise_id}")

    try:
        exercise = Exercise.query.get(exercise_id)
        if not exercise:
            logger.warning(f"Exercise {exercise_id} not found for validation")
            return jsonify({"status": "fail", "message": "Exercise not found!"}), 404

        tests = exercise.test_cases
        solutions = exercise.solutions

        if len(tests) != len(solutions):
            logger.error(f"Tests and solutions length mismatch for exercise {exercise_id}")
            return jsonify({
                "status": "fail", 
                "message": "Tests and solutions length mismatch!"
            }), 500

        results = []
        user_results = []

        namespace = {}
        try:
            exec(answer, namespace)
        except Exception as e:
            logger.warning(f"Code compilation failed for exercise {exercise_id}: {str(e)}")
            return jsonify({
                "status": "fail",
                "message": f"Code compilation failed: {str(e)}!"
            }), 400

        for test, sol in zip(tests, solutions):
            try:
                # Capture stdout to get print() output
                import io
                import sys
                captured_output = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = captured_output

                try:
                    res = eval(test, namespace)
                    output = captured_output.getvalue().strip()

                    # Use output if available, otherwise use return value
                    user_str = output if output else str(res)
                    user_results.append(user_str)
                    results.append(user_str == sol)
                finally:
                    sys.stdout = old_stdout
            except Exception as e:
                user_results.append(f"Error: {str(e)}")
                results.append(False)

        all_correct = all(results)
        logger.info(f"Code validation completed for exercise {exercise_id}: {all_correct}")
        
        return jsonify({
            "status": "success",
            "results": results,
            "user_results": user_results,
            "all_correct": all_correct,
        }), 200
        
    except Exception as e:
        logger.error(f"Error during code validation: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        return jsonify({"status": "error", "message": INTERNAL_SERVER_ERROR}), 500

@exercises_blueprint.route("/", methods=["POST"])
@authenticate
def add_exercise(user_data):
    """Add exercise (admin only)"""
    logger.info("Adding new exercise")
    
    if not is_admin(user_data):
        logger.warning("Non-admin user attempted to add exercise")
        response_object = {
            "status": "fail",
            "message": "You do not have permission to do that."
        }
        return jsonify(response_object), 401
    
    post_data = request.get_json()
    if not post_data:
        logger.warning("Empty payload received for add exercise")
        response_object = {"status": "fail", "message": INVALID_PAYLOAD_ERROR}
        return jsonify(response_object), 400
        
    title = post_data.get("title")
    body = post_data.get("body")
    difficulty = post_data.get("difficulty")
    test_cases = post_data.get("test_cases")
    solutions = post_data.get("solutions")
    
    if not all([title, body, difficulty is not None, test_cases, solutions]):
        logger.warning("Missing required fields for add exercise")
        response_object = {"status": "fail", "message": "Missing required fields"}
        return jsonify(response_object), 400
    
    logger.debug(f"Attempting to add exercise: {title}")
    
    try:
        exercise = Exercise(
            title=title,
            body=body,
            difficulty=difficulty,
            test_cases=test_cases,
            solutions=solutions,
        )
        db.session.add(exercise)
        db.session.commit()
        
        logger.info(f"Successfully added exercise: {title}")
        response_object = {
            "status": "success",
            "message": "New exercise was added!",
            "data": exercise.to_json(),
        }
        return jsonify(response_object), 201
        
    except exc.IntegrityError as e:
        logger.error(f"Database integrity error adding exercise {title}: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "fail", "message": INVALID_PAYLOAD_ERROR}), 400
    except Exception as e:
        logger.error(f"Error adding exercise {title}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        db.session.rollback()
        return jsonify({"status": "error", "message": INTERNAL_SERVER_ERROR}), 500

@exercises_blueprint.route("/<exercise_id>", methods=["PUT"])
@authenticate
def update_exercise(user_data, exercise_id):
    """Update exercise (admin only)"""
    logger.info(f"Updating exercise {exercise_id}")
    
    if not is_admin(user_data):
        logger.warning("Non-admin user attempted to update exercise")
        response_object = {
            "status": "fail",
            "message": "You do not have permission to do that."
        }
        return jsonify(response_object), 401

    try:
        post_data = request.get_json()
        if not post_data:
            logger.warning("Empty payload received for update exercise")
            return jsonify({"status": "fail", "message": INVALID_PAYLOAD_ERROR}), 400

        title = post_data.get("title")
        body = post_data.get("body")
        difficulty = post_data.get("difficulty")
        test_cases = post_data.get("test_cases")
        solutions = post_data.get("solutions")

        if all(x is None for x in [title, body, difficulty, test_cases, solutions]):
            logger.warning("No fields to update in payload")
            response_object = {"status": "fail", "message": "No fields to update in payload!"}
            return jsonify(response_object), 400

        exercise = Exercise.query.filter_by(id=int(exercise_id)).first()
        if not exercise:
            logger.warning(f"Exercise {exercise_id} not found for update")
            response_object = {"status": "fail", "message": "Sorry. That exercise does not exist."}
            return jsonify(response_object), 404

        # Update fields
        if title is not None:
            exercise.title = title
        if body is not None:
            exercise.body = body
        if difficulty is not None:
            exercise.difficulty = difficulty
        if test_cases is not None:
            exercise.test_cases = test_cases
        if solutions is not None:
            exercise.solutions = solutions
            
        db.session.commit()
        
        logger.info(f"Successfully updated exercise {exercise_id}")
        response_object = {
            "status": "success",
            "message": "Exercise was updated!",
            "data": exercise.to_json()
        }
        return jsonify(response_object), 200
        
    except ValueError as e:
        logger.error(f"Invalid exercise ID format: {exercise_id} - {str(e)}")
        return jsonify({"status": "fail", "message": "Invalid exercise ID"}), 400
    except Exception as e:
        logger.error(f"Error updating exercise {exercise_id}: {str(e)}")
        logger.exception(FULL_TRACEBACK_MSG)
        db.session.rollback()
        return jsonify({"status": "error", "message": INTERNAL_SERVER_ERROR}), 500

@exercises_blueprint.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "success",
        "message": "Exercises service is healthy"
    }), 200