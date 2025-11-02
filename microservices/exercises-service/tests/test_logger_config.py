from logging.handlers import RotatingFileHandler
from app.logger import get_logger, has_handlers, reset_logger, add_rotating_file_handler
from app.config import compute_database_uri, parse_cors_origins, get_bool_env, get_config

def test_logger_helpers(tmp_path):
    name = "cov_test_logger"
    # ensure clean
    reset_logger(name)
    assert has_handlers(name) is False

    # get_logger attaches a console handler
    lg = get_logger(name)
    assert has_handlers(name) is True

    # add rotating file handler
    log_file = tmp_path / "logs" / "app.log"
    h = add_rotating_file_handler(lg, str(log_file))
    assert isinstance(h, RotatingFileHandler)

    # reset removes all
    reset_logger(name)
    assert has_handlers(name) is False

def test_config_helpers_env_branches(monkeypatch):
    # DATABASE_URL present path
    env = {"DATABASE_URL": "postgresql://u:p@h:5432/db"}
    assert compute_database_uri(env) == env["DATABASE_URL"]

    # else-branch assembling URI
    env2 = {
        "DB_USER": "u",
        "DB_PASSWORD": "p",
        "DB_HOST": "h",
        "DB_PORT": "6543",
        "DB_NAME": "d",
    }
    assert compute_database_uri(env2) == "postgresql://u:p@h:6543/d"

    # parse CORS from env string
    env3 = {"CORS_ORIGINS": "http://a, http://b "}
    assert parse_cors_origins(env3) == ["http://a", "http://b"]

    # defaults when missing
    defaults = parse_cors_origins({})
    assert isinstance(defaults, list) and len(defaults) >= 1

    # bool parsing
    assert get_bool_env("X", default=True, env={}) is True
    assert get_bool_env("X", env={"X": "true"}) is True
    assert get_bool_env("X", env={"X": "0"}) is False
    assert get_bool_env("X", default=False, env={"X": "maybe"}) is False

def test_get_config_returns_class():
    cfg = get_config()
    assert hasattr(cfg, "SQLALCHEMY_DATABASE_URI")