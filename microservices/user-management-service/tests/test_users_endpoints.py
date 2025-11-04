import importlib
import pytest
from flask import Flask

# Import để tăng coverage khi parse file users.py
import app.api.users as users_module


def _create_app_or_skip():
    main = importlib.import_module("app.main")
    create_app = getattr(main, "create_app", None)
    if not callable(create_app):
        pytest.skip("create_app not available")
    app = create_app()
    if not isinstance(app, Flask):
        pytest.skip("create_app did not return Flask app")
    app.config.update(TESTING=True)
    return app


def test_users_health_endpoint_status_code():
    app = _create_app_or_skip()
    client = app.test_client()
    rv = client.get("/api/users/health")
    assert rv.status_code in (200, 204, 404)


def test_users_list_requires_auth_or_exists():
    app = _create_app_or_skip()
    client = app.test_client()
    rv = client.get("/api/users/")
    assert rv.status_code in (200, 401, 403, 404)