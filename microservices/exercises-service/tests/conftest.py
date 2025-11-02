import os
import re
import importlib
import sys
import json
import pytest
import requests
from requests.models import Response

# ensure service root is on sys.path so `import app` works
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ensure app uses an in-memory database for tests and testing mode BEFORE importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TESTING", "1")

from app.main import app
from app.models import Exercise

# helpers
def _find_endpoints():
    collection = None
    item = None
    for rule in app.url_map.iter_rules():
        p = rule.rule.lower()
        if "exercise" not in p:
            continue
        if "<" not in p and collection is None:
            collection = rule.rule
        if "<" in p and item is None:
            item = rule.rule
    return collection, item

def _exercises_endpoint(method):
    m = method.upper()
    candidates = []
    for rule in app.url_map.iter_rules():
        if "exercise" not in rule.rule.lower():
            continue
        if m in rule.methods:
            candidates.append(rule.rule)
    if not candidates:
        return None
    if m in ("POST", "GET"):
        for r in candidates:
            if "<" not in r:
                return r
    for r in candidates:
        if "<" in r:
            return r
    return candidates[0]

def _fill_id(path, id_val=1):
    return re.sub(r"<[^>]+>", str(id_val), path)

def _extract_list_from_response(resp):
    try:
        data = resp.get_json()
    except Exception:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("data", "result", "items", "exercises", "payload", "results"):
            v = data.get(k)
            if isinstance(v, list):
                return v
        for v in data.values():
            if isinstance(v, list):
                return v
    return None

# fixtures
@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as c:
        yield c

@pytest.fixture
def headers():
    return {"Authorization": "Bearer token"}

@pytest.fixture
def sample_model_data():
    return {
        "title": "Sum Test",
        "body": "Add two numbers",
        "difficulty": 1,
        "test_cases": [],
        "solutions": []
    }

@pytest.fixture
def sample_data():
    return {
        "title": "Sum Test",
        "body": "Add two numbers",
        "difficulty": 1,
        "test_cases": [{"input": "1 2", "output": "3"}],
        "solutions": ["def solve(a,b): return a+b"],
        "author": "test_user",
        "time_limit": 1,
        "memory_limit": 256,
        "tags": ["math", "easy"],
        "category": "algorithms",
        "public": True,
        "language": "python",
        "samples": [{"input": "1 2", "output": "3"}],
        "starter_code": "def solve(): pass",
        "input_format": "two integers",
        "output_format": "one integer"
    }

# autouse stub for external auth utility functions
@pytest.fixture(autouse=True)
def _mock_auth_checks(monkeypatch):
    candidates = [
        "exercises_utils.utils",
        "exercises_utils.auth",
        "utils",
        "app.utils",
        "exercises.utils",
    ]
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for fn in ("verify_token", "verify_user", "get_user_status", "check_token"):
            if hasattr(mod, fn):
                monkeypatch.setattr(mod, fn, lambda token, *a, **k: {"username": "test_user", "admin": True}, raising=False)
    yield

# expose helpers to tests if needed
@pytest.fixture
def endpoints_helpers():
    return {
        "find": _find_endpoints,
        "endpoint": _exercises_endpoint,
        "fill_id": _fill_id,
        "extract_list": _extract_list_from_response
    }

@pytest.fixture(autouse=True)
def set_test_env():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("TESTING", "1")
    yield

@pytest.fixture(autouse=True)
def _prevent_network_calls(monkeypatch):
    """
    Autouse fixture: stub outbound HTTP calls so tests don't perform
    real network requests to user-management or other services.
    Return a response shape compatible with typical auth endpoints.
    """
    def _make_resp(json_obj=None, status=200):
        r = Response()
        r.status_code = status
        r.headers['Content-Type'] = 'application/json'
        r._content = json.dumps(json_obj or {
            "status": "success",
            "data": {"username": "test_user", "admin": True}
        }).encode()
        return r

    def fake_session_request(self, method, url, *args, **kwargs):
        # Return an auth-success shaped payload for auth-related URLs
        if "/api/auth" in url or "/auth" in url or "host.docker.internal" in url:
            return _make_resp({
                "status": "success",
                "data": {"username": "test_user", "admin": True}
            }, status=200)
        # Default generic OK response with helpful body
        return _make_resp({"status": "success", "data": {"ok": True}}, status=200)

    # Patch Session.request and common helpers
    monkeypatch.setattr(requests.sessions.Session, "request", fake_session_request, raising=False)
    monkeypatch.setattr(requests, "get", lambda *a, **k: _make_resp({
        "status": "success",
        "data": {"username": "test_user", "admin": True}
    }, status=200), raising=False)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _make_resp({
        "status": "success",
        "data": {"username": "test_user", "admin": True}
    }, status=200), raising=False)
    yield