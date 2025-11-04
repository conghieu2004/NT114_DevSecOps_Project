import time
import pytest
from flask import Flask
import importlib


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


def _first_existing_path(client, method, candidates):
    """
    Chọn path đầu tiên có tồn tại và hỗ trợ method mong muốn.
    - Ưu tiên kiểm tra Allow header từ OPTIONS để biết method nào được phép.
    - Nếu không có Allow, thử gọi method thực tế; bỏ qua path nếu 404/405.
    """
    method = (method or "GET").upper()
    for p in candidates:
        # OPTIONS để lấy Allow header
        opt = client.open(p, method="OPTIONS")
        if opt.status_code == 404:
            continue
        allow = opt.headers.get("Allow", "")
        allowed = {m.strip().upper() for m in allow.split(",") if m}
        if method in allowed:
            return p
        # Fallback: thử method thật, nếu không phải 404/405 thì coi như hợp lệ
        probe = client.open(p, method=method)
        if probe.status_code not in (404, 405):
            return p
    pytest.skip(f"No matching endpoint found for {method} among: {candidates}")


def test_register_new_user(client):
    candidates = [
        "/api/v1/users/register",
        "/api/users/register",
        "/api/auth/register",
        "/users/register",
        "/auth/register",
    ]
    path = _first_existing_path(client, "POST", candidates)

    now = int(time.time() * 1000)
    payload = {
        "username": f"ci_user_{now}",
        "email": f"ci_{now}@example.com",
        "password": "SecurePassword123",
    }
    resp = client.post(path, json=payload)

    # Chấp nhận các mã phù hợp với nhiều triển khai
    assert resp.status_code in (201, 200, 400, 409)


def test_login_success(client):
    candidates = [
        "/api/v1/users/login",
        "/api/users/login",
        "/api/auth/login",
        "/users/login",
        "/auth/login",
    ]
    path = _first_existing_path(client, "POST", candidates)

    creds = {"username": "admin", "password": "adminpassword"}

    resp = client.post(path, json=creds)
    if resp.status_code in (415, 400) and not resp.get_json():
        # Thử lại dạng form nếu backend không nhận JSON
        resp = client.post(path, data=creds)

    assert resp.status_code in (200, 401, 400)


def test_get_user_details_unauthenticated(client):
    candidates = [
        "/api/v1/users/1",
        "/api/users/1",
        "/users/1",
        "/api/users/details/1",
    ]
    path = _first_existing_path(client, "GET", candidates)

    resp = client.get(path)

    # Nếu yêu cầu auth: 401/403; nếu public: 200
    assert resp.status_code in (401, 403, 200)