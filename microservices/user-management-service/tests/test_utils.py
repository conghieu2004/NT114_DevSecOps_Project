import types
import pytest
from flask import Flask
import app.utils as utils_mod


def _app():
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", TESTING=True)
    return app


# ---------- authenticate ----------

def test_authenticate_missing_header_returns_403():
    app = _app()

    @utils_mod.authenticate
    def protected(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET"):
        resp = protected()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 403
        assert body.get_json()["message"].lower().startswith("provide a valid auth token")


def test_authenticate_bearer_without_token_returns_401():
    app = _app()

    @utils_mod.authenticate
    def protected(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = protected()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 401
        assert "Invalid token format" in body.get_json()["message"]


def test_authenticate_invalid_token_returns_401(monkeypatch):
    app = _app()
    # Force decode_auth_token to fail
    monkeypatch.setattr(utils_mod, "decode_auth_token", lambda tok: None, raising=False)

    @utils_mod.authenticate
    def protected(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer bad"}):
        resp = protected()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 401
        assert "Invalid token" in body.get_json()["message"]


def test_authenticate_success_passes_user_id(monkeypatch):
    app = _app()
    monkeypatch.setattr(utils_mod, "decode_auth_token", lambda tok: 42, raising=False)

    @utils_mod.authenticate
    def protected(user_id):
        return {"received": user_id}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer good"}):
        res = protected()
        assert isinstance(res, dict)
        assert res["received"] == 42


# ---------- decode_auth_token ----------

class _FakeQuery:
    def __init__(self, user):
        self._user = user

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._user


class _UserObj:
    def __init__(self, username="u", email="e@e", active=True, admin=False):
        self.username = username
        self.email = email
        self.active = active
        self.admin = admin


def test_decode_auth_token_error_string_short_circuits(monkeypatch):
    # User.decode_auth_token returns error string -> utils.decode_auth_token returns None
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: "Invalid token",
        query=_FakeQuery(_UserObj()),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.decode_auth_token("x") is None


def test_decode_auth_token_valid_and_active_returns_user_id(monkeypatch):
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: 7,
        query=_FakeQuery(_UserObj(active=True)),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.decode_auth_token("good") == 7


def test_decode_auth_token_user_not_found(monkeypatch):
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: 1,
        query=_FakeQuery(None),  # first() -> None
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.decode_auth_token("x") is None


def test_decode_auth_token_inactive_user(monkeypatch):
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: 2,
        query=_FakeQuery(_UserObj(active=False)),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.decode_auth_token("x") is None


def test_decode_auth_token_exception_returns_none(monkeypatch):
    # Make User.decode_auth_token raise to hit except
    def boom(_):
        raise RuntimeError("boom")

    FakeUser = types.SimpleNamespace(
        decode_auth_token=boom,
        query=_FakeQuery(_UserObj()),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.decode_auth_token("x") is None


# ---------- is_admin ----------

def test_is_admin_true(monkeypatch):
    FakeUser = types.SimpleNamespace(
        query=_FakeQuery(_UserObj(admin=True))
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.is_admin(1) is True


def test_is_admin_user_not_found(monkeypatch):
    FakeUser = types.SimpleNamespace(
        query=_FakeQuery(None)
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.is_admin(999) is False


def test_is_admin_exception_returns_false(monkeypatch):
    class BoomQuery:
        def filter_by(self, **_):
            raise RuntimeError("db down")

    FakeUser = types.SimpleNamespace(query=BoomQuery())
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)
    assert utils_mod.is_admin(1) is False


# ---------- admin_required ----------

def test_admin_required_missing_header(monkeypatch):
    app = _app()

    @utils_mod.admin_required
    def admin_ep(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET"):
        resp = admin_ep()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 403
        assert "Provide a valid auth token" in body.get_json()["message"]


def test_admin_required_invalid_header_format(monkeypatch):
    app = _app()

    @utils_mod.admin_required
    def admin_ep(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = admin_ep()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 403
        assert "Bearer token malformed" in body.get_json()["message"]


def test_admin_required_non_admin_returns_403(monkeypatch):
    app = _app()
    # Fake user: active=True, admin=False
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: 11,
        query=_FakeQuery(_UserObj(active=True, admin=False, username="u", email="e@e")),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)

    @utils_mod.admin_required
    def admin_ep(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer tok"}):
        resp = admin_ep()
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 403
        assert "Admin privileges required" in body.get_json()["message"]


def test_admin_required_success(monkeypatch):
    app = _app()
    # Fake user admin=True
    FakeUser = types.SimpleNamespace(
        decode_auth_token=lambda tok: 5,
        query=_FakeQuery(_UserObj(active=True, admin=True, username="admin", email="a@a")),
    )
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=False)

    @utils_mod.admin_required
    def admin_ep(user_id):
        return {"received": user_id}

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer tok"}):
        res = admin_ep()
        assert isinstance(res, dict)
        assert res["received"] == 5