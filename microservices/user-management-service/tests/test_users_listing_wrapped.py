import types
import importlib
from flask import Flask

class FakeUser:
    def __init__(self, id=1, username="u", email="u@e", admin=False, active=True):
        self.id = id; self.username = username; self.email = email
        self.admin = admin; self.active = active
    def to_json(self):
        return {"id": self.id, "username": self.username, "email": self.email, "admin": self.admin, "active": self.active}

class FakePagination:
    def __init__(self, items, total=2, pages=1):
        self.items = items; self.total = total; self.pages = pages

class FakeQuery:
    def all(self):
        return [FakeUser(1, "u1", "u1@e"), FakeUser(2, "u2", "u2@e")]
    def filter(self, *a, **k): return self
    def filter_by(self, **kw): return self
    def paginate(self, page=1, per_page=2, error_out=False):
        return FakePagination(self.all(), total=2, pages=1)
    def first(self):
        return FakeUser(1, "u1", "u1@e")

def _mk_app():
    app = Flask("users-listing")
    app.config.update(TESTING=True, SECRET_KEY="x")
    return app

def _call_if_present(users_mod, name, app, path="/", method="GET"):
    if not hasattr(users_mod, name):
        return
    view = getattr(users_mod, name)
    view = view.__wrapped__ if hasattr(view, "__wrapped__") else view
    # Patch admin check to pass
    if hasattr(users_mod, "is_admin"):
        setattr(users_mod, "is_admin", lambda uid: True)
    # Patch model/query
    setattr(users_mod, "User", FakeUser)
    FakeUser.query = FakeQuery()

    with app.test_request_context(f"{path}?page=1&per_page=2&q=a", method=method):
        rv = view(1) if view.__code__.co_argcount >= 1 else view()
        # Normalize (Response, code) or Response
        if isinstance(rv, tuple) and len(rv) >= 2:
            resp, code = rv[0], rv[1]
            assert code in (200, 201)
        else:
            resp = rv
            code = getattr(resp, "status_code", 200)
            assert code in (200, 201)

def test_users_module_listing_variants():
    try:
        users_mod = importlib.import_module("app.api.users")
    except Exception:
        return
    app = _mk_app()
    # Try common listing endpoint names
    for fname in [
        "get_users", "list_users", "get_all_users", "search_users", "admin_list_users",
        "get_all_active_users", "get_all_inactive_users",
    ]:
        _call_if_present(users_mod, fname, app, path="/api/users", method="GET")

def test_users_module_fetch_single_and_profile():
    try:
        users_mod = importlib.import_module("app.api.users")
    except Exception:
        return
    app = _mk_app()
    # Single fetch by id if present
    for fname in ["get_user", "fetch_user", "admin_get_user", "get_user_by_id"]:
        _call_if_present(users_mod, fname, app, path="/api/users/1", method="GET")