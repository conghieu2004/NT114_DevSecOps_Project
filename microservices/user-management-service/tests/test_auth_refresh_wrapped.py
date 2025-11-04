import importlib
import types
import pytest
from flask import Flask

def _get_auth_mod():
    return importlib.import_module("app.api.auth")

def _mk_app():
    app = Flask("test-auth-api")
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        BCRYPT_LOG_ROUNDS=4,
        TOKEN_EXPIRATION_DAYS=30,
        TOKEN_EXPIRATION_SECONDS=0
    )
    return app

class FakeUser:
    def __init__(self, id, username, email, password="hashed", active=True, admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
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
    
    def encode_auth_token(self, user_id):
        return f"token_{user_id}"

class FakeColumn:
    """Fake SQLAlchemy column for filtering"""
    def __init__(self, name):
        self.name = name
    
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
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = len(self.added) + 100
        self.added.append(obj)
    
    def commit(self):
        self.committed += 1
        if self._fail_on_commit:
            from sqlalchemy import exc
            raise exc.IntegrityError("test", "params", Exception("duplicate"))
    
    def rollback(self):
        self.rolled_back += 1

class FakeBcrypt:
    @staticmethod
    def generate_password_hash(password, rounds=None):
        return b"hashed_password"
    
    @staticmethod
    def check_password_hash(stored, provided):
        return provided == "correctpass"

def _ensure_auth_deps(monkeypatch, auth_api):
    """Ensure User, db, and bcrypt are properly set up"""
    if not hasattr(auth_api, "User"):
        class MockUser:
            email = FakeColumn("email")
            username = FakeColumn("username")
            query = FakeQuery()
            
            def __init__(self, **kw):
                pass
            
            def to_json(self):
                return {}
            
            def encode_auth_token(self, uid):
                return f"token_{uid}"
        
        monkeypatch.setattr(auth_api, "User", MockUser, raising=False)
    
    if not hasattr(auth_api, "db"):
        monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(
            session=FakeDBSession()
        ), raising=False)
    
    if not hasattr(auth_api, "bcrypt"):
        monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)

def _get_view(auth_api, view_name):
    """Get view function, preferring __wrapped__ to bypass decorators"""
    view = getattr(auth_api, view_name, None)
    if view is None:
        pytest.skip(f"{view_name} not found")
    return getattr(view, "__wrapped__", view)

# ============= register_user tests =============

def test_register_user_success(monkeypatch):
    auth_api = _get_auth_mod()
    session = FakeDBSession()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password):
            self.id = 100
            self.username = username
            self.email = email
            self.password = b"hashed"
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
        
        def encode_auth_token(self, user_id):
            return f"token_{user_id}"
        
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view(auth_api, "register_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "testuser", "email": "test@example.com", "password": "SecurePass123"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 201, f"Expected 201, got {code}. Response: {resp.get_json()}"
        data = resp.get_json()
        assert data["status"] == "success"
        assert "auth_token" in data
        assert session.committed == 1

def test_register_user_invalid_payload(monkeypatch):
    auth_api = _get_auth_mod()
    _ensure_auth_deps(monkeypatch, auth_api)
    view = _get_view(auth_api, "register_user")
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", data="", content_type="application/json"):
        resp, code = view()
        assert code == 400
        assert "Invalid payload" in resp.get_json()["message"]

def test_register_user_missing_fields(monkeypatch):
    auth_api = _get_auth_mod()
    _ensure_auth_deps(monkeypatch, auth_api)
    view = _get_view(auth_api, "register_user")
    
    app = _mk_app()
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "test"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400

def test_register_user_duplicate_username(monkeypatch):
    auth_api = _get_auth_mod()
    
    existing = FakeUser(1, "existing", "old@example.com")
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=existing)
        
        def __init__(self, username, email, password):
            pass
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=FakeDBSession()), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view(auth_api, "register_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "existing", "email": "new@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400
        assert "already exists" in resp.get_json()["message"].lower()

def test_register_user_duplicate_email(monkeypatch):
    auth_api = _get_auth_mod()
    
    # First call returns None (username check), second returns existing user (email check)
    call_count = [0]
    
    class SmartFakeQuery:
        def filter_by(self, **kwargs):
            return self
        
        def first(self):
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # username doesn't exist
            else:
                return FakeUser(2, "other", "existing@example.com")  # email exists
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = SmartFakeQuery()
        
        def __init__(self, username, email, password):
            pass
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=FakeDBSession()), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view(auth_api, "register_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "newuser", "email": "existing@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code in (400, 409)

def test_register_user_integrity_error(monkeypatch):
    auth_api = _get_auth_mod()
    
    # Mock sqlalchemy.exc để đảm bảo exception được xử lý đúng
    from sqlalchemy import exc as sqlalchemy_exc
    
    class FakeDBSessionWithError:
        def __init__(self):
            self.added = []
            self.committed = 0
            self.rolled_back = 0
        
        def add(self, obj):
            self.added.append(obj)
        
        def commit(self):
            self.committed += 1
            # Raise IntegrityError from sqlalchemy
            raise sqlalchemy_exc.IntegrityError("test", "params", Exception("duplicate key"))
        
        def rollback(self):
            self.rolled_back += 1
    
    session = FakeDBSessionWithError()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password):
            self.username = username
            self.email = email
        
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view(auth_api, "register_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "test", "email": "test@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400, f"Expected 400, got {code}. Response: {resp.get_json()}"
        assert "already exists" in resp.get_json()["message"].lower()

def test_register_user_general_exception(monkeypatch):
    auth_api = _get_auth_mod()
    
    class BrokenUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        
        def __init__(self, username, email, password):
            raise RuntimeError("Something went wrong")
        
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(auth_api, "User", BrokenUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=FakeDBSession()), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view(auth_api, "register_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"username": "test", "email": "test@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code in (400, 500)

# ============= login_user tests =============

def test_login_user_success(monkeypatch):
    auth_api = _get_auth_mod()
    
    user = FakeUser(5, "testuser", "test@example.com", "hashed", True, False)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    class FakeBcryptSuccess:
        @staticmethod
        def check_password_hash(stored, provided):
            return True
    
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcryptSuccess(), raising=False)
    
    view = _get_view(auth_api, "login_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"email": "test@example.com", "password": "correctpass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "auth_token" in data

def test_login_user_invalid_payload(monkeypatch):
    auth_api = _get_auth_mod()
    _ensure_auth_deps(monkeypatch, auth_api)
    view = _get_view(auth_api, "login_user")
    
    app = _mk_app()
    with app.test_request_context("/", method="POST", data="", content_type="application/json"):
        resp, code = view()
        assert code == 400

def test_login_user_missing_email(monkeypatch):
    auth_api = _get_auth_mod()
    _ensure_auth_deps(monkeypatch, auth_api)
    view = _get_view(auth_api, "login_user")
    
    app = _mk_app()
    with app.test_request_context(
        "/",
        method="POST",
        data='{"password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400

def test_login_user_not_found(monkeypatch):
    auth_api = _get_auth_mod()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view(auth_api, "login_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"email": "notfound@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 404

def test_login_user_wrong_password(monkeypatch):
    auth_api = _get_auth_mod()
    
    user = FakeUser(5, "testuser", "test@example.com", "hashed", True, False)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    class FakeBcryptFail:
        @staticmethod
        def check_password_hash(stored, provided):
            return False
    
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcryptFail(), raising=False)
    
    view = _get_view(auth_api, "login_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"email": "test@example.com", "password": "wrongpass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 401

def test_login_user_inactive_account(monkeypatch):
    auth_api = _get_auth_mod()
    
    user = FakeUser(5, "testuser", "test@example.com", "hashed", active=False, admin=False)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    class FakeBcryptSuccess:
        @staticmethod
        def check_password_hash(stored, provided):
            return True
    
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcryptSuccess(), raising=False)
    
    view = _get_view(auth_api, "login_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"email": "test@example.com", "password": "correctpass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 401
        assert "inactive" in resp.get_json()["message"].lower()

def test_login_user_exception(monkeypatch):
    auth_api = _get_auth_mod()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(raise_error=RuntimeError("db error"))
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view(auth_api, "login_user")
    app = _mk_app()
    
    with app.test_request_context(
        "/",
        method="POST",
        data='{"email": "test@example.com", "password": "pass"}',
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 500

# ============= logout_user tests =============

def test_logout_user_success(monkeypatch):
    auth_api = _get_auth_mod()
    view = _get_view(auth_api, "logout_user")
    app = _mk_app()
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer validtoken"}):
        if hasattr(view, "__code__") and view.__code__.co_argcount > 0:
            resp, code = view(5)
        else:
            resp, code = view()
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"

# ============= get_user_status tests =============

def test_get_user_status_success(monkeypatch):
    auth_api = _get_auth_mod()
    
    user = FakeUser(7, "statususer", "status@example.com", active=True, admin=False)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view(auth_api, "get_user_status")
    app = _mk_app()
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer validtoken"}):
        if hasattr(view, "__code__") and view.__code__.co_argcount > 0:
            resp, code = view(7)
        else:
            resp, code = view()
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["id"] == 7

def test_get_user_status_not_found(monkeypatch):
    auth_api = _get_auth_mod()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view(auth_api, "get_user_status")
    app = _mk_app()
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer validtoken"}):
        if hasattr(view, "__code__") and view.__code__.co_argcount > 0:
            resp, code = view(999)
        else:
            resp, code = view()
        assert code == 404

def test_get_user_status_exception(monkeypatch):
    auth_api = _get_auth_mod()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(raise_error=RuntimeError("db error"))
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view(auth_api, "get_user_status")
    app = _mk_app()
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer validtoken"}):
        if hasattr(view, "__code__") and view.__code__.co_argcount > 0:
            resp, code = view(7)
        else:
            resp, code = view()
        assert code == 500

# ============= health_check test =============

def test_health_check(monkeypatch):
    auth_api = _get_auth_mod()
    view = getattr(auth_api, "health_check", None)
    if view is None:
        pytest.skip("health_check not found")
    
    app = _mk_app()
    with app.test_request_context("/", method="GET"):
        resp, code = view()
        assert code in (200, 204)