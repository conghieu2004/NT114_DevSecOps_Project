import importlib
import types
import pytest
from flask import Flask
import json

def _mk_app():
    app = Flask("test-auth-more")
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        BCRYPT_LOG_ROUNDS=4
    )
    return app

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
    def __init__(self, single=None):
        self._single = single
    
    def filter_by(self, **kwargs):
        return self
    
    def first(self):
        return self._single

class FakeDBSession:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = 0
    
    def add(self, obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = len(self.added) + 1
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

def test_register_branches(monkeypatch):
    auth = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    session = FakeDBSession()
    
    class MockUser:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=None)
        
        def __init__(self, username, email, password):
            self.id = None
            self.username = username
            self.email = email
            self.password = b"hashed"
        
        def to_json(self):
            return {"id": self.id, "username": self.username, "email": self.email}
        
        def encode_auth_token(self, user_id):
            return f"token_{user_id}"
    
    monkeypatch.setattr(auth, "User", MockUser, raising=False)
    monkeypatch.setattr(auth, "db", types.SimpleNamespace(session=session), raising=False)
    monkeypatch.setattr(auth, "bcrypt", FakeBcrypt(), raising=False)
    
    view = getattr(auth.register_user, "__wrapped__", auth.register_user)
    
    # Test empty payload
    with app.test_request_context(
        "/",
        method="POST",
        data="",
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400
    
    # Test missing fields
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"username": "test"}),
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400
    
    # Test success
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123"
        }),
        content_type="application/json"
    ):
        resp, code = view()
        assert code in (201, 200), f"Expected 201/200, got {code}"

def test_login_branches(monkeypatch):
    auth = importlib.import_module("app.api.auth")
    app = _mk_app()
    
    class FakeUser:
        def __init__(self):
            self.id = 1
            self.email = "test@example.com"
            self.password = b"hashed"
            self.active = True
        
        def to_json(self):
            return {"id": self.id, "email": self.email, "active": self.active}
        
        def encode_auth_token(self, user_id):
            return f"token_{user_id}"
    
    user = FakeUser()
    
    class MockUser:
        email = FakeColumn("email")
        username = FakeColumn("username")
        query = FakeQuery(single=user)
    
    monkeypatch.setattr(auth, "User", MockUser, raising=False)
    monkeypatch.setattr(auth, "bcrypt", FakeBcrypt(), raising=False)
    
    view = getattr(auth.login_user, "__wrapped__", auth.login_user)
    
    # Test empty payload
    with app.test_request_context(
        "/",
        method="POST",
        data="",
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400
    
    # Test missing fields
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({"email": "test@example.com"}),
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 400
    
    # Test user not found
    MockUser.query = FakeQuery(single=None)
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({
            "email": "notfound@example.com",
            "password": "pass"
        }),
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 404
    
    # Test success
    MockUser.query = FakeQuery(single=user)
    with app.test_request_context(
        "/",
        method="POST",
        data=json.dumps({
            "email": "test@example.com",
            "password": "correctpass"
        }),
        content_type="application/json"
    ):
        resp, code = view()
        assert code == 200

# Keep other tests...