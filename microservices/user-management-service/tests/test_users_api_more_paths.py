import importlib
import types
import pytest
from flask import Flask

def _get_mod():
    return importlib.import_module("app.api.users")

def _mk_app():
    app = Flask("test-users-api")
    app.config.update(TESTING=True, SECRET_KEY="test-secret", BCRYPT_LOG_ROUNDS=4, TOKEN_EXPIRATION_DAYS=30, TOKEN_EXPIRATION_SECONDS=0)
    return app

class FakeUser:
    def __init__(self, id, username, email, active=True, admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.active = active
        self.admin = admin
    
    def to_json(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "active": self.active,
            "admin": self.admin
        }

class FakeColumn:
    """Fake SQLAlchemy column for filtering"""
    def __init__(self, name, value=None):
        self.name = name
        self.value = value
    
    def __eq__(self, other):
        return FakeFilter(self.name, "==", other)
    
    def __or__(self, other):
        return FakeCombinedFilter([self, other])

class FakeFilter:
    def __init__(self, column, op, value):
        self.column = column
        self.op = op
        self.value = value

class FakeCombinedFilter:
    def __init__(self, filters):
        self.filters = filters

class FakeQuery:
    def __init__(self, items=None, single=None, raise_error=None):
        self._items = items or []
        self._single = single
        self._raise_error = raise_error
    
    def filter(self, *args, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return self
    
    def filter_by(self, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return self
    
    def first(self):
        if self._raise_error:
            raise self._raise_error
        return self._single
    
    def all(self):
        if self._raise_error:
            raise self._raise_error
        return self._items

class FakeDBSession:
    def __init__(self, fail_on_commit=False):
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self._fail_on_commit = fail_on_commit
    
    def add(self, obj):
        self.added.append(obj)
    
    def commit(self):
        self.committed += 1
        if self._fail_on_commit:
            from sqlalchemy import exc
            raise exc.IntegrityError("test", "params", Exception("duplicate"))
    
    def rollback(self):
        self.rolled_back += 1

def _ensure_user_and_db(monkeypatch, users_api):
    """Ensure User class and db.session are properly set up"""
    if not hasattr(users_api, "User"):
        monkeypatch.setattr(users_api, "User", type("User", (), {
            "query": FakeQuery(),
            "__init__": lambda self, **kw: None,
            "to_json": lambda self: {}
        }), raising=False)
    
    if not hasattr(users_api, "db"):
        monkeypatch.setattr(users_api, "db", types.SimpleNamespace(
            session=FakeDBSession()
        ), raising=False)

def _get_view(users_api, view_name):
    """Get view function, preferring __wrapped__ to bypass decorators"""
    view = getattr(users_api, view_name, None)
    if view is None:
        pytest.skip(f"{view_name} not found")
    return getattr(view, "__wrapped__", view)

# ============= get_all_users tests =============

def test_get_all_users_success(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_all_users")
    
    users = [FakeUser(1, "u1", "a@e"), FakeUser(2, "u2", "b@e")]
    monkeypatch.setattr(users_api.User, "query", FakeQuery(items=users), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1)
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["data"]["users"]) == 2

def test_get_all_users_exception(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_all_users")
    
    monkeypatch.setattr(users_api.User, "query", FakeQuery(raise_error=RuntimeError("db error")), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1)
        assert code == 500
        data = resp.get_json()
        assert data["status"] == "error"

# ============= get_single_user tests =============

def test_get_single_user_unauthorized(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(2, "1")
        assert code == 401
        data = resp.get_json()
        assert "permission" in data["message"].lower()

def test_get_single_user_not_found(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    monkeypatch.setattr(users_api.User, "query", FakeQuery(single=None), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "999")
        assert code == 404
        data = resp.get_json()
        assert "does not exist" in data["message"].lower()

def test_get_single_user_value_error_in_try(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "abc")
        assert code == 404
        data = resp.get_json()
        assert "does not exist" in data["message"].lower()

def test_get_single_user_success(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    user = FakeUser(id=7, username="u7", email="u7@e")
    monkeypatch.setattr(users_api.User, "query", FakeQuery(single=user), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "7")
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["id"] == 7

def test_get_single_user_self_access(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    user = FakeUser(id=5, username="u5", email="u5@e")
    monkeypatch.setattr(users_api.User, "query", FakeQuery(single=user), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(5, "5")
        assert code == 200
        data = resp.get_json()
        assert data["data"]["id"] == 5

def test_get_single_user_exception(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "get_single_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    monkeypatch.setattr(users_api.User, "query", FakeQuery(raise_error=RuntimeError("db error")), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "1")
        assert code == 500
        data = resp.get_json()
        assert data["status"] == "error"

# ============= add_user tests =============

def test_add_user_not_admin(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "add_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "test"}):
        resp, code = view(1)
        assert code == 401

def test_add_user_invalid_payload(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "add_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json=None):
        resp, code = view(1)
        assert code == 400
        assert "Invalid payload" in resp.get_json()["message"]

def test_add_user_missing_fields(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "add_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "test"}):
        resp, code = view(1)
        assert code == 400
        assert "Missing required fields" in resp.get_json()["message"]

def test_add_user_duplicate(monkeypatch):
    users_api = _get_mod()
    _ensure_user_and_db(monkeypatch, users_api)
    view = _get_view(users_api, "add_user")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    existing = FakeUser(1, "exist", "exist@e")
    monkeypatch.setattr(users_api.User, "query", FakeQuery(single=existing), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "exist", "email": "exist@e", "password": "pass"}):
        resp, code = view(1)
        assert code == 400
        assert "already exists" in resp.get_json()["message"].lower()

def test_add_user_success(monkeypatch):
    users_api = _get_mod()
    session = FakeDBSession()
    
    class FakeUserClass:
        # Class-level attributes for SQLAlchemy-style filtering
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password):
            self.id = 10
            self.username = username
            self.email = email
            self.active = True
            self.admin = False
        
        def to_json(self):
            return {
                "id": self.id,
                "username": self.username,
                "email": self.email,
                "active": self.active,
                "admin": self.admin
            }
        
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    view = _get_view(users_api, "add_user")
    app = _mk_app()
    
    with app.test_request_context("/", method="POST", json={"username": "new", "email": "new@e", "password": "pass"}):
        resp, code = view(1)
        assert code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["username"] == "new"

def test_add_user_integrity_error(monkeypatch):
    users_api = _get_mod()
    session = FakeDBSession(fail_on_commit=True)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password):
            self.username = username
        
        query = FakeQuery(single=None)
        def to_json(self): return {}
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    view = _get_view(users_api, "add_user")
    app = _mk_app()
    
    with app.test_request_context("/", method="POST", json={"username": "new", "email": "new@e", "password": "pass"}):
        resp, code = view(1)
        assert code == 400

# ============= admin_create_user tests =============

def test_admin_create_user_exists(monkeypatch):
    """Test that admin_create_user function exists or skip if not implemented"""
    users_api = _get_mod()
    if not hasattr(users_api, "admin_create_user"):
        pytest.skip("admin_create_user not implemented - likely using add_user instead")

def test_admin_create_user_not_admin(monkeypatch):
    users_api = _get_mod()
    view = _get_view(users_api, "admin_create_user")
    _ensure_user_and_db(monkeypatch, users_api)
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={}):
        resp, code = view(1)
        assert code == 401

def test_admin_create_user_missing_fields(monkeypatch):
    users_api = _get_mod()
    view = _get_view(users_api, "admin_create_user")
    _ensure_user_and_db(monkeypatch, users_api)
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "test"}):
        resp, code = view(1)
        assert code == 400

def test_admin_create_user_success(monkeypatch):
    users_api = _get_mod()
    view = _get_view(users_api, "admin_create_user")
    
    session = FakeDBSession()
    
    class FakeUserClass:
        # Class-level attributes for SQLAlchemy-style filtering
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password, admin=False, active=True):
            self.id = 20
            self.username = username
            self.email = email
            self.admin = admin
            self.active = active
        
        def to_json(self):
            return {
                "id": self.id,
                "username": self.username,
                "email": self.email,
                "admin": self.admin,
                "active": self.active
            }
        
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    app = _mk_app()
    
    with app.test_request_context("/", method="POST", json={
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "pass123",
        "admin": True,
        "active": False
    }):
        resp, code = view(1)
        assert code == 201, f"Expected 201, got {code}. Response: {resp.get_json()}"
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["admin"] is True
        assert data["data"]["active"] is False

def test_admin_create_user_duplicate(monkeypatch):
    users_api = _get_mod()
    view = _get_view(users_api, "admin_create_user")
    _ensure_user_and_db(monkeypatch, users_api)
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    existing = FakeUser(1, "exist", "exist@e")
    monkeypatch.setattr(users_api.User, "query", FakeQuery(single=existing), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "exist", "email": "exist@e", "password": "pass"}):
        resp, code = view(1)
        assert code == 400

def test_admin_create_user_exception(monkeypatch):
    users_api = _get_mod()
    view = _get_view(users_api, "admin_create_user")
    _ensure_user_and_db(monkeypatch, users_api)
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    monkeypatch.setattr(users_api.User, "query", FakeQuery(raise_error=RuntimeError("db error")), raising=False)
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", json={"username": "test", "email": "test@e", "password": "pass"}):
        resp, code = view(1)
        assert code in (400, 500)

# ============= health check test =============

def test_health_check():
    users_api = _get_mod()
    health = getattr(users_api, "health_check", None)
    if health is None:
        pytest.skip("health_check not found")
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = health()
        assert code in (200, 204)