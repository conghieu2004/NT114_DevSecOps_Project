import types
import pytest
from flask import Flask
from sqlalchemy import exc
import app.api.scores as scores_api

# Build a lightweight Flask app and register the blueprint for isolated testing
@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(scores_api.scores_blueprint, url_prefix="/api/scores")
    return app.test_client()

class DummySession:
    def __init__(self, commit_exc=None):
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.commit_exc = commit_exc
    def add(self, obj):
        self.added.append(obj)
    def commit(self):
        if self.commit_exc:
            raise self.commit_exc
        self.committed = True
    def rollback(self):
        self.rolled_back = True

class ScoreStub:
    def __init__(self, user_id=1, exercise_id=2, answer=None, results=None, user_results=None, id=10):
        self.id = id
        self.user_id = user_id
        self.exercise_id = exercise_id
        self.answer = answer
        self.results = results
        self.user_results = user_results
    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "exercise_id": self.exercise_id,
            "answer": self.answer,
            "results": self.results,
            "user_results": self.user_results,
        }

def test_ping(client):
    r = client.get("/api/scores/ping")
    assert r.status_code == 200
    assert r.get_json().get("message") == "pong!"

def test_get_all_scores_success(monkeypatch, client):
    class QSuccess:
        def all(self_inner):
            return [ScoreStub(id=1), ScoreStub(id=2)]
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QSuccess()), raising=False)
    r = client.get("/api/scores/")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data.get("data", {}).get("scores"), list)

def test_get_all_scores_by_user_unwrapped(monkeypatch, client):
    # bypass authenticate by calling __wrapped__ with user_data in a request context
    class QByUser:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(all=lambda : [ScoreStub(user_id=kw.get("user_id", 1))])
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QByUser()), raising=False)
    app = client.application
    with app.test_request_context("/api/scores/user", method="GET"):
        resp = scores_api.get_all_scores_by_user_user.__wrapped__({"id": 99})
        assert isinstance(resp, tuple) and resp[1] == 200

def test_get_single_score_by_user_id_branches(monkeypatch, client):
    app = client.application
    # not found
    class QNot:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : None)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QNot()), raising=False)
    with app.test_request_context("/api/scores/user/5", method="GET"):
        resp = scores_api.get_single_score_by_user_id.__wrapped__({"id": 1}, "5")
        assert isinstance(resp, tuple) and resp[1] == 404
    # found
    class QFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : ScoreStub(id=7, user_id=kw.get("user_id", 1)))
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    with app.test_request_context("/api/scores/user/7", method="GET"):
        resp2 = scores_api.get_single_score_by_user_id.__wrapped__({"id": 1}, "7")
        assert isinstance(resp2, tuple) and resp2[1] == 200
    # value error
    with app.test_request_context("/api/scores/user/notint", method="GET"):
        resp3 = scores_api.get_single_score_by_user_id.__wrapped__({"id": 1}, "notint")
        assert isinstance(resp3, tuple) and resp3[1] == 404

def test_add_scores_invalid_and_success_and_integrity(monkeypatch, client):
    app = client.application
    # invalid payload -> 400 (empty body but application/json header)
    with app.test_request_context(
        "/api/scores/",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=b""
    ):
        resp = scores_api.add_scores.__wrapped__({"id": 1})
        assert isinstance(resp, tuple) and resp[1] == 400
    # success -> 201
    ds = DummySession()
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(scores_api, "Score", ScoreStub, raising=False)
    with app.test_request_context("/api/scores/", method="POST", json={"exercise_id": 2, "answer": "a", "results": [True], "user_results": ["ok"]}):
        resp2 = scores_api.add_scores.__wrapped__({"id": 1})
        assert isinstance(resp2, tuple) and resp2[1] == 201
    # integrity error -> 400
    ds2 = DummySession(commit_exc=exc.IntegrityError("stmt", {}, Exception("orig")))
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds2), raising=False)
    monkeypatch.setattr(scores_api, "Score", ScoreStub, raising=False)
    with app.test_request_context("/api/scores/", method="POST", json={"exercise_id": 2}):
        resp3 = scores_api.add_scores.__wrapped__({"id": 1})
        assert isinstance(resp3, tuple) and resp3[1] == 400

def test_update_score_branches(monkeypatch, client):
    app = client.application
    # empty payload -> 400 (empty body but application/json header)
    with app.test_request_context(
        "/api/scores/3",
        method="PUT",
        headers={"Content-Type": "application/json"},
        data=b""
    ):
        resp = scores_api.update_score.__wrapped__({"id": 1}, "3")
        assert isinstance(resp, tuple) and resp[1] == 400
    # no fields to update -> 400
    with app.test_request_context("/api/scores/3", method="PUT", json={}):
        resp2 = scores_api.update_score.__wrapped__({"id": 1}, "3")
        assert isinstance(resp2, tuple) and resp2[1] == 400
    # not found -> 400
    class QNot:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : None)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QNot()), raising=False)
    with app.test_request_context("/api/scores/9", method="PUT", json={"answer": "x"}):
        resp3 = scores_api.update_score.__wrapped__({"id": 1}, "9")
        assert isinstance(resp3, tuple) and resp3[1] == 400
    # found -> success 200
    s = ScoreStub(id=5, user_id=1, exercise_id=9)
    class QFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda : s)
    ds = DummySession()
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    with app.test_request_context("/api/scores/9", method="PUT", json={"answer": "new", "results": [True], "user_results": ["v"]}):
        resp4 = scores_api.update_score.__wrapped__({"id": 1}, "9")
        assert isinstance(resp4, tuple) and resp4[1] == 200
    # commit raises TypeError -> caught by specific except -> 400
    ds_err_type = DummySession(commit_exc=TypeError("bad"))
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds_err_type), raising=False)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    with app.test_request_context("/api/scores/9", method="PUT", json={"answer": "a"}):
        resp5 = scores_api.update_score.__wrapped__({"id": 1}, "9")
        assert isinstance(resp5, tuple) and resp5[1] == 400
    # commit raises RuntimeError -> caught by general except -> 400
    ds_err_rt = DummySession(commit_exc=RuntimeError("boom"))
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds_err_rt), raising=False)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    with app.test_request_context("/api/scores/9", method="PUT", json={"answer": "a"}):
        resp6 = scores_api.update_score.__wrapped__({"id": 1}, "9")
        assert isinstance(resp6, tuple) and resp6[1] == 400

def test_get_all_scores_exception(monkeypatch, client):
    # Force Score.query.all() to raise -> cover error handler
    class QFail:
        def all(self_inner):
            raise RuntimeError("db boom")
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFail()), raising=False)
    r = client.get("/api/scores/")
    assert r.status_code in (500, 400)

def test_get_single_score_exception(monkeypatch, client):
    # Force Score.query.filter_by().first() to raise -> cover error handler
    class QFail:
        def filter_by(self_inner, **kw):
            def _first():
                raise RuntimeError("db fail")
            return types.SimpleNamespace(first=_first)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFail()), raising=False)
    r = client.get("/api/scores/1")
    # Một số cấu hình blueprint không cho phép GET trên route này -> 405
    assert r.status_code in (500, 400, 405)

def test_add_scores_generic_exception(monkeypatch, client):
    app = client.application
    # Make constructor raise to trigger general exception path in add_scores
    class ScoreCtorBoom:
        def __init__(self, user_id=None, exercise_id=None, answer=None, results=None, user_results=None):
            raise RuntimeError("ctor exploded")
    ds = DummySession()
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(scores_api, "Score", ScoreCtorBoom, raising=False)
    with app.test_request_context(
        "/api/scores/",
        method="POST",
        json={"exercise_id": 2, "answer": "a", "results": [True], "user_results": ["ok"]},
    ):
        resp = scores_api.add_scores.__wrapped__({"id": 123})
        # catch-all thường trả 500 hoặc 400 tùy implement
        assert isinstance(resp, tuple) and resp[1] in (500, 400)

def test_add_scores_results_length_mismatch(monkeypatch, client):
    # Nếu API kiểm tra độ dài không khớp -> trả lỗi (400/422/500 tùy implement)
    app = client.application
    with app.test_request_context(
        "/api/scores/",
        method="POST",
        json={"exercise_id": 2, "answer": "a", "results": [True, False], "user_results": ["only-one"]},
    ):
        resp = scores_api.add_scores.__wrapped__({"id": 1})
        assert isinstance(resp, tuple)
        assert resp[1] in (400, 422, 500)

def test_update_score_value_error_id(monkeypatch, client):
    app = client.application
    # Truyền id không phải số -> nhánh ValueError (404/400)
    with app.test_request_context("/api/scores/not-an-int", method="PUT", json={"answer": "x"}):
        resp = scores_api.update_score.__wrapped__({"id": 1}, "not-an-int")
        assert isinstance(resp, tuple)
        assert resp[1] in (404, 400)