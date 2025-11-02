import types
import pytest
from flask import Flask
import app.utils as utils_mod

def test_is_admin_true_false():
    assert utils_mod.is_admin({"admin": True}) is True
    assert utils_mod.is_admin({"admin": False}) is False
    assert utils_mod.is_admin(None) is False

def test_verify_token_with_user_service_success(monkeypatch):
    class FakeResp:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {"username": "u", "admin": True}}
    monkeypatch.setattr(utils_mod, "USER_MANAGEMENT_SERVICE_URL", "http://fake")
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    res = utils_mod.verify_token_with_user_service("token")
    assert isinstance(res, dict)
    assert res.get("username") == "u"

def test_verify_token_with_user_service_non200(monkeypatch):
    class FakeResp:
        status_code = 401
        def json(self):
            return {}
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    assert utils_mod.verify_token_with_user_service("token") is None

def test_verify_token_with_user_service_exception(monkeypatch):
    def bad_get(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=bad_get))
    assert utils_mod.verify_token_with_user_service("token") is None

def test_authenticate_decorator_missing_header():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET"):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401, 403)

def test_authenticate_decorator_invalid_format():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401,)

def test_authenticate_decorator_success(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(utils_mod, "verify_token_with_user_service", lambda t: {"username":"u","admin":True}, raising=False)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"received": user_data.get("username")}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer tok"}):
        res = _inner()
        assert isinstance(res, dict)
        assert res.get("received") == "u"

def test_authenticate_decorator_invalid_token(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(utils_mod, "verify_token_with_user_service", lambda t: None, raising=False)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer bad"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401,)