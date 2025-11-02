import types
from flask import Flask
import app.utils as utils_mod

def test_authenticate_missing_header():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET"):
        resp = _inner()
        assert isinstance(resp, tuple)
        # scores-service returns 403 when header missing
        assert resp[1] in (401, 403)

def test_authenticate_invalid_format():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Token abc"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        # invalid format returns 401 in scores-service
        assert resp[1] in (401,)

def test_authenticate_invalid_token(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(utils_mod, "verify_token_with_user_service", lambda t: None, raising=False)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer bad"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401,)

def test_authenticate_success(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(utils_mod, "verify_token_with_user_service", lambda t: {"id": 7, "username": "u"}, raising=False)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"received": user_data.get("id")}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer tok"}):
        res = _inner()
        assert isinstance(res, dict)
        assert res.get("received") == 7

def test_verify_token_with_user_service_success(monkeypatch):
    class FakeResp:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {"id": 1, "username": "u"}}
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    data = utils_mod.verify_token_with_user_service("token")
    assert isinstance(data, dict) and data.get("id") == 1

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

def test_is_admin_truthiness():
    # function returns user_data and user_data.get('admin', False)
    assert utils_mod.is_admin({"admin": True}) is True
    assert utils_mod.is_admin({"admin": False}) is False
    # ensure falsy when None (may be None from implementation)
    assert bool(utils_mod.is_admin(None)) is False

def test_authenticate_bearer_missing_token():
    app = Flask(__name__)
    import app.utils as utils_mod
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    # "Bearer" không kèm token -> IndexError branch
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401,)

def test_verify_token_with_user_service_200_invalid_body(monkeypatch):
    import app.utils as utils_mod
    class FakeResp:
        status_code = 200
        def json(self):
            # status khác success -> phải trả None
            return {"status": "fail"}
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    assert utils_mod.verify_token_with_user_service("token") is None