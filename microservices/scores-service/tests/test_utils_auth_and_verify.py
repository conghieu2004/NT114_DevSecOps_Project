import types
import pytest
from flask import Flask
import app.utils as utils_mod

def test_authenticate_no_header():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data=None):
        return {"ok": True}
    with app.test_request_context("/", method="GET"):
        resp = _inner()
        assert isinstance(resp, tuple) and resp[1] in (401, 403)

def test_authenticate_wrong_scheme():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data=None):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Basic abc"}):
        resp = _inner()
        assert isinstance(resp, tuple) and resp[1] in (401, 403)

def test_authenticate_empty_bearer_token():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data=None):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = _inner()
        assert isinstance(resp, tuple) and resp[1] in (401, 403)

def test_verify_token_timeout_returns_none(monkeypatch):
    class TimeoutExc(Exception): ...
    class FakeRequests:
        def get(self, *a, **k):
            raise TimeoutExc("timeout")
    monkeypatch.setattr(utils_mod, "requests", FakeRequests())
    assert utils_mod.verify_token_with_user_service("tok") is None

def test_verify_token_success_returns_dict(monkeypatch):
    class FakeResp:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {"id": 1, "admin": True}}
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    out = utils_mod.verify_token_with_user_service("tok")
    assert isinstance(out, dict) and out.get("id") == 1 and out.get("admin") is True

def test_is_admin_true_and_false():
    assert utils_mod.is_admin({"admin": True}) is True
    assert utils_mod.is_admin({"admin": False}) is False
    assert utils_mod.is_admin(None) is False