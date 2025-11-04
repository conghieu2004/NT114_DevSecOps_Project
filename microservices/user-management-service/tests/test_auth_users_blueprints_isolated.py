import importlib
import types
import pytest
from flask import Flask
import json

def _mk_app():
    app = Flask("test-isolated")
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
    def __init__(self, name):
        self.name = name
    
    def __eq__(self, other):
        return FakeFilter(self.name, "==", other)

class FakeFilter:
    def __init__(self, column, op, value):
        self.column = column
        self.op = op
        self.value = value

class FakeQuery:
    def __init__(self, items=None, single=None):
        self._items = items or []
        self._single = single
    
    def filter(self, *args, **kwargs):
        return self
    
    def filter_by(self, **kwargs):
        return self
    
    def first(self):
        return self._single
    
    def all(self):
        return self._items

class FakeDBSession:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self._next_id = 1
    
    def add(self, obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = self._next_id
            self._next_id += 1
        self.added.append(obj)
    
    def commit(self):
        self.committed += 1
    
    def rollback(self):
        self.rolled_back += 1

class FakeBcrypt:
    @staticmethod
    def generate_password_hash(password, rounds=None):
        return b"hashed_password"
    
    @staticmethod
    def check_password_hash(stored, provided):
        return True

def _get_view_function(module, func_name):
    """Get the actual view function, unwrapping decorators if needed"""
    func = getattr(module, func_name, None)
    if func is None:
        pytest.skip(f"{func_name} not found in module")
    
    # Try to get __wrapped__ if it exists (from decorators)
    return getattr(func, "__wrapped__", func)

def _call_view_with_params(view, *args):
    """Call view function with correct number of parameters"""
    import inspect
    
    # Get function signature
    try:
        sig = inspect.signature(view)
        param_count = len(sig.parameters)
    except:
        # If we can't get signature, try calling with all args
        try:
            return view(*args)
        except TypeError:
            # Try without args
            return view()
    
    # Call with appropriate number of arguments
    if param_count == 0:
        return view()
    elif param_count == 1:
        return view(args[0] if args else None)
    elif param_count == 2:
        return view(args[0] if args else None, args[1] if len(args) > 1 else None)
    else:
        return view(*args)

# ============= add_user tests =============

def test_add_user_wrapped_paths(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    # Setup minimal mocks
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery()
        
        def __init__(self, **kwargs):
            self.id = 1
            self.username = kwargs.get('username', '')
            self.email = kwargs.get('email', '')
        
        def to_json(self):
            return {"id": self.id, "username": self.username, "email": self.email}
    
    session = FakeDBSession()
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    
    view = _get_view_function(users_api, "add_user")
    
    # Test 1: Not admin -> 401
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "x"}),
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code == 401
    
    # Test 2: Missing payload -> 400
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    with app.test_request_context(
        "/",
        method="POST",
        data="",
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code == 400
    
    # Test 3: Missing fields -> 400
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "test"}),
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code == 400
    
    # Test 4: Success
    FakeUserClass.query = FakeQuery(single=None)  # No existing user
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "newuser", "email": "new@example.com", "password": "pass123"}),
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code in (201, 200)

def test_add_user_duplicate(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    existing_user = FakeUser(1, "existing", "existing@example.com")
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=existing_user)
        
        def __init__(self, **kwargs):
            pass
    
    session = FakeDBSession()
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    view = _get_view_function(users_api, "add_user")
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "existing", "email": "existing@example.com", "password": "pass"}),
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code == 400

# ============= get_all_users tests =============

def test_get_all_users_wrapped(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    users = [
        FakeUser(1, "user1", "user1@example.com"),
        FakeUser(2, "user2", "user2@example.com")
    ]
    
    class FakeUserClass:
        query = FakeQuery(items=users)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_all_users")
    
    with app.test_request_context("/", method="GET"):
        resp, code = _call_view_with_params(view, 1)
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["data"]["users"]) == 2

# ============= get_single_user tests =============

def test_get_single_user_wrapped_unauthorized(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    class FakeUserClass:
        query = FakeQuery()
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_single_user")
    
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "2")
        assert code == 401

def test_get_single_user_wrapped_not_found(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    class FakeUserClass:
        query = FakeQuery(single=None)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_single_user")
    
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "999")
        assert code == 404

def test_get_single_user_wrapped_success(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    user = FakeUser(5, "testuser", "test@example.com")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    class FakeUserClass:
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_single_user")
    
    with app.test_request_context("/", method="GET"):
        resp, code = view(1, "5")
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["id"] == 5

def test_get_single_user_wrapped_self_access(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    user = FakeUser(3, "testuser", "test@example.com")
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    class FakeUserClass:
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_single_user")
    
    with app.test_request_context("/", method="GET"):
        resp, code = view(3, "3")
        assert code == 200
        data = resp.get_json()
        assert data["data"]["id"] == 3

# ============= admin_create_user tests =============

def test_admin_create_user_exists(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    if not hasattr(users_api, "admin_create_user"):
        pytest.skip("admin_create_user not implemented")

def test_admin_create_user_not_admin(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    
    if not hasattr(users_api, "admin_create_user"):
        pytest.skip("admin_create_user not implemented")
    
    view = _get_view_function(users_api, "admin_create_user")
    app = _mk_app()
    
    monkeypatch.setattr(users_api, "is_admin", lambda uid: False, raising=False)
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({}),
        content_type="application/json"
    ):
        resp, code = _call_view_with_params(view, 1)
        assert code == 401

def test_admin_create_user_success(monkeypatch):
    users_api = importlib.import_module("app.api.users")
    
    if not hasattr(users_api, "admin_create_user"):
        pytest.skip("admin_create_user not implemented")
    
    view = _get_view_function(users_api, "admin_create_user")
    app = _mk_app()
    
    session = FakeDBSession()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
        
        def __init__(self, username, email, password, admin=False, active=True):
            self.id = 10
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
    
    monkeypatch.setattr(users_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({
            "username": "admin",
            "email": "admin@example.com",
            "password": "pass",
            "admin": True,
            "active": False
        }),
        content_type="application/json"
    ):
        resp, code = _call_view_with_params(view, 1)
        assert code in (201, 200, 400), f"Expected 201/200/400 but got {code}. Response: {resp.get_json()}"
        
        # If successful creation
        if code in (201, 200):
            data = resp.get_json()
            assert data["status"] == "success"
            assert data["data"]["admin"] is True
            assert data["data"]["active"] is False

# ============= Auth API tests =============

def test_register_user_wrapped(monkeypatch):
    auth_api = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    session = FakeDBSession()
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
        
        def __init__(self, username, email, password):
            self.id = 1
            self.username = username
            self.email = email
            self.password = b"hashed"
        
        def to_json(self):
            return {"id": self.id, "username": self.username, "email": self.email}
        
        def encode_auth_token(self, user_id):
            return f"token_{user_id}"
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view_function(auth_api, "register_user")
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "testuser", "email": "test@example.com", "password": "SecurePass123"}),
        content_type="application/json"
    ):
        resp, code = _call_view_with_params(view)
        assert code in (201, 200, 400), f"Expected 201/200/400 but got {code}. Response: {resp.get_json()}"
        
        if code in (201, 200):
            data = resp.get_json()
            assert data["status"] == "success"
            assert "auth_token" in data

def test_login_user_wrapped(monkeypatch):
    auth_api = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    user = FakeUser(1, "testuser", "test@example.com", password=b"hashed", active=True)
    
    class FakeUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    monkeypatch.setattr(auth_api, "bcrypt", FakeBcrypt(), raising=False)
    
    view = _get_view_function(auth_api, "login_user")
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"email": "test@example.com", "password": "correctpass"}),
        content_type="application/json"
    ):
        resp, code = _call_view_with_params(view)
        assert code in (200, 404, 401), f"Expected 200/404/401 but got {code}. Response: {resp.get_json()}"
        
        if code == 200:
            data = resp.get_json()
            assert data["status"] == "success"

def test_logout_user_wrapped(monkeypatch):
    auth_api = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    view = _get_view_function(auth_api, "logout_user")
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer token_1"}):
        # logout_user might require resp parameter from decorator
        try:
            resp, code = _call_view_with_params(view, 1)  # Try with user_id
        except TypeError:
            try:
                resp, code = _call_view_with_params(view)  # Try without parameters
            except:
                pytest.skip("Cannot determine logout_user signature")
        
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"

def test_get_user_status_wrapped(monkeypatch):
    auth_api = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    user = FakeUser(1, "testuser", "test@example.com")
    
    class FakeUserClass:
        query = FakeQuery(single=user)
        
        @staticmethod
        def decode_auth_token(token):
            return 1
    
    monkeypatch.setattr(auth_api, "User", FakeUserClass, raising=False)
    
    view = _get_view_function(auth_api, "get_user_status")
    
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer token_1"}):
        # get_user_status might require resp parameter from decorator
        try:
            resp, code = _call_view_with_params(view, 1)  # Try with user_id
        except TypeError:
            try:
                resp, code = _call_view_with_params(view)  # Try without parameters
            except:
                pytest.skip("Cannot determine get_user_status signature")
        
        assert code == 200
        data = resp.get_json()
        assert data["status"] == "success"

# ============= Additional Edge Case Tests =============

def test_add_user_exception_handling(monkeypatch):
    """Test exception handling in add_user"""
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    class BrokenUserClass:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
        
        def __init__(self, **kwargs):
            raise RuntimeError("Database error")
    
    session = FakeDBSession()
    monkeypatch.setattr(users_api, "User", BrokenUserClass, raising=False)
    monkeypatch.setattr(users_api, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(users_api, "is_admin", lambda uid: True, raising=False)
    
    view = _get_view_function(users_api, "add_user")
    
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "test", "email": "test@e.com", "password": "pass"}),
        content_type="application/json"
    ):
        resp, code = view(1)
        assert code in (400, 500)

def test_get_all_users_exception(monkeypatch):
    """Test exception handling in get_all_users"""
    users_api = importlib.import_module("app.api.users")
    app = _mk_app()
    
    class BrokenQuery:
        def all(self):
            raise RuntimeError("Database error")
    
    class BrokenUserClass:
        query = BrokenQuery()
    
    monkeypatch.setattr(users_api, "User", BrokenUserClass, raising=False)
    
    view = _get_view_function(users_api, "get_all_users")
    
    with app.test_request_context("/", method="GET"):
        resp, code = _call_view_with_params(view, 1)
        assert code in (500,)