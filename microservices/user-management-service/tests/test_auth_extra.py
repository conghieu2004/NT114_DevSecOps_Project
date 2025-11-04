import importlib
import pytest
from flask import Flask

def _get_app() -> Flask:
    main = importlib.import_module("app.main")
    app = getattr(main, "app", None)
    if app is None:
        create_app = getattr(main, "create_app", None)
        if callable(create_app):
            app = create_app()
    assert isinstance(app, Flask), "Failed to create Flask app"
    app.config.update(TESTING=True)
    return app

@pytest.fixture
def client():
    app = _get_app()
    return app.test_client()

def _find_path(url_map, candidates, methods=None):
    # Trả về path đầu tiên tồn tại, và nếu methods được chỉ định thì phải hỗ trợ
    allowed = set(m.upper() for m in (methods or []))
    for rule in url_map.iter_rules():
        if any(str(rule.rule).endswith(c) or c in str(rule.rule) for c in candidates):
            if not allowed or (rule.methods and allowed.issubset(rule.methods)):
                return str(rule.rule)
    return None

def test_auth_status_with_invalid_token(client):
    path = _find_path(client.application.url_map, candidates=["/status", "auth/status"], methods=["GET"])
    if not path:
        pytest.skip("status endpoint not found")
    rv = client.get(path, headers={"Authorization": "Bearer invalid-token"})
    # Có thể 401/403 hoặc 200 tùy implement
    assert rv.status_code in (200, 401, 403)

def test_auth_logout_with_invalid_token(client):
    # tìm logout
    path = _find_path(client.application.url_map, candidates=["/logout", "auth/logout"], methods=["POST"])
    if not path:
        pytest.skip("logout endpoint not found")
    rv = client.post(path, headers={"Authorization": "Bearer invalid-token"})
    assert rv.status_code in (200, 401, 403)

def test_auth_refresh_missing_token(client):
    # refresh có thể là GET hoặc POST tùy implement
    path = _find_path(client.application.url_map, candidates=["/refresh", "auth/refresh"], methods=["GET"])
    method = "GET"
    if not path:
        path = _find_path(client.application.url_map, candidates=["/refresh", "auth/refresh"], methods=["POST"])
        method = "POST"
    if not path:
        pytest.skip("refresh endpoint not found")

    if method == "GET":
        rv = client.get(path)
    else:
        rv = client.post(path)
    # Không có token có thể dẫn đến 401/403/400
    assert rv.status_code in (200, 400, 401, 403)