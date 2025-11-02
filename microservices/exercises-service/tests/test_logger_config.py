from app.logger import get_logger, setup_logger
from app.config import get_config

def test_get_logger_returns_logger():
    lg = get_logger("testlogger")
    assert hasattr(lg, "info")
    lg.info("logger test")

def test_get_config_callable():
    cfg = get_config()
    assert hasattr(cfg, "SQLALCHEMY_DATABASE_URI")