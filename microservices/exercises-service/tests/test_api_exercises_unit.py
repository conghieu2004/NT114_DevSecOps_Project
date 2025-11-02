import types
from sqlalchemy import exc
import pytest
from app.main import app
import app.api.exercises as exercises_api

class DummySession:
    def __init__(self, fail_commit=None):
        # fail_commit can be Exception instance to raise on commit
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.fail_commit = fail_commit

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        if isinstance(self.fail_commit, Exception):
            raise self.fail_commit
        self.committed = True

    def rollback(self):
        self.rolled_back = True

class EStub:
    def __init__(self, title=None, body=None, difficulty=None, test_cases=None, solutions=None):
        self.id = 99
        self.title = title or "t"
        self.body = body or "b"
        self.difficulty = difficulty or 1
        self.test_cases = test_cases or []
        self.solutions = solutions or []
    def to_json(self):
        return {"id": self.id, "title": self.title}

def _req_ctx(path="/", method="POST", json=None):
    return app.test_request_context(path, method=method, json=json)

def test_add_exercise_success(monkeypatch):
    # prepare request payload and dummy DB/session + stub Exercise
    payload = {"title":"t","body":"b","difficulty":1,"test_cases":[1],"solutions":[1]}
    ds = DummySession()
    monkeypatch.setattr(exercises_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(exercises_api, "Exercise", EStub, raising=False)

    with _req_ctx("/", method="POST", json=payload):
        # call unwrapped function to bypass authenticate decorator
        resp = exercises_api.add_exercise.__wrapped__({"username":"u","admin":True})
    assert isinstance(resp, tuple)
    assert resp[1] in (201,)

def test_add_exercise_integrity_error(monkeypatch):
    payload = {"title":"t","body":"b","difficulty":1,"test_cases":[1],"solutions":[1]}
    # session commit will raise IntegrityError
    ds = DummySession(fail_commit=exc.IntegrityError("stmt", {}, Exception("orig")))
    monkeypatch.setattr(exercises_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(exercises_api, "Exercise", EStub, raising=False)

    with _req_ctx("/", method="POST", json=payload):
        resp = exercises_api.add_exercise.__wrapped__({"username":"u","admin":True})
    assert isinstance(resp, tuple)
    assert resp[1] in (400,)

def test_add_exercise_generic_exception(monkeypatch):
    payload = {"title":"t","body":"b","difficulty":1,"test_cases":[1],"solutions":[1]}
    # session commit raises RuntimeError
    ds = DummySession(fail_commit=RuntimeError("boom"))
    monkeypatch.setattr(exercises_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(exercises_api, "Exercise", EStub, raising=False)

    with _req_ctx("/", method="POST", json=payload):
        resp = exercises_api.add_exercise.__wrapped__({"username":"u","admin":True})
    assert isinstance(resp, tuple)
    assert resp[1] in (500,)

def test_update_exercise_invalid_id_returns_400():
    with _req_ctx("/abc", method="PUT", json={"title":"x"}):
        resp = exercises_api.update_exercise.__wrapped__({"username":"u","admin":True}, "abc")
    assert isinstance(resp, tuple)
    assert resp[1] in (400,)

def test_update_exercise_not_found(monkeypatch):
    # simulate query returning None
    class QNot:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : None)
    monkeypatch.setattr(exercises_api, "Exercise", types.SimpleNamespace(query=QNot()), raising=False)

    with _req_ctx("/5", method="PUT", json={"title":"x"}):
        resp = exercises_api.update_exercise.__wrapped__({"username":"u","admin":True}, "5")
    assert isinstance(resp, tuple)
    assert resp[1] in (404,)

def test_update_exercise_success(monkeypatch):
    # simulate found exercise instance that will be updated
    ex = EStub(title="old")
    class QFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : ex)
    # dummy session
    ds = DummySession()
    monkeypatch.setattr(exercises_api, "Exercise", types.SimpleNamespace(query=QFound()), raising=False)
    monkeypatch.setattr(exercises_api, "db", types.SimpleNamespace(session=ds), raising=False)

    with _req_ctx("/5", method="PUT", json={"title":"new"}):
        resp = exercises_api.update_exercise.__wrapped__({"username":"u","admin":True}, "5")
    assert isinstance(resp, tuple) or hasattr(resp, "status_code")
    # accept success or auth/method variations depending on test harness
    # primary goal: exercise success path so prefer 200
    status = resp[1] if isinstance(resp, tuple) else resp.status_code
    assert status in (200,)

def test_get_single_exercise_value_error_branch(client):
    # call with non-numeric id to trigger ValueError path in get_single_exercise
    _, item = None, None
    # find item route
    for rule in client.application.url_map.iter_rules():
        if "<" in rule.rule and "exercise" in rule.rule.lower():
            item = rule.rule
            break
    if item is None:
        pytest.skip("no item route")
    url = item.replace("<exercise_id>", "notint")
    r = client.get(url)
    assert r.status_code in (404,)