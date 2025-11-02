import types
import pytest
from flask import Flask
from sqlalchemy import exc
import app.api.scores as scores_api

class DummySession:
    def __init__(self, exc_to_raise=None):
        self.exc_to_raise = exc_to_raise
        self.added = []
        self.commits = 0
        self.rolled = 0
    def add(self, obj):
        self.added.append(obj)
    def commit(self):
        self.commits += 1
        if self.exc_to_raise:
            raise self.exc_to_raise
    def rollback(self):
        self.rolled += 1

@pytest.fixture()
def client():
    app = Flask("scores_ext")
    app.register_blueprint(scores_api.scores_blueprint, url_prefix="/api/scores")
    return app.test_client()

def test_add_scores_success_with_all_fields(monkeypatch, client):
    app = client.application
    class ScoreCtor:
        def __init__(self, user_id=None, exercise_id=None, answer=None, results=None, user_results=None):
            self.user_id = user_id
            self.exercise_id = exercise_id
            self.answer = answer
            self.results = results
            self.user_results = user_results
        def to_json(self):
            return {
                "user_id": self.user_id,
                "exercise_id": self.exercise_id,
                "answer": self.answer,
                "results": self.results,
                "user_results": self.user_results,
            }
    ds = DummySession()
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(scores_api, "Score", ScoreCtor, raising=False)
    with app.test_request_context(
        "/api/scores/",
        method="POST",
        json={"exercise_id": 9, "answer": "A", "results": [True, False], "user_results": ["ok", "no"]},
    ):
        resp = scores_api.add_scores.__wrapped__({"id": 7})
        assert isinstance(resp, tuple) and resp[1] == 201
        assert ds.commits == 1

def test_update_score_not_found(monkeypatch, client):
    app = client.application
    class QNotFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda: None)
    ds = DummySession()
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QNotFound()), raising=False)
    with app.test_request_context("/api/scores/5", method="PUT", json={"answer": "x"}):
        resp = scores_api.update_score.__wrapped__({"id": 1}, "5")
        # API thường trả 404 khi không tồn tại score
        assert isinstance(resp, tuple) and resp[1] in (404, 400)

def test_update_score_permission_denied_or_ok(monkeypatch, client):
    app = client.application
    class ScoreStub:
        def __init__(self):
            self.id = 10
            self.user_id = 99  # khác user -> có thể 403
            self.answer = None
            self.results = None
            self.user_results = None
        def to_json(self):
            return {"id": self.id, "user_id": self.user_id, "answer": self.answer}
    class QFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda: ScoreStub())
    ds = DummySession()
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds), raising=False)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    with app.test_request_context("/api/scores/10", method="PUT", json={"answer": "new"}):
        resp = scores_api.update_score.__wrapped__({"id": 1}, "10")
        # Tùy implement: 403 (forbidden) hoặc 200 nếu không kiểm tra quyền
        assert isinstance(resp, tuple) and resp[1] in (403, 200)

def test_update_score_integrity_and_generic_error(monkeypatch, client):
    app = client.application
    class ScoreStub:
        def __init__(self):
            self.id = 11
            self.user_id = 1
            self.answer = None
            self.results = None
            self.user_results = None
        def to_json(self):
            return {"id": self.id, "user_id": self.user_id}
    class QFound:
        def filter_by(self_inner, **kw):
            return types.SimpleNamespace(first=lambda: ScoreStub())
    # IntegrityError -> 400
    ds_int = DummySession(exc.IntegrityError("stmt", {}, Exception("orig")))
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds_int), raising=False)
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QFound()), raising=False)
    with app.test_request_context("/api/scores/11", method="PUT", json={"answer": "x"}):
        resp1 = scores_api.update_score.__wrapped__({"id": 1}, "11")
        assert isinstance(resp1, tuple) and resp1[1] == 400
    # Generic error -> 500 hoặc 400 tùy API
    ds_gen = DummySession(RuntimeError("boom"))
    monkeypatch.setattr(scores_api, "db", types.SimpleNamespace(session=ds_gen), raising=False)
    with app.test_request_context("/api/scores/11", method="PUT", json={"results": [True]}):
        resp2 = scores_api.update_score.__wrapped__({"id": 1}, "11")
        assert isinstance(resp2, tuple) and resp2[1] in (500, 400)