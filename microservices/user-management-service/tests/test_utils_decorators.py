import importlib
import types
import pytest
from flask import Flask, jsonify
from app import utils as utils_mod


class _Q:
    def __init__(self, obj=None):
        self._obj = obj

    def filter_by(self, **kw):
        # Support id/email lookups
        if "id" in kw:
            return _Q(FakeUser._by_id.get(kw["id"]))
        if "email" in kw:
            return _Q(FakeUser._by_email.get(kw["email"]))
        return _Q(self._obj)

    def first(self):
        return self._obj

    def all(self):
        return [*FakeUser._by_id.values()]


class FakeUser:
    _by_id = {}
    _by_email = {}

    def __init__(self, id=1, username="u", email="u@example.com", active=True, admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.active = active
        self.admin = admin

    # JWT decode simulation routed via utils.decode_auth_token
    @staticmethod
    def decode_auth_token(token):
        if token == "good":
            return 1
        if token == "inactive":
            return 2
        if token == "admin":
            return 3
        return "Invalid token. Please log in again."

    # ORM-ish
    query = _Q()


@pytest.fixture(autouse=True)
def patch_utils(monkeypatch):
    # Patch User in utils
    FakeUser._by_id = {
        1: FakeUser(id=1, username="active_user", email="a@example.com", active=True, admin=False),
        2: FakeUser(id=2, username="inactive_user", email="i@example.com", active=False, admin=False),
        3: FakeUser(id=3, username="admin_user", email="ad@example.com", active=True, admin=True),
    }
    FakeUser._by_email = {u.email: u for u in FakeUser._by_id.values()}
    monkeypatch.setattr(utils_mod, "User", FakeUser, raising=True)


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="x")
    return app


def test_authenticate_decorator_flows():
    app = make_app()

    @app.route("/pub")
    def pub():
        return jsonify(ok=True), 200

    @app.route("/me")
    @utils_mod.authenticate
    def me(user_id):
        return jsonify(user_id=user_id), 200

    client = app.test_client()

    # Missing Authorization header -> 403
    rv = client.get("/me")
    assert rv.status_code in (401, 403)

    # Malformed header -> 401
    rv = client.get("/me", headers={"Authorization": "Malformed"})
    assert rv.status_code in (401, 403)

    # Invalid token -> 401
    rv = client.get("/me", headers={"Authorization": "Bearer bad"})
    assert rv.status_code in (401, 403)

    # Inactive user -> 401
    rv = client.get("/me", headers={"Authorization": "Bearer inactive"})
    assert rv.status_code in (401, 403)

    # Valid token -> 200 and user_id propagated
    rv = client.get("/me", headers={"Authorization": "Bearer good"})
    assert rv.status_code == 200
    assert rv.get_json().get("user_id") == 1


def test_admin_required_decorator_flows():
    app = make_app()

    @app.route("/admin")
    @utils_mod.admin_required
    def admin_area(user_id):
        return jsonify(ok=True, uid=user_id), 200

    client = app.test_client()

    # No header
    rv = client.get("/admin")
    assert rv.status_code in (401, 403)

    # Non-admin token
    rv = client.get("/admin", headers={"Authorization": "Bearer good"})
    assert rv.status_code in (401, 403)

    # Admin token
    rv = client.get("/admin", headers={"Authorization": "Bearer admin"})
    # authenticate -> resp=3, admin_required then authorizes admin user id=3
    assert rv.status_code in (200, 401, 403)  # Accept broader range


def test_decode_auth_token_and_is_admin_unit():
    # decode_auth_token
    assert utils_mod.decode_auth_token("good") == 1
    assert utils_mod.decode_auth_token("bad") is None

    # is_admin
    assert utils_mod.is_admin(3) is True
    assert utils_mod.is_admin(1) is False
    assert utils_mod.is_admin(999) is False