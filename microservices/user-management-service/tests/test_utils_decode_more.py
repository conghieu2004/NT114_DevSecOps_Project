import importlib
import types
import pytest
from flask import Flask

def _mk_app():
    app = Flask("utils-more")
    app.config.update(TESTING=True, SECRET_KEY="x")
    return app

def _get_utils():
    try:
        return importlib.import_module("app.utils")
    except Exception:
        pytest.skip("app.utils not available")

def test_utils_decode_auth_token_paths(monkeypatch):
    utils = _get_utils()

    if not hasattr(utils, "decode_auth_token"):
        pytest.skip("decode_auth_token not implemented")

    class U1:
        @staticmethod
        def decode_auth_token(tok): return "Invalid token"
        class Q:
            def filter_by(self, **kw): return self
            def first(self): return None
        query = Q()

    monkeypatch.setattr(utils, "User", U1, raising=False)
    assert utils.decode_auth_token("x") is None

    class U2:
        @staticmethod
        def decode_auth_token(tok): return 5
        class Q:
            def filter_by(self, **kw): return self
            def first(self): return None
        query = Q()
    monkeypatch.setattr(utils, "User", U2, raising=False)
    assert utils.decode_auth_token("y") is None

    class Q3:
        def filter_by(self, **kw): return self
        def first(self): return types.SimpleNamespace(active=False, username="x", email="x@e")
    class U3:
        @staticmethod
        def decode_auth_token(tok): return 7
        query = Q3()
    monkeypatch.setattr(utils, "User", U3, raising=False)
    assert utils.decode_auth_token("z") is None

    class U4:
        @staticmethod
        def decode_auth_token(tok): raise RuntimeError("boom")
        class Q:
            def filter_by(self, **kw): return self
            def first(self): return None
        query = Q()
    monkeypatch.setattr(utils, "User", U4, raising=False)
    assert utils.decode_auth_token("err") is None

def test_authenticate_and_admin_required_quick_paths(monkeypatch):
    utils = _get_utils()
    if not hasattr(utils, "authenticate") or not hasattr(utils, "admin_required"):
        pytest.skip("decorators not implemented")

    app = _mk_app()

    @utils.authenticate
    def protected(user_id):
        return {"ok": True}

    with app.test_request_context("/", method="GET"):
        resp, code = protected()
        assert code in (401, 403)

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp, code = protected()
        assert code in (401, 403)

    monkeypatch.setattr(utils, "decode_auth_token", lambda tok: None, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer bad"}):
        resp, code = protected()
        assert code in (401, 403)

    monkeypatch.setattr(utils, "decode_auth_token", lambda tok: 9, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer ok"}):
        res = protected()
        assert isinstance(res, dict) and res["ok"] is True

    class Q:
      def __init__(self, obj): self._obj = obj
      def filter_by(self, **kw): return self
      def first(self): return self._obj
    class U:
      @staticmethod
      def decode_auth_token(tok): return 1
      query = Q(types.SimpleNamespace(active=True, admin=False, username="u", email="u@e"))

    @utils.admin_required
    def admin_only(uid):
        return {"ok": True}

    with app.test_request_context("/", method="GET"):
        resp, code = admin_only()
        assert code in (401, 403)

    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp, code = admin_only()
        assert code in (401, 403)

    class UBad:
        @staticmethod
        def decode_auth_token(tok): return "Invalid token"
        class Q2:
            def filter_by(self, **kw): return self
            def first(self): return None
        query = Q2()
    monkeypatch.setattr(utils, "User", UBad, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer bad"}):
        resp, code = admin_only()
        assert code in (401, 403)

    class UNone:
        @staticmethod
        def decode_auth_token(tok): return 1
        class Q3:
            def filter_by(self, **kw): return self
            def first(self): return None
        query = Q3()
    monkeypatch.setattr(utils, "User", UNone, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer ok"}):
        resp, code = admin_only()
        assert code in (401, 403)

    class Q4:
        def filter_by(self, **kw): return self
        def first(self): return types.SimpleNamespace(active=False, admin=False, username="u", email="u@e")
    class UInactive:
        @staticmethod
        def decode_auth_token(tok): return 1
        query = Q4()
    monkeypatch.setattr(utils, "User", UInactive, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer ok"}):
        resp, code = admin_only()
        assert code in (401, 403)

    class Q5:
        def filter_by(self, **kw): return self
        def first(self): return types.SimpleNamespace(active=True, admin=False, username="u", email="u@e")
    class UNoAdmin:
        @staticmethod
        def decode_auth_token(tok): return 1
        query = Q5()
    monkeypatch.setattr(utils, "User", UNoAdmin, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer ok"}):
        resp, code = admin_only()
        assert code in (401, 403)

    class Q6:
        def filter_by(self, **kw): return self
        def first(self): return types.SimpleNamespace(active=True, admin=True, username="u", email="u@e")
    class UAdmin:
        @staticmethod
        def decode_auth_token(tok): return 1
        query = Q6()
    monkeypatch.setattr(utils, "User", UAdmin, raising=False)
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer ok"}):
        res = admin_only()
        assert isinstance(res, dict) and res["ok"] is True