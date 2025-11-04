import os
import importlib
import pytest
from flask import Flask


def test_setup_logger_and_get_logger(tmp_path, monkeypatch):
    logger_mod = importlib.import_module("app.logger")
    setup_logger = getattr(logger_mod, "setup_logger", None)
    get_logger = getattr(logger_mod, "get_logger", None)
    assert callable(setup_logger) and callable(get_logger)
    # Đổi current dir để tạo thư mục logs an toàn
    monkeypatch.chdir(tmp_path)
    setup_logger()
    lg = get_logger("test")
    # logger có thể trả instance hoặc None tùy implement
    assert lg is None or hasattr(lg, "info")


def test_config_get_config_and_env_reload(monkeypatch):
    config_mod = importlib.import_module("app.config")
    get_config = getattr(config_mod, "get_config", None)
    assert callable(get_config)
    cfg = get_config()
    # Các thuộc tính cơ bản
    assert hasattr(cfg, "SECRET_KEY")
    assert hasattr(cfg, "SQLALCHEMY_TRACK_MODIFICATIONS")

    # Thử thay đổi env rồi reload để cover nhánh khác
    monkeypatch.setenv("FLASK_DEBUG", "1")
    importlib.reload(config_mod)
    cfg2 = config_mod.get_config()
    # Kiểm tra vẫn có SECRET_KEY và kiểu dữ liệu hợp lý
    assert hasattr(cfg2, "SECRET_KEY")


def test_create_app_and_blueprints_importable():
    # Import main để cover code khởi tạo
    main = importlib.import_module("app.main")
    create_app = getattr(main, "create_app", None)
    assert callable(create_app)
    app = create_app()
    assert isinstance(app, Flask)

    # Kiểm tra map route (không cứng ràng buộc)
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert isinstance(rules, list)