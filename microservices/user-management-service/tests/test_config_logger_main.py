import os
import importlib
import types
from flask import Flask
from app.logger import setup_logger, get_logger
from app.config import get_config, BaseConfig, DevelopmentConfig, ProductionConfig


def test_get_config_variants(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    cfg = get_config()
    assert cfg is ProductionConfig

    monkeypatch.setenv("FLASK_ENV", "development")
    cfg2 = get_config()
    assert cfg2 is DevelopmentConfig


def test_logger_setup_and_get_logger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logger = setup_logger()
    log = get_logger("x")
    log.info("hello")
    # Handlers created, log files exist
    assert (tmp_path / "logs" / "auth_service.log").exists()
    assert (tmp_path / "logs" / "auth_error.log").exists()


def test_main_factory_with_sqlite(monkeypatch):
    # Force main to use a SQLite config via monkeypatching get_config before importing app.main
    class TestCfg(BaseConfig):
        TESTING = True
        DEBUG = False
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SECRET_KEY = "test-secret"
        BCRYPT_LOG_ROUNDS = 4

    import sys
    if "app.main" in sys.modules:
        del sys.modules["app.main"]

    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setattr("app.config.get_config", lambda: TestCfg, raising=True)

    main = importlib.import_module("app.main")
    app = getattr(main, "app", None)
    assert app and isinstance(app, Flask)

    # Only hit health endpoints to avoid DB logic beyond create_all
    client = app.test_client()
    assert client.get("/api/auth/health").status_code == 200
    assert client.get("/api/users/health").status_code == 200